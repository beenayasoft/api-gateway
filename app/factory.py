"""
App Factory - Configuration et création de l'application FastAPI
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import DEBUG, GATEWAY_HOST, GATEWAY_PORT
from .endpoints import static_router  
from .proxy import proxy_request
from .service_registry import service_registry
from .service_discovery import service_discovery

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application
    Démarre et arrête le Service Registry
    """
    logger.info("🚀 Démarrage de l'API Gateway avec Service Registry")
    
    # Démarrer le Service Registry
    await service_registry.start()
    
    # Enregistrer les services par défaut
    await service_discovery.register_default_services()
    
    logger.info("✅ Service Registry initialisé")
    
    yield  # L'application est maintenant active
    
    # Cleanup au shutdown
    logger.info("🛑 Arrêt du Service Registry")
    await service_registry.stop()


def create_app() -> FastAPI:
    """
    Factory pour créer l'application FastAPI avec toute sa configuration
    """
    # Création de l'application FastAPI avec lifespan
    app = FastAPI(
        title="Beenaya API Gateway", 
        description="Point d'entrée centralisé pour l'architecture SOA avec Service Registry",
        version="2.0.0",  # Version avec Service Registry
        docs_url="/docs" if DEBUG else None,
        redoc_url="/redoc" if DEBUG else None,
        lifespan=lifespan
    )
    
    # Configuration CORS pour le frontend
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
    
    # Inclure les routes statiques
    app.include_router(static_router)
    
    # Route de proxy catch-all (doit être la dernière)
    app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])(proxy_request)
    
    logger.info("✅ API Gateway application créée avec succès")
    return app


def get_server_config() -> dict:
    """
    Configuration pour le serveur uvicorn
    """
    return {
        "host": GATEWAY_HOST,
        "port": GATEWAY_PORT,
        "reload": DEBUG,
        "log_level": "info"
    }