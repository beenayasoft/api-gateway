"""
API Gateway - Point d'entrée principal
Refactorisé pour une meilleure maintenabilité
"""
import logging
import uvicorn

from app.factory import create_app, get_server_config

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Création de l'application
app = create_app()

if __name__ == "__main__":
    logger.info("🚀 Démarrage de l'API Gateway Beenaya")
    server_config = get_server_config()
    uvicorn.run(app, **server_config)