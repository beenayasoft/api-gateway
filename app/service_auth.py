"""
Service-to-Service Authentication
Gestion de l'authentification entre services via l'API Gateway
"""
import logging
import jwt
import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# Secret partagé pour les communications inter-services
SERVICE_SECRET = "beenaya-soa-internal-services-secret-2024"  # TODO: Mettre en variable d'environnement

class ServiceAuthenticator:
    """Gestion de l'authentification service-to-service"""
    
    @staticmethod
    def generate_service_token(source_service: str, tenant_id: str, user_id: str = None) -> str:
        """Génère un token pour les communications inter-services"""
        payload = {
            'iss': 'api-gateway',  # Issuer
            'aud': 'beenaya-services',  # Audience
            'source_service': source_service,
            'tenant_id': tenant_id,
            'user_id': user_id,
            'iat': int(time.time()),
            'exp': int(time.time()) + 300,  # 5 minutes
            'type': 'service-to-service'
        }
        
        return jwt.encode(payload, SERVICE_SECRET, algorithm='HS256')
    
    @staticmethod
    def validate_service_token(token: str) -> Optional[Dict[str, Any]]:
        """Valide un token service-to-service"""
        try:
            if token.startswith('Bearer '):
                token = token[7:]
                
            payload = jwt.decode(token, SERVICE_SECRET, algorithms=['HS256'])
            
            # Vérifier que c'est bien un token service-to-service
            if payload.get('type') != 'service-to-service':
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Service token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid service token: {e}")
            return None
    
    @staticmethod
    def is_service_request(request: Request) -> bool:
        """Détermine si c'est une requête service-to-service"""
        # Vérifier les headers spécifiques aux services
        service_headers = [
            'X-Service-Source',  # Header ajouté par les services
            'X-Internal-Request'  # Header pour identifier les requêtes internes
        ]
        
        return any(header in request.headers for header in service_headers)
    
    @staticmethod 
    def extract_service_context(request: Request) -> Optional[Dict[str, str]]:
        """Extrait le contexte service depuis les headers"""
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return None
            
        payload = ServiceAuthenticator.validate_service_token(auth_header)
        if not payload:
            return None
            
        return {
            'source_service': payload.get('source_service'),
            'tenant_id': payload.get('tenant_id'), 
            'user_id': payload.get('user_id')
        }

def create_service_headers(tenant_id: str, user_id: str = None, user_email: str = None) -> Dict[str, str]:
    """Crée les headers pour les appels vers les services backend"""
    headers = {
        "X-Tenant-ID": str(tenant_id),
        "X-Internal-Request": "true"
    }
    
    if user_id:
        headers["X-User-ID"] = str(user_id)
        
    if user_email:
        headers["X-User-Email"] = user_email
        
    return headers