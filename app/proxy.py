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
    Proxy intelligent OPTIMISÉ - Milestone 2.2: Logs réduits + Headers streamlined
    """
    # OPTIMISATION: Logs condensés (DEBUG level pour détails)
    logger.debug(f"🚀 {request.method} /{path} → routing...")
    
    # Résoudre le service cible (avec routage O(1) optimisé)
    try:
        service_url, target_path = router.resolve_service(f"/{path}")
        full_url = f"{service_url}{target_path}"
        logger.debug(f"⚡ Route: /{path} → {full_url}")
        
    except Exception as e:
        logger.warning(f"❌ Route non trouvée: /{path} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route non trouvée: /{path}"
        )
    
    # OPTIMISATION: Headers streamlined (éviter copies inutiles)
    headers = {
        k: v for k, v in request.headers.items() 
        if k.lower() not in ['host', 'content-length', 'content-encoding', 'transfer-encoding']
    }
    
    # Ajouter auth headers si authentifié (optimisé)
    if current_user:
        headers.update({
            "X-User-ID": str(current_user["user_id"]),
            "X-Tenant-ID": str(current_user["tenant_id"]),
            "X-User-Email": current_user.get("email", "")
        })
        logger.debug(f"🔐 Auth: {current_user['email']} → {current_user['tenant_id']}")
    
    # Body optimisé (sans log verbeux)
    body = await request.body()
    logger.debug(f"📄 Body: {len(body)} bytes")
    
    # OPTIMISATION: Requête streamlined avec timeout optimisé
    async with httpx.AsyncClient(timeout=15.0) as client:  # Timeout réduit 30s → 15s
        try:
            response = await client.request(
                method=request.method,
                url=full_url,
                content=body,
                headers=headers,
                params=dict(request.query_params)
            )
            
            # Log condensé pour production (INFO level seulement pour erreurs)
            logger.debug(f"✅ {request.method} /{path} → {response.status_code}")
            
            # OPTIMISATION: Headers response streamlined
            response_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in ['content-encoding', 'transfer-encoding', 'connection']
            }
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type', 'application/json')
            )
            
        except httpx.TimeoutException:
            logger.warning(f"⏱️ Timeout: {request.method} /{path} → {service_url}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Service timeout"
            )
        except httpx.RequestError as e:
            logger.warning(f"🔌 Service error: {request.method} /{path} → {service_url} - {type(e).__name__}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable"
            )
        except Exception as e:
            logger.error(f"💥 Gateway error: {request.method} /{path} - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gateway error"
            )