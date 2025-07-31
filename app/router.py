"""
Service Router - Gestion intelligente du routage vers les microservices
"""
import logging
from typing import Dict, Any, Tuple
from fastapi import HTTPException, status
import httpx
import asyncio

from config import SERVICES, LEGACY_ROUTE_MAPPING

logger = logging.getLogger(__name__)


class ServiceRouter:
    """Router intelligent avec compatibilité frontend existant"""
    
    def __init__(self):
        self.services = SERVICES
        self.legacy_mapping = LEGACY_ROUTE_MAPPING
    
    def resolve_service(self, path: str) -> Tuple[str, str]:
        """
        Résout intelligemment le service cible
        1. Vérifie d'abord le mapping de compatibilité
        2. Puis la configuration normale des services
        """
        logger.info(f"🔍 RESOLVE_SERVICE: Début résolution pour path='{path}'")
        
        # 1. Vérification mapping de compatibilité
        logger.info(f"🔍 STEP 1: Vérification mapping exact pour '{path}'")
        if path in self.legacy_mapping:
            service_name, target_path = self.legacy_mapping[path]
            logger.info(f"✅ STEP 1: Mapping exact trouvé - service='{service_name}', target='{target_path}'")
            if service_name in self.services:
                service_url = self.services[service_name]["url"]
                logger.info(f"✅ STEP 1: Service trouvé - service_url='{service_url}'")
                logger.info(f"✅ RESOLVE_SERVICE: Retour STEP 1 - url='{service_url}', path='{target_path}'")
                return service_url, target_path
            else:
                logger.error(f"❌ STEP 1: Service '{service_name}' non trouvé dans SERVICES")
        else:
            logger.info(f"ℹ️ STEP 1: Pas de mapping exact trouvé pour '{path}'")
        
        # 2. Vérification mapping par préfixe (pour routes dynamiques)
        logger.info(f"🔍 STEP 2: Vérification mapping par préfixe pour '{path}'")
        for legacy_route, (service_name, new_route) in self.legacy_mapping.items():
            legacy_route_stripped = legacy_route.rstrip('/')
            logger.debug(f"🔍 STEP 2: Test préfixe '{legacy_route}' (stripped: '{legacy_route_stripped}') vs '{path}'")
            
            if path.startswith(legacy_route_stripped):
                logger.info(f"✅ STEP 2: Préfixe match - route='{legacy_route}', service='{service_name}', new_route='{new_route}'")
                
                if service_name in self.services:
                    # Remplacer le préfixe
                    new_route_stripped = new_route.rstrip('/')
                    target_path = path.replace(legacy_route_stripped, new_route_stripped)
                    service_url = self.services[service_name]["url"]
                    
                    logger.info(f"✅ STEP 2: Transformation - '{legacy_route_stripped}' -> '{new_route_stripped}'")
                    logger.info(f"✅ STEP 2: Path final - '{path}' -> '{target_path}'")
                    logger.info(f"✅ STEP 2: Service URL - '{service_url}'")
                    logger.info(f"✅ RESOLVE_SERVICE: Retour STEP 2 - url='{service_url}', path='{target_path}'")
                    return service_url, target_path
                else:
                    logger.error(f"❌ STEP 2: Service '{service_name}' non trouvé dans SERVICES")
        
        logger.info(f"ℹ️ STEP 2: Aucun préfixe match trouvé pour '{path}'")
        
        # 3. Configuration normale des services
        logger.info(f"🔍 STEP 3: Vérification configuration normale des services pour '{path}'")
        for service_name, config in self.services.items():
            logger.debug(f"🔍 STEP 3: Test service '{service_name}' - routes: {config['routes']}")
            for route_prefix in config["routes"]:
                logger.debug(f"🔍 STEP 3: Test route_prefix '{route_prefix}' vs '{path}'")
                if path.startswith(route_prefix):
                    service_url = config["url"]
                    logger.info(f"✅ STEP 3: Match trouvé - service='{service_name}', route_prefix='{route_prefix}'")
                    logger.info(f"✅ RESOLVE_SERVICE: Retour STEP 3 - url='{service_url}', path='{path}'")
                    return service_url, path
        
        logger.error(f"❌ RESOLVE_SERVICE: Aucune route trouvée pour '{path}'")
        logger.error(f"❌ RESOLVE_SERVICE: LEGACY_MAPPING disponible: {list(self.legacy_mapping.keys())}")
        logger.error(f"❌ RESOLVE_SERVICE: SERVICES disponible: {list(self.services.keys())}")
        
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