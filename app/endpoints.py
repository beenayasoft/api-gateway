"""
Endpoints statiques - Routes qui ne nécessitent pas de proxy
Intégration Service Registry et Service Discovery
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import DEBUG
from .service_registry import service_registry
from .service_discovery import service_discovery
from .circuit_breaker import circuit_breaker_manager
from .distributed_tracing import gateway_tracer

logger = logging.getLogger(__name__)

# Router pour les endpoints statiques
static_router = APIRouter()


# Modèles Pydantic pour validation
class ServiceRegistration(BaseModel):
    service_name: str
    instance_id: str
    host: str
    port: int
    health_endpoint: str = "/health/"
    routes: List[str] = []
    metadata: Dict[str, Any] = {}


class HeartbeatRequest(BaseModel):
    service_name: str
    instance_id: str


@static_router.get("/")
async def gateway_info():
    """Informations sur l'API Gateway avec Service Registry"""
    
    registry_stats = service_registry.get_registry_stats()
    
    return {
        "service": "Beenaya API Gateway",
        "version": "2.0.0",  # Version avec Service Registry
        "status": "operational",
        "features": [
            "Service Registry dynamique",
            "Load Balancing round-robin", 
            "Health Check automatique",
            "Découverte de services",
            "Compatibilité legacy"
        ],
        "documentation": "/docs" if DEBUG else "disabled",
        "service_registry": {
            "enabled": True,
            "services_registered": registry_stats["total_services"],
            "instances_total": registry_stats["total_instances"],
            "instances_healthy": registry_stats["healthy_instances"]
        },
        "endpoints": {
            "health": "/health/",
            "registry": "/registry/",
            "service_registration": "/registry/register",
            "discovery_stats": "/discovery/stats",
            "service_resolution_test": "/discovery/resolve/{path}",
            "circuit_breakers": "/circuit-breakers/",
            "circuit_breaker_stats": "/circuit-breakers/stats",
            "distributed_tracing": "/tracing/",
            "traces": "/tracing/traces"
        }
    }


@static_router.get("/health/")
async def health_check():
    """
    Health check global de l'API Gateway et des services backend via Service Discovery
    """
    logger.info("🔍 Health check avec Service Discovery")
    
    try:
        # Obtenir l'état via Service Discovery
        health_data = await service_discovery.get_service_health()
        
        # Déterminer le status code global
        registry_stats = health_data.get("service_registry", {})
        healthy_instances = registry_stats.get("healthy_instances", 0)
        total_instances = registry_stats.get("total_instances", 0)
        
        if total_instances == 0:
            status_code = 503  # Aucun service disponible
        elif healthy_instances == total_instances:
            status_code = 200  # Tout va bien
        elif healthy_instances > 0:
            status_code = 206  # Partiellement disponible
        else:
            status_code = 503  # Tous les services sont down
        
        logger.info(f"✅ Health check completed: {healthy_instances}/{total_instances} services healthy")
        return JSONResponse(content=health_data, status_code=status_code)
        
    except Exception as e:
        logger.error(f"💥 Health check failed: {e}")
        error_response = {
            "service_discovery": {"status": "error", "message": str(e)},
            "service_registry": {"status": "error"},
            "services": {}
        }
        return JSONResponse(content=error_response, status_code=503)


# ==================== SERVICE REGISTRY ENDPOINTS ====================

@static_router.post("/registry/register", response_model=Dict[str, str])
async def register_service(registration: ServiceRegistration):
    """
    Enregistre un nouveau service dans le registre
    """
    try:
        success = service_registry.register_service(
            service_name=registration.service_name,
            instance_id=registration.instance_id,
            host=registration.host,
            port=registration.port,
            health_endpoint=registration.health_endpoint,
            routes=registration.routes,
            metadata=registration.metadata
        )
        
        if success:
            logger.info(f"✅ Service enregistré: {registration.service_name}#{registration.instance_id}")
            return {
                "status": "registered",
                "service": registration.service_name,
                "instance": registration.instance_id,
                "url": f"http://{registration.host}:{registration.port}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Échec de l'enregistrement du service"
            )
            
    except Exception as e:
        logger.error(f"💥 Erreur enregistrement service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'enregistrement: {str(e)}"
        )


