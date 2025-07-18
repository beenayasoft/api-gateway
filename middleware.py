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
        
        # Routes toujours publiques
        for public_route in PUBLIC_ROUTES:
            if path.startswith(public_route):
                return True
        
        # GET sur tenants (lecture publique pour validation)
        if path.startswith("/api/tenants/") and method == "GET":
            return True
            
        # Routes VAT (explicitement publiques)
        if path == "/api/quotes/vat-rates/" or path == "/vat-rates/":
            return True
            
        return False
    
    @staticmethod
    def extract_token(authorization: Optional[str]) -> Optional[str]:
        """Extrait le token JWT du header Authorization"""
        
        if not authorization:
            return None
            
        try:
            auth_type, token = authorization.split()
            if auth_type.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None
    
    @staticmethod
    def validate_token(token: str) -> Dict[str, Any]:
        """
        Valide un token JWT et retourne les informations utilisateur
        
        Raises:
            HTTPException: Si le token est invalide
        """
        
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )
            
            # Vérifier les champs obligatoires
            user_id = payload.get("user_id")
            tenant_id = payload.get("tenant_id")
            
            if not user_id or not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token JWT valide mais informations utilisateur manquantes"
                )
            
            return {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "email": payload.get("email"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token JWT expiré"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token JWT invalide"
            )
        except Exception as e:
            logger.error(f"Erreur lors de la validation du token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Erreur de validation du token"
            ) 