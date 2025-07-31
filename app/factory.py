"""
App Factory - Configuration et création de l'application FastAPI
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import DEBUG, GATEWAY_HOST, GATEWAY_PORT
from .endpoints import static_router  
from .proxy import proxy_request

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Factory pour créer l'application FastAPI avec toute sa configuration
    """
    # Création de l'application FastAPI
    app = FastAPI(
        title="Beenaya API Gateway", 
        description="Point d'entrée centralisé pour l'architecture SOA avec compatibilité frontend",
        version="1.0.0",
        docs_url="/docs" if DEBUG else None,
        redoc_url="/redoc" if DEBUG else None
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