@static_router.delete("/registry/{service_name}/{instance_id}")
async def unregister_service(service_name: str, instance_id: str):
    """
    Désenregistre un service du registre
    """
    success = service_registry.unregister_service(service_name, instance_id)
    
    if success:
        logger.info(f"✅ Service désenregistré: {service_name}#{instance_id}")
        return {
            "status": "unregistered",
            "service": service_name,
            "instance": instance_id
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service non trouvé: {service_name}#{instance_id}"
        )


@static_router.post("/registry/heartbeat")
async def heartbeat(heartbeat: HeartbeatRequest):
    """
    Met à jour le heartbeat d'un service
    """
    success = service_registry.heartbeat(heartbeat.service_name, heartbeat.instance_id)
    
    if success:
        return {
            "status": "heartbeat_updated",
            "service": heartbeat.service_name,
            "instance": heartbeat.instance_id,
            "timestamp": "now"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service non trouvé: {heartbeat.service_name}#{heartbeat.instance_id}"
        )


@static_router.get("/registry/", response_model=Dict[str, Any])
async def get_service_registry():
    """
    Retourne l'état complet du service registry
    """
    return {
        "registry": service_registry.get_all_services(),
        "stats": service_registry.get_registry_stats()
    }


@static_router.get("/registry/{service_name}")
async def discover_service_instances(service_name: str):
    """
    Découvre toutes les instances d'un service spécifique
    """
    instances = service_registry.discover_service(service_name)
    
    return {
        "service_name": service_name,
        "instances_count": len(instances),
        "instances": [
            {
                "instance_id": instance.instance_id,
                "url": instance.url,
                "status": instance.status,
                "last_heartbeat": instance.last_heartbeat.isoformat() if instance.last_heartbeat else None,
                "routes": instance.routes
            }
            for instance in instances
        ]
    }


# ==================== SERVICE DISCOVERY ENDPOINTS ====================

@static_router.get("/discovery/stats")
async def get_discovery_stats():
    """
    Statistiques du système de découverte de services
    """
    return service_discovery.get_discovery_stats()


@static_router.get("/discovery/resolve/{path:path}")
async def test_service_resolution(path: str):
    """
    Teste la résolution d'une route (utile pour débug)
    """
    try:
        service_url, target_path = await service_discovery.resolve_service_dynamic(f"/{path}")
        return {
            "original_path": f"/{path}",
            "resolved_service_url": service_url,
            "target_path": target_path,
            "full_url": f"{service_url}{target_path}"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur résolution: {str(e)}"
        )


# ==================== LEGACY ENDPOINTS (Compatibilité) ====================

@static_router.get("/api/quotes/vat-rates/", include_in_schema=True)
async def vat_rates_endpoint():
    """
    Endpoint pour les taux de TVA (compatibilité - France par défaut)
    """
    logger.info("Accès à l'endpoint des taux de TVA (FR par défaut)")
    
    # Taux de TVA français directement (pour éviter l'erreur d'import)
    fr_vat_rates = [
        {
            'id': 'fr_vat_0',
            'code': "0", 
            'name': "Exonéré", 
            'rate': 0.0,
            'rate_display': "0%",
            'description': "Exonéré de TVA",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'fr_vat_5_5',
            'code': "5.5", 
            'name': "Taux réduit", 
            'rate': 5.5,
            'rate_display': "5,5%",
            'description': "Taux réduit (travaux d'amélioration énergétique)",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'fr_vat_10',
            'code': "10", 
            'name': "Taux intermédiaire", 
            'rate': 10.0,
            'rate_display': "10%",
            'description': "Taux intermédiaire (travaux, restauration)",
            'is_default': False,
            'is_active': True
        },
        {
            'id': 'fr_vat_20',
            'code': "20", 
            'name': "Taux normal", 
            'rate': 20.0,
            'rate_display': "20%",
            'description': "Taux normal français",
            'is_default': True,
            'is_active': True
        }
    ]
    
    return fr_vat_rates


