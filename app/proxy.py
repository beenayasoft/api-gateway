"""
Proxy Logic - Logique de proxy principal vers les microservices
SOA 100% avec Service Discovery + Circuit Breaker + Distributed Tracing
"""
import logging
import time
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
import httpx

from .service_discovery import service_discovery
from .auth import get_current_user
from .circuit_breaker import circuit_breaker_manager, CircuitBreakerOpenError, CircuitBreakerConfig
from .distributed_tracing import gateway_tracer, TracingMiddleware

logger = logging.getLogger(__name__)


async def proxy_request(
    request: Request, 
    path: str
):
    """
    Proxy intelligent SOA 100% - Service Discovery + Circuit Breaker + Distributed Tracing
    """
    # 🎯 AUDIT LATENCE - Start gateway timing
    gateway_start = time.time()
    
    # 📊 DISTRIBUTED TRACING - Initialiser le tracing
    tracing_middleware = TracingMiddleware(gateway_tracer)
    trace_context = tracing_middleware.extract_trace_headers(dict(request.headers))
    
    # Démarrer le span principal pour cette requête
    with gateway_tracer.trace_operation(
        operation_name=f"{request.method} /{path}",
        trace_id=trace_context["trace_id"],
        parent_span_id=trace_context["parent_span_id"],
        tags={
            "http.method": request.method,
            "http.url": str(request.url),
            "service.name": "api-gateway",
            "component": "proxy"
        }
    ) as main_span:
        
        main_span.add_log(f"Requête reçue: {request.method} /{path}")
        logger.info(f"[GATEWAY AUDIT] START - {request.method} /{path} (trace:{main_span.trace_id[:8]})")
        
        # 1. RÉSOLUTION DE SERVICE
        try:
            with gateway_tracer.trace_operation(
                operation_name="service_resolution",
                trace_id=main_span.trace_id,
                parent_span_id=main_span.span_id,
                tags={"component": "service-discovery"}
            ) as resolution_span:
                service_url, target_path = await service_discovery.resolve_service_dynamic(f"/{path}")
                resolution_span.add_tag("resolved_service_url", service_url)
                resolution_span.add_tag("target_path", target_path)
            
            full_url = f"{service_url}{target_path}"
            routing_time = time.time()
            logger.info(f"[GATEWAY AUDIT] Service Discovery: {(routing_time - gateway_start)*1000:.2f}ms -> {full_url}")
            main_span.add_log(f"Service résolu: {service_url}")
            
        except HTTPException:
            main_span.add_log("Erreur résolution service", "error")
            raise
        except Exception as e:
            main_span.add_log(f"Erreur résolution service: {str(e)}", "error")
            logger.warning(f"❌ Erreur résolution service: /{path} - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service indisponible pour la route: /{path}"
            )
        
        # 2. AUTHENTIFICATION
        auth_start = time.time()
        try:
            with gateway_tracer.trace_operation(
                operation_name="authentication",
                trace_id=main_span.trace_id,
                parent_span_id=main_span.span_id,
                tags={"component": "auth"}
            ) as auth_span:
                current_user = await get_current_user(request)
                if current_user:
                    auth_span.add_tag("user_id", current_user.get("user_id"))
                    auth_span.add_tag("tenant_id", current_user.get("tenant_id"))
                
        except HTTPException as e:
            main_span.add_log("Erreur authentification", "error")
            raise e
        except Exception as e:
            main_span.add_log(f"Erreur authentification: {str(e)}", "error")
            logger.error(f"💥 Erreur authentification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur d'authentification"
            )
        
        auth_time = time.time()
        logger.info(f"[GATEWAY AUDIT] Authentication: {(auth_time - auth_start)*1000:.2f}ms")
        
        # 3. PRÉPARATION DES HEADERS
        headers_start = time.time()
        headers = {
            k: v for k, v in request.headers.items() 
            if k.lower() not in ['host', 'content-length', 'content-encoding', 'transfer-encoding']
        }
        
        # Ajouter auth headers
        if current_user:
            auth_token = request.headers.get("authorization", "")
            headers.update({
                "X-User-ID": str(current_user["user_id"]),
                "X-Tenant-ID": str(current_user["tenant_id"]),
                "X-User-Email": current_user.get("email", ""),
                "X-Auth-Token": auth_token
            })
            logger.info(f"🔐 Auth headers: {current_user['email']} → {current_user['tenant_id']}")
        
        # Injecter headers de tracing
        headers = tracing_middleware.inject_trace_headers(
            headers, main_span.trace_id, main_span.span_id
        )
        
        headers_time = time.time()
        logger.info(f"[GATEWAY AUDIT] Headers: {(headers_time - headers_start)*1000:.2f}ms")
        
        # 4. LECTURE DU BODY
        body_start = time.time()
        body = await request.body()
        body_time = time.time()
        logger.info(f"[GATEWAY AUDIT] Body ({len(body)} bytes): {(body_time - body_start)*1000:.2f}ms")
        
        # 5. APPEL BACKEND AVEC CIRCUIT BREAKER
        backend_start = time.time()
        service_name = service_discovery._extract_service_name_from_path(f"/{path}") or "unknown"
        
        # Configuration Circuit Breaker
        circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout=60.0,
            recovery_timeout=10.0,
            success_threshold=2
        )
        
        try:
            # Fonction backend protégée
            async def make_backend_request():
                with gateway_tracer.trace_operation(
                    operation_name=f"backend_call_{service_name}",
                    trace_id=main_span.trace_id,
                    parent_span_id=main_span.span_id,
                    tags={
                        "service.name": service_name,
                        "http.url": full_url,
                        "component": "http-client"
                    }
                ) as backend_span:
                    
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        backend_span.add_log(f"Appel backend: {full_url}")
                        response = await client.request(
                            method=request.method,
                            url=full_url,
                            content=body,
                            headers=headers,
                            params=dict(request.query_params)
                        )
                        backend_span.add_tag("http.status_code", response.status_code)
                        backend_span.add_tag("response.size", len(response.content))
                        return response
            
            # Fallback
            async def fallback_response():
                logger.warning(f"🔴 Fallback activé pour {service_name}")
                main_span.add_log(f"Fallback activé pour {service_name}", "warning")
                return Response(
                    content='{"error": "Service temporairement indisponible", "fallback": true}',
                    status_code=503,
                    headers={"Content-Type": "application/json"}
                )
            
            # Exécution avec Circuit Breaker
            response = await circuit_breaker_manager.call_with_circuit_breaker(
                service_name=service_name,
                func=make_backend_request,
                config=circuit_config,
                fallback=fallback_response
            )
            
            backend_time = time.time()
            logger.info(f"[GATEWAY AUDIT] Backend: {(backend_time - backend_start)*1000:.2f}ms -> {response.status_code}")
            
            main_span.add_tag("http.status_code", response.status_code)
            main_span.add_tag("backend.service", service_name)
            main_span.add_tag("backend.duration_ms", (backend_time - backend_start) * 1000)
            
            # 6. TRAITEMENT RÉPONSE
            response_proc_start = time.time()
            
            response_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in ['content-encoding', 'transfer-encoding', 'connection']
            }
            response_headers["X-Trace-ID"] = main_span.trace_id
            
            final_response = Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type', 'application/json')
            )
            
            # 7. AUDIT FINAL
            gateway_end = time.time()
            total_time = (gateway_end - gateway_start) * 1000
            response_proc_time = (gateway_end - response_proc_start) * 1000
            
            logger.info(f"[GATEWAY AUDIT] Response: {response_proc_time:.2f}ms")
            logger.info(f"[GATEWAY AUDIT] TOTAL: {total_time:.2f}ms")
            
            main_span.add_tag("total_duration_ms", total_time)
            main_span.add_log(f"Requête terminée: {response.status_code} ({total_time:.2f}ms)")
            
            return final_response
            
        except CircuitBreakerOpenError:
            main_span.add_log(f"Circuit breaker ouvert pour {service_name}", "error")
            logger.warning(f"🔴 Circuit breaker ouvert: {service_name}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {service_name} temporairement indisponible"
            )
        except httpx.TimeoutException:
            main_span.add_log("Timeout backend", "error")
            logger.warning(f"⏱️ Timeout: {request.method} /{path}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Service timeout"
            )
        except httpx.RequestError as e:
            main_span.add_log(f"Erreur réseau: {str(e)}", "error")
            logger.warning(f"🔌 Service error: {type(e).__name__}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable"
            )
        except Exception as e:
            main_span.add_log(f"Erreur gateway: {str(e)}", "error")
            logger.error(f"💥 Gateway error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gateway error"
            )