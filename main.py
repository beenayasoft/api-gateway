"""
API Gateway FastAPI avec compatibilité frontend existant et CORS configuré pour le frontend
"""
import asyncio
import logging
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn

from config import SERVICES, LEGACY_ROUTE_MAPPING, GATEWAY_HOST, GATEWAY_PORT, DEBUG
from middleware import JWTMiddleware

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création de l'application FastAPI
app = FastAPI(
    title="Beenaya API Gateway",
    description="Point d'entrée centralisé pour l'architecture SOA avec compatibilité frontend",
    version="1.0.0",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None
)

# ✅ CONFIGURATION CORS POUR LE FRONTEND
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Frontend Vite
        "http://127.0.0.1:8080",
        "http://localhost:3000",  # React standard
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*", "X-Tenant-ID", "x-tenant-id"],  # Ajout explicite
)

class ServiceRouter:
    """Router intelligent avec compatibilité frontend existant"""
    
    def __init__(self):
        self.services = SERVICES
        self.legacy_mapping = LEGACY_ROUTE_MAPPING
    
    def resolve_service(self, path: str) -> tuple[str, str]:
        """
        Résout intelligemment le service cible
        1. Vérifie d'abord le mapping de compatibilité
        2. Puis la configuration normale des services
        """
        
        # 1. Vérification mapping de compatibilité
        if path in self.legacy_mapping:
            service_name, target_path = self.legacy_mapping[path]
            if service_name in self.services:
                return self.services[service_name]["url"], target_path
        
        # 2. Vérification mapping par préfixe (pour routes dynamiques)
        for legacy_route, (service_name, new_route) in self.legacy_mapping.items():
            if path.startswith(legacy_route.rstrip('/')):
                if service_name in self.services:
                    # Remplacer le préfixe
                    target_path = path.replace(legacy_route.rstrip('/'), new_route.rstrip('/'))
                    return self.services[service_name]["url"], target_path
        
        # 3. Configuration normale des services
        for service_name, config in self.services.items():
            for route_prefix in config["routes"]:
                if path.startswith(route_prefix):
                    return config["url"], path
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun service configuré pour le chemin: {path}"
        )
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Vérifie la santé de tous les services backend"""
        
        health_status = {
            "gateway": {"status": "healthy", "version": "1.0.0"},
            "services": {},
            "legacy_compatibility": "enabled"
        }
        
        overall_healthy = True
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            tasks = []
            
            for service_name, config in self.services.items():
                health_url = f"{config['url']}{config['health']}"
                tasks.append(self._check_service_health(client, service_name, health_url))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for service_name, result in zip(self.services.keys(), results):
                if isinstance(result, Exception):
                    health_status["services"][service_name] = {
                        "status": "unreachable",
                        "error": str(result)
                    }
                    overall_healthy = False
                else:
                    health_status["services"][service_name] = result
                    if result["status"] != "healthy":
                        overall_healthy = False
        
        health_status["gateway"]["overall_status"] = "healthy" if overall_healthy else "degraded"
        return health_status
    
    async def _check_service_health(self, client: httpx.AsyncClient, service_name: str, health_url: str) -> Dict[str, Any]:
        """Vérifie la santé d'un service individuel"""
        
        try:
            response = await client.get(health_url)
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "url": health_url,
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                return {
                    "status": "unhealthy", 
                    "url": health_url,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                "status": "unreachable",
                "url": health_url, 
                "error": str(e)
            }

# Instance globale du router
router = ServiceRouter()