@static_router.get("/vat-rates/default/", include_in_schema=True)
async def vat_rates_default_endpoint():
    """
    Endpoint pour récupérer le taux de TVA par défaut
    """
    logger.info("Accès à l'endpoint du taux de TVA par défaut")
    
    # Retourner le taux de TVA par défaut
    default_vat_rate = {
        'id': 'default_20',
        'code': "20", 
        'name': "20%", 
        'rate': 20.0,
        'rate_display': "20%",
        'description': "Taux de TVA par défaut à 20%",
        'is_default': True,
        'is_active': True
    }
    
    return default_vat_rate


# ==================== CIRCUIT BREAKER ENDPOINTS ====================

@static_router.get("/circuit-breakers/")
async def get_circuit_breakers_stats():
    """
    Statistiques de tous les circuit breakers
    """
    return circuit_breaker_manager.get_all_stats()


@static_router.get("/circuit-breakers/health")
async def get_circuit_breakers_health():
    """
    Health check des circuit breakers
    """
    return await circuit_breaker_manager.health_check_all_circuits()


@static_router.post("/circuit-breakers/{service_name}/reset")
async def reset_circuit_breaker(service_name: str):
    """
    Remet à zéro un circuit breaker spécifique
    """
    circuit = circuit_breaker_manager.get_circuit(service_name)
    await circuit.reset()
    
    return {
        "status": "reset",
        "service": service_name,
        "message": f"Circuit breaker {service_name} remis à zéro"
    }


@static_router.post("/circuit-breakers/reset-all")
async def reset_all_circuit_breakers():
    """
    Remet à zéro tous les circuit breakers
    """
    await circuit_breaker_manager.reset_all_circuits()
    
    return {
        "status": "reset_all",
        "message": "Tous les circuit breakers ont été remis à zéro"
    }


@static_router.post("/circuit-breakers/{service_name}/force-open")
async def force_open_circuit_breaker(service_name: str):
    """
    Force l'ouverture d'un circuit breaker (pour maintenance)
    """
    circuit = circuit_breaker_manager.get_circuit(service_name)
    await circuit.force_open()
    
    return {
        "status": "forced_open",
        "service": service_name,
        "message": f"Circuit breaker {service_name} forcé en ouverture"
    }


@static_router.get("/circuit-breakers/{service_name}")
async def get_circuit_breaker_stats(service_name: str):
    """
    Statistiques d'un circuit breaker spécifique
    """
    circuit = circuit_breaker_manager.get_circuit(service_name)
    return circuit.get_stats()


# ==================== DISTRIBUTED TRACING ENDPOINTS ====================

@static_router.get("/tracing/")
async def get_tracing_stats():
    """
    Statistiques du système de tracing distribué
    """
    return gateway_tracer.get_stats()


@static_router.get("/tracing/traces")
async def get_traces(
    limit: int = 100,
    service_name: str = None,
    status: str = None,
    min_duration: float = None
):
    """
    Récupère les traces avec filtres optionnels
    """
    if service_name or status or min_duration:
        return gateway_tracer.search_traces(
            service_name=service_name,
            status=status,
            min_duration=min_duration,
            limit=limit
        )
    else:
        return gateway_tracer.get_completed_traces(limit)


@static_router.get("/tracing/traces/active")
async def get_active_traces():
    """
    Récupère toutes les traces actives
    """
    return gateway_tracer.get_active_traces()


@static_router.get("/tracing/traces/{trace_id}")
async def get_trace_by_id(trace_id: str):
    """
    Récupère une trace spécifique avec son arbre complet
    """
    trace = gateway_tracer.get_trace_by_id(trace_id)
    if trace:
        return trace
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace non trouvée: {trace_id}"
        )


@static_router.post("/tracing/search")
async def search_traces(
    service_name: str = None,
    operation_name: str = None,
    status: str = None,
    min_duration: float = None,
    limit: int = 50
):
    """
    Recherche avancée de traces
    """
    return gateway_tracer.search_traces(
        service_name=service_name,
        operation_name=operation_name,
        status=status,
        min_duration=min_duration,
        limit=limit
    )