"""
Middleware pour l'authentification JWT
"""
import jwt
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from config import JWT_SECRET_KEY, JWT_ALGORITHM, PUBLIC_ROUTES

logger = logging.getLogger(__name__)

class JWTMiddleware:
    """Middleware pour gérer l'authentification JWT"""
    
    @staticmethod
    def is_public_route(path: str, method: str) -> bool:
        """Vérifie si une route est publique"""
        logger.info(f"🔒 IS_PUBLIC_ROUTE: Checking path='{path}', method='{method}'")
        
        # Routes toujours publiques
        for public_route in PUBLIC_ROUTES:
            if path.startswith(public_route):
                logger.info(f"✅ IS_PUBLIC_ROUTE: Match found in PUBLIC_ROUTES - '{public_route}'")
                return True
        
        # GET sur tenants (lecture publique pour validation)
        if path.startswith("/api/tenants/") and method == "GET":
            logger.info(f"✅ IS_PUBLIC_ROUTE: GET tenant route - public")
            return True
            
        # Routes VAT (explicitement publiques)
        if path == "/api/quotes/vat-rates/" or path == "/vat-rates/":
            logger.info(f"✅ IS_PUBLIC_ROUTE: VAT rates route - public")
            return True
        
        logger.info(f"❌ IS_PUBLIC_ROUTE: Route not public - authentication required")
        logger.info(f"❌ IS_PUBLIC_ROUTE: Available PUBLIC_ROUTES: {PUBLIC_ROUTES}")
        return False
    
    @staticmethod
    def extract_token(authorization: Optional[str]) -> Optional[str]:
        """Extrait le token JWT du header Authorization"""
        logger.info(f"🔓 EXTRACT_TOKEN: Authorization header - {'Present' if authorization else 'None'}")
        
        if not authorization:
            logger.info(f"❌ EXTRACT_TOKEN: No authorization header")
            return None
            
        try:
            auth_parts = authorization.split()
            logger.info(f"🔓 EXTRACT_TOKEN: Split authorization into {len(auth_parts)} parts")
            
            if len(auth_parts) != 2:
                logger.error(f"❌ EXTRACT_TOKEN: Invalid authorization format - expected 2 parts, got {len(auth_parts)}")
                return None
                
            auth_type, token = auth_parts
            logger.info(f"🔓 EXTRACT_TOKEN: Auth type='{auth_type}', token length={len(token)}")
            
            if auth_type.lower() != "bearer":
                logger.error(f"❌ EXTRACT_TOKEN: Invalid auth type - expected 'bearer', got '{auth_type.lower()}'")
                return None
            
            logger.info(f"✅ EXTRACT_TOKEN: Token extracted successfully")
            return token
        except ValueError as e:
            logger.error(f"❌ EXTRACT_TOKEN: ValueError splitting authorization - {str(e)}")
            return None
    
    @staticmethod
    def validate_token(token: str) -> Dict[str, Any]:
        """
        Valide un token JWT et retourne les informations utilisateur
        
        Raises:
            HTTPException: Si le token est invalide
        """
        logger.info(f"🔐 VALIDATE_TOKEN: Starting token validation - token length: {len(token)}")
        
        try:
            logger.info(f"🔐 VALIDATE_TOKEN: Decoding JWT with algorithm {JWT_ALGORITHM}")
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )
            
            logger.info(f"🔐 VALIDATE_TOKEN: JWT decoded successfully - payload keys: {list(payload.keys())}")
            
            # Vérifier les champs obligatoires
            user_id = payload.get("user_id")
            tenant_id = payload.get("tenant_id")
            
            logger.info(f"🔐 VALIDATE_TOKEN: user_id={'Present' if user_id else 'Missing'}, tenant_id={'Present' if tenant_id else 'Missing'}")
            
            if not user_id or not tenant_id:
                logger.error(f"❌ VALIDATE_TOKEN: Missing required fields - user_id: {user_id}, tenant_id: {tenant_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token JWT valide mais informations utilisateur manquantes"
                )
            
            user_data = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "email": payload.get("email"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
            
            logger.info(f"✅ VALIDATE_TOKEN: Token validation successful - user_id: {user_id}, tenant_id: {tenant_id}")
            return user_data
            
        except jwt.ExpiredSignatureError as e:
            logger.error(f"❌ VALIDATE_TOKEN: Token expired - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token JWT expiré"
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ VALIDATE_TOKEN: Invalid token - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token JWT invalide"
            )
        except Exception as e:
            logger.error(f"❌ VALIDATE_TOKEN: Unexpected error - {str(e)}")
            logger.error(f"❌ VALIDATE_TOKEN: Exception type: {type(e).__name__}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Erreur de validation du token"
            ) 