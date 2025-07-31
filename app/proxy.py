"""
Proxy Logic - Logique de proxy principal vers les microservices
"""
import logging
from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import Response
import httpx

from .router import router
from .auth import get_current_user

logger = logging.getLogger(__name__)


async def proxy_request(
    request: Request, 
    path: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Proxy intelligent avec compatibilité frontend existant
    """
    logger.info(f"🚀 PROXY_REQUEST: START - Method: {request.method}, Path: /{path}")
    logger.info(f"🚀 PROXY_REQUEST: Headers: {dict(request.headers)}")
    logger.info(f"🚀 PROXY_REQUEST: Query params: {dict(request.query_params)}")
    
    # Résoudre le service cible (avec mapping de compatibilité)
    try:
        logger.info(f"🔍 PROXY_REQUEST: Calling router.resolve_service('/{path}')")
        service_url, target_path = router.resolve_service(f"/{path}")
        
        # Log détaillé pour le débogage
        logger.info(f"✅ PROXY_REQUEST: Route résolue - /{path} -> service: {service_url}, path: {target_path}")
        
        # Construire l'URL complète
        full_url = f"{service_url}{target_path}"
        logger.info(f"✅ PROXY_REQUEST: URL complète construite - {full_url}")
        
    except Exception as e:
        logger.error(f"❌ PROXY_REQUEST: Erreur lors de la résolution de la route /{path}: {str(e)}")
        logger.error(f"❌ PROXY_REQUEST: Exception type: {type(e).__name__}")
        logger.error(f"❌ PROXY_REQUEST: Exception args: {e.args}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route non trouvée: /{path}"
        )
    
    # Préparer les headers
    headers = dict(request.headers)
    logger.info(f"📋 PROXY_REQUEST: Headers initiaux - {headers}")
    
    # Ajouter les informations utilisateur si authentifié
    if current_user:
        headers["X-User-ID"] = str(current_user["user_id"])
        headers["X-Tenant-ID"] = str(current_user["tenant_id"])
        headers["X-User-Email"] = current_user.get("email", "")
        
        # LOG pour débugger
        logger.info(f"🔐 PROXY_REQUEST: User authenticated - {current_user['email']}, Tenant: {current_user['tenant_id']}")
    else:
        logger.info(f"🔐 PROXY_REQUEST: No user authentication")
    
    # Nettoyer les headers problématiques
    headers.pop("host", None)
    headers.pop("content-length", None)
    logger.info(f"📋 PROXY_REQUEST: Headers nettoyés - {headers}")
    
    # Lire le body de la requête
    body = await request.body()
    logger.info(f"📄 PROXY_REQUEST: Body length: {len(body)} bytes")
    if body and len(body) < 1000:  # Log only small bodies
        logger.info(f"📄 PROXY_REQUEST: Body content: {body.decode('utf-8', errors='ignore')}")
    
    # Effectuer la requête vers le service backend
    logger.info(f"🌐 PROXY_REQUEST: Envoi requête vers {full_url}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info(f"🌐 PROXY_REQUEST: httpx.request - method: {request.method}, url: {full_url}")
            logger.info(f"🌐 PROXY_REQUEST: httpx.request - headers: {headers}")
            logger.info(f"🌐 PROXY_REQUEST: httpx.request - params: {dict(request.query_params)}")
            
            response = await client.request(
                method=request.method,
                url=full_url,
                content=body,
                headers=headers,
                params=dict(request.query_params)
            )
            
            # Logger la requête avec mapping
            logger.info(f"✅ PROXY_REQUEST: Response reçue - {request.method} /{path} → {full_url} ({response.status_code})")
            logger.info(f"✅ PROXY_REQUEST: Response headers - {dict(response.headers)}")
            
            # Log response content if small
            if response.content and len(response.content) < 1000:
                logger.info(f"✅ PROXY_REQUEST: Response content - {response.content.decode('utf-8', errors='ignore')}")
            
            # Retourner la réponse directement sans re-sérialisation
            logger.info(f"✅ PROXY_REQUEST: Returning response with status {response.status_code}")
            
            # Préparer les headers de réponse
            response_headers = {}
            for key, value in response.headers.items():
                if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection']:
                    response_headers[key] = value
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type', 'application/json')
            )
            
        except httpx.TimeoutException as e:
            logger.error(f"❌ PROXY_REQUEST: Timeout lors de la requête vers {service_url} - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Le service backend a mis trop de temps à répondre"
            )
        except httpx.RequestError as e:
            logger.error(f"❌ PROXY_REQUEST: Erreur de communication avec {service_url} - {str(e)}")
            logger.error(f"❌ PROXY_REQUEST: RequestError details - {e.__class__.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service temporairement indisponible: {str(e)}"
            )
        except Exception as e:
            logger.error(f"❌ PROXY_REQUEST: Erreur inattendue lors du proxy - {str(e)}")
            logger.error(f"❌ PROXY_REQUEST: Exception type: {type(e).__name__}")
            logger.error(f"❌ PROXY_REQUEST: Exception args: {e.args}")
            import traceback
            logger.error(f"❌ PROXY_REQUEST: Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur interne du gateway"
            )