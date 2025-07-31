"""
Static Endpoints - Endpoints statiques du gateway
"""
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config import DEBUG
from .router import router

logger = logging.getLogger(__name__)

# Router pour les endpoints statiques
static_router = APIRouter()


@static_router.get("/")
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


@static_router.get("/health/")
async def health_check():
    """Health check de l'API Gateway et de tous les services"""
    
    health_data = await router.health_check_all()
    
    # Déterminer le status code
    if health_data["gateway"]["overall_status"] == "healthy":
        return JSONResponse(content=health_data, status_code=200)
    else:
        return JSONResponse(content=health_data, status_code=503)


@static_router.get("/api/quotes/vat-rates/", include_in_schema=True)
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