async def get_current_user(request: Request):
    """
    Dependency pour extraire et valider l'utilisateur à partir du JWT
    Compatible avec le frontend existant
    """
    
    # Vérifier si la route est publique
    if JWTMiddleware.is_public_route(request.url.path, request.method):
        logger.info(f"Route publique accédée: {request.method} {request.url.path}")
        return None
    
    # Extraire le token
    authorization = request.headers.get("authorization")
    token = JWTMiddleware.extract_token(authorization)
    
    if not token:
        # Pour compatibilité frontend, retourner 401 avec format attendu
        logger.warning(f"Accès non authentifié à une route protégée: {request.method} {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification requis",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Valider le token et retourner les informations utilisateur
    return JWTMiddleware.validate_token(token)

@app.get("/")
async def gateway_info():
    """Informations sur l'API Gateway"""
    
    return {
        "service": "api-gateway",
        "version": "1.0.0", 
        "status": "operational",
        "documentation": "/docs" if DEBUG else "disabled",
        "legacy_compatibility": "enabled",
        "endpoints": {
            "health": "/health/",
            "auth": "/api/auth/*",
            "tenants": "/api/tenants/*",
            "tiers": "/api/tiers/*",
            "legacy": "Mapping automatique des anciennes routes"
        },
        "services_backend": list(router.services.keys())
    }

@app.get("/health/")
async def health_check():
    """Health check de l'API Gateway et de tous les services"""
    
    health_data = await router.health_check_all()
    
    # Déterminer le status code
    if health_data["gateway"]["overall_status"] == "healthy":
        return JSONResponse(content=health_data, status_code=200)
    else:
        return JSONResponse(content=health_data, status_code=503)

# Note: L'endpoint /tenants/current_tenant_info/ est géré par le routage standard via LEGACY_ROUTE_MAPPING

# Endpoint direct pour les taux de TVA (sans authentification)
@app.get("/api/quotes/vat-rates/", include_in_schema=True)
async def vat_rates_endpoint():
    """
    Endpoint direct pour les taux de TVA sans authentification requise
    """
    logger.info("Accès direct à l'endpoint des taux de TVA")
    
    # Définition des taux de TVA directement dans l'API Gateway
    vat_rates = [
        {
            'code': "0", 
            'name': "0%", 
            'rate': 0.0,
            'rate_display': "0%",
            'description': "Taux de TVA à 0%",
            'is_default': False,
            'is_active': True
        },
        {
            'code': "5.5", 
            'name': "5.5%", 
            'rate': 5.5,
            'rate_display': "5.5%",
            'description': "Taux de TVA à 5.5%",
            'is_default': False,
            'is_active': True
        },
        {
            'code': "10", 
            'name': "10%", 
            'rate': 10.0,
            'rate_display': "10%",
            'description': "Taux de TVA à 10%",
            'is_default': False,
            'is_active': True
        },
        {
            'code': "20", 
            'name': "20%", 
            'rate': 20.0,
            'rate_display': "20%",
            'description': "Taux de TVA à 20%",
            'is_default': True,
            'is_active': True
        }
    ]
    
    return vat_rates

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_request(
    request: Request, 
    path: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Proxy intelligent avec compatibilité frontend existant
    """
    
    # Résoudre le service cible (avec mapping de compatibilité)
    try:
        service_url, target_path = router.resolve_service(f"/{path}")
        
        # Log détaillé pour le débogage
        logger.info(f"Route résolue: /{path} -> service: {service_url}, path: {target_path}")
        
        # Construire l'URL complète
        full_url = f"{service_url}{target_path}"
    except Exception as e:
        logger.error(f"Erreur lors de la résolution de la route /{path}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route non trouvée: /{path}"
        )
    
    # Préparer les headers
    headers = dict(request.headers)
    
    # Ajouter les informations utilisateur si authentifié
    if current_user:
        headers["X-User-ID"] = str(current_user["user_id"])
        headers["X-Tenant-ID"] = str(current_user["tenant_id"])
        headers["X-User-Email"] = current_user.get("email", "")
        
        # LOG pour débugger
        logger.info(f"User authenticated: {current_user['email']}, Tenant: {current_user['tenant_id']}")
    
    # Nettoyer les headers problématiques
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # Lire le body de la requête
    body = await request.body()
    
    # Effectuer la requête vers le service backend
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=full_url,
                content=body,
                headers=headers,
                params=dict(request.query_params)
            )
            
            # Logger la requête avec mapping
            logger.info(f"Proxy: {request.method} /{path} → {full_url} ({response.status_code})")
            
            # Retourner la réponse dans le format attendu par le frontend
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
            
        except httpx.TimeoutException:
            logger.error(f"Timeout lors de la requête vers {service_url}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Le service backend a mis trop de temps à répondre"
            )
        except httpx.RequestError as e:
            logger.error(f"Erreur de communication avec {service_url}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service temporairement indisponible: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Erreur inattendue lors du proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur interne du gateway"
            )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=GATEWAY_HOST,
        port=GATEWAY_PORT,
        reload=DEBUG,
        log_level="info"
    ) 