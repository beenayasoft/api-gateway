"""
Authentication Logic - Gestion de l'authentification JWT
"""
import logging
from fastapi import Request, HTTPException, status
from middleware import JWTMiddleware

logger = logging.getLogger(__name__)


async def get_current_user(request: Request):
    """
    Dependency pour extraire et valider l'utilisateur à partir du JWT
    Compatible avec le frontend existant
    """
    logger.info(f"🔐 GET_CURRENT_USER: START - {request.method} {request.url.path}")
    
    # Vérifier si la route est publique
    is_public = JWTMiddleware.is_public_route(request.url.path, request.method)
    logger.info(f"🔐 GET_CURRENT_USER: Route publique check - {is_public}")
    
    if is_public:
        logger.info(f"✅ GET_CURRENT_USER: Route publique accédée - {request.method} {request.url.path}")
        return None
    
    # Extraire le token
    authorization = request.headers.get("authorization")
    logger.info(f"🔐 GET_CURRENT_USER: Authorization header - {'Present' if authorization else 'Missing'}")
    if authorization:
        logger.info(f"🔐 GET_CURRENT_USER: Authorization header value - {authorization[:20]}...")
    
    token = JWTMiddleware.extract_token(authorization)
    logger.info(f"🔐 GET_CURRENT_USER: Token extracted - {'Present' if token else 'Missing'}")
    
    if not token:
        # Pour compatibilité frontend, retourner 401 avec format attendu
        logger.warning(f"❌ GET_CURRENT_USER: Accès non authentifié à une route protégée - {request.method} {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification requis",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Valider le token et retourner les informations utilisateur
    try:
        logger.info(f"🔐 GET_CURRENT_USER: Validating token...")
        user = JWTMiddleware.validate_token(token)
        logger.info(f"✅ GET_CURRENT_USER: Token valid - user_id: {user.get('user_id')}, tenant_id: {user.get('tenant_id')}")
        return user
    except Exception as e:
        logger.error(f"❌ GET_CURRENT_USER: Token validation failed - {str(e)}")
        raise