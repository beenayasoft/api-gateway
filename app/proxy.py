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
    import time
    
    # 🎯 AUDIT LATENCE - Start gateway timing
    gateway_start = time.time()
    logger.info(f"[GATEWAY AUDIT] START - {request.method} /{path}")
    
    # Résoudre le service cible (avec routage O(1) optimisé)
    try:
        service_url, target_path = router.resolve_service(f"/{path}")
        full_url = f"{service_url}{target_path}"
        
        # 🎯 AUDIT - Timing routing
        routing_time = time.time()
        logger.info(f"[GATEWAY AUDIT] Routing: {(routing_time - gateway_start)*1000:.2f}ms -> {full_url}")
        
    except Exception as e:
        logger.warning(f"❌ Route non trouvée: /{path} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route non trouvée: /{path}"
        )
    
    # 🎯 AUDIT - Timing headers preparation
    headers_start = time.time()
    
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
    
    headers_time = time.time()
    logger.info(f"[GATEWAY AUDIT] Headers preparation: {(headers_time - headers_start)*1000:.2f}ms")
    
    # 🎯 AUDIT - Timing body read
    body_start = time.time()
    
    # Body optimisé (sans log verbeux)
    body = await request.body()
    
    body_time = time.time()
    logger.info(f"[GATEWAY AUDIT] Body read ({len(body)} bytes): {(body_time - body_start)*1000:.2f}ms")
    
    # 🎯 AUDIT - Timing backend request
    backend_start = time.time()
    
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
            
            backend_time = time.time()
            logger.info(f"[GATEWAY AUDIT] Backend request: {(backend_time - backend_start)*1000:.2f}ms -> {response.status_code}")
            
            # Log condensé pour production (INFO level seulement pour erreurs)
            logger.debug(f"✅ {request.method} /{path} → {response.status_code}")
            
            # 🎯 AUDIT - Timing response processing
            response_proc_start = time.time()
            
            # OPTIMISATION: Headers response streamlined
            response_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in ['content-encoding', 'transfer-encoding', 'connection']
            }
            
            # Create response
            final_response = Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type', 'application/json')
            )
            
            # 🎯 AUDIT - Final timing
            gateway_end = time.time()
            total_time = (gateway_end - gateway_start) * 1000
            response_proc_time = (gateway_end - response_proc_start) * 1000
            
            logger.info(f"[GATEWAY AUDIT] Response processing: {response_proc_time:.2f}ms")
            logger.info(f"[GATEWAY AUDIT] TOTAL GATEWAY TIME: {total_time:.2f}ms")
            
            return final_response
            
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