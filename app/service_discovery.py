"""
Service Discovery - Remplace le routeur statique par découverte dynamique
Intégration du Service Registry dans l'API Gateway
"""
import logging
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urlparse
from fastapi import HTTPException, status
from decouple import config

from .service_registry import service_registry, ServiceInstance
from config import LEGACY_ROUTE_MAPPING, PUBLIC_ROUTES

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """
    Service Discovery dynamique pour remplacer le routage statique
    Utilise le Service Registry pour découvrir les services à la volée
    """
    
    def __init__(self):
        self.legacy_mapping = LEGACY_ROUTE_MAPPING
        self.public_routes = PUBLIC_ROUTES
        
        # Cache de routage pour performance (avec TTL court)
        self._route_cache = {}
        self._cache_ttl = 30  # 30 secondes TTL
        self._last_cache_update = 0
        
        logger.info("🔍 Service Discovery initialisé")
    
    async def resolve_service_dynamic(self, path: str) -> Tuple[str, str]:
        """
        Résolution dynamique de service via Service Registry
        Fallback sur configuration legacy si service non trouvé
        """
        logger.debug(f"🔍 Résolution dynamique pour: {path}")
        
        # 1. Essayer le cache d'abord (performance)
        cached_result = self._get_from_cache(path)
        if cached_result:
            return cached_result
        
        # 2. Essayer découverte dynamique via Service Registry
        dynamic_result = await self._resolve_via_service_registry(path)
        if dynamic_result:
            self._cache_result(path, dynamic_result)
            return dynamic_result
        
        # 3. Fallback sur configuration legacy
        legacy_result = self._resolve_via_legacy_mapping(path)
        if legacy_result:
            self._cache_result(path, legacy_result)
            return legacy_result
        
        # 4. Aucune route trouvée
        logger.warning(f"❌ Aucune route trouvée pour: {path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service non trouvé pour la route: {path}"
        )
    
    async def _resolve_via_service_registry(self, path: str) -> Optional[Tuple[str, str]]:
        """
        Tente de résoudre la route via le Service Registry dynamique
        """
        # Extraire le nom du service depuis le path
        service_name = self._extract_service_name_from_path(path)
        if not service_name:
            return None
        
        # Découvrir les instances du service
        instances = service_registry.discover_service(service_name)
        if not instances:
            logger.debug(f"🔍 Aucune instance trouvée pour le service: {service_name}")
            return None
        
        # Load balancing simple (round-robin)
        service_url = service_registry.get_service_url(service_name, "round_robin")
        if not service_url:
            return None
        
        # Construire le target path
        target_path = self._build_target_path(path, service_name)
        
        logger.info(f"✅ Résolution dynamique: {path} → {service_url}{target_path}")
        return service_url, target_path
    
    def _extract_service_name_from_path(self, path: str) -> Optional[str]:
        """
        Extrait le nom du service depuis le path
        Ex: /api/crm/tiers/ → crm
            /api/quotes/stats/ → documents
        """
        path_parts = path.strip('/').split('/')
        
        # Patterns de routing SOA
        if len(path_parts) >= 2:
            if path_parts[0] == 'api':
                potential_service = path_parts[1]
                
                # Mapping des noms de service
                service_mapping = {
                    'auth': 'auth',
                    'tenants': 'tenant', 
                    'crm': 'crm',
                    'tiers': 'crm',
                    'opportunities': 'crm',
                    'contacts': 'crm',
                    'adresses': 'crm',
                    'quotes': 'documents',
                    'invoices': 'documents',
                    'devis': 'documents',
                    'factures': 'documents',
                    'library': 'library',
                    'categories': 'library',
                    'fournitures': 'library',
                    'main-oeuvre': 'library',
                    'ouvrages': 'library',
                    'ingredients': 'library',
                }
                
                return service_mapping.get(potential_service)
        
        return None
    
    def _build_target_path(self, original_path: str, service_name: str) -> str:
        """
        Construit le path cible pour le service
        Applique les transformations nécessaires
        """
        # Pour l'instant, retourner le path original
        # Plus tard: appliquer des transformations spécifiques par service
        
        # Mapping des transformations de path
        path_transformations = {
            'crm': {
                '/api/tiers/': '/api/tiers/',
                '/api/crm/': '/api/',  # Nouveau format unifié
            },
            'documents': {
                '/api/devis/': '/api/quotes/',
                '/api/factures/': '/api/invoices/',
            },
            'library': {
                '/api/library/': '/api/',
            }
        }
        
        if service_name in path_transformations:
            for pattern, replacement in path_transformations[service_name].items():
                if original_path.startswith(pattern):
                    return original_path.replace(pattern, replacement, 1)
        
        return original_path
    
    def _resolve_via_legacy_mapping(self, path: str) -> Optional[Tuple[str, str]]:
        """
        Résolution via configuration legacy (fallback)
        """
        # Recherche exacte
        if path in self.legacy_mapping:
            service_name, target_path = self.legacy_mapping[path]
            service_url = service_registry.get_service_url(service_name)
            
            if service_url:
                logger.debug(f"📋 Résolution legacy exacte: {path} → {service_url}{target_path}")
                return service_url, target_path
        
        # Recherche par préfixe
        for legacy_route, (service_name, mapped_route) in self.legacy_mapping.items():
            if path.startswith(legacy_route.rstrip('/')):
                service_url = service_registry.get_service_url(service_name)
                
                if service_url:
                    # Transformer le path
                    target_path = path.replace(legacy_route.rstrip('/'), mapped_route.rstrip('/'), 1)
                    logger.debug(f"📋 Résolution legacy préfixe: {path} → {service_url}{target_path}")
                    return service_url, target_path
        
        return None
    
    def _get_from_cache(self, path: str) -> Optional[Tuple[str, str]]:
        """Récupère un résultat du cache de routage"""
        import time
        
        if path in self._route_cache:
            cached_time, result = self._route_cache[path]
            if time.time() - cached_time < self._cache_ttl:
                logger.debug(f"⚡ Cache hit pour: {path}")
                return result
            else:
                # Cache expiré
                del self._route_cache[path]
        
        return None
    
    def _cache_result(self, path: str, result: Tuple[str, str]):
        """Met en cache un résultat de résolution"""
        import time
        self._route_cache[path] = (time.time(), result)
    
    def is_public_route(self, path: str) -> bool:
        """Vérifie si une route est publique (pas d'authentification requise)"""
        # Nettoyer le path
        clean_path = f"/{path.strip('/')}"
        
        # Vérification exacte
        if clean_path in self.public_routes:
            return True
        
        # Vérification par préfixe
        for public_route in self.public_routes:
            if clean_path.startswith(public_route):
                return True
        
        return False
    
    async def get_service_health(self) -> Dict[str, Any]:
        """
        Retourne l'état de santé de tous les services découverts
        """
        registry_stats = service_registry.get_registry_stats()
        all_services = service_registry.get_all_services()
        
        health_report = {
            "service_discovery": {
                "status": "healthy",
                "cache_size": len(self._route_cache),
                "cache_ttl": self._cache_ttl
            },
            "service_registry": registry_stats,
            "services": {}
        }
        
        # Détail par service
        for service_name, instances in all_services.items():
            health_report["services"][service_name] = {
                "total_instances": len(instances),
                "healthy_instances": len([i for i in instances if i["status"] == "healthy"]),
                "instances": instances
            }
        
        return health_report
    
    async def register_default_services(self):
        """
        Enregistre les services par défaut au démarrage
        Pour assurer la rétrocompatibilité pendant la migration
        """
        service_configs = [
            {
                "name": "auth",
                "url": config('AUTH_SERVICE_URL', default='http://localhost:8002'),
                "routes": ["/api/auth/"]
            },
            {
                "name": "tenant",
                "url": config('TENANT_SERVICE_URL', default='http://localhost:8001'),
                "routes": ["/api/tenants/"]
            },
            {
                "name": "crm",
                "url": config('CRM_SERVICE_URL', default='http://localhost:8003'),
                "routes": ["/api/crm/", "/api/tiers/", "/api/opportunities/"]
            },
            {
                "name": "library",
                "url": config('LIBRARY_SERVICE_URL', default='http://localhost:8005'),
                "routes": ["/api/library/", "/api/categories/"]
            }
        ]
        
        for service in service_configs:
            # Parser l'URL pour extraire host et port
            parsed_url = urlparse(service["url"])
            host = parsed_url.hostname
            port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
            
            service_registry.register_service(
                service_name=service["name"],
                instance_id=f"{service['name']}-1",
                host=host,
                port=port,
                health_endpoint="/health/",
                routes=service["routes"],
                metadata={
                    "type": "default",
                    "version": "1.0",
                    "scheme": parsed_url.scheme
                }
            )
            logger.info(f"📝 Service enregistré: {service['name']} @ {service['url']}")
        
        logger.info("📝 Services par défaut enregistrés pour rétrocompatibilité")
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Statistiques de découverte de service"""
        return {
            "service_discovery": {
                "cache_size": len(self._route_cache),
                "cache_ttl": self._cache_ttl,
                "public_routes_count": len(self.public_routes),
                "legacy_mappings_count": len(self.legacy_mapping)
            },
            "service_registry": service_registry.get_registry_stats()
        }


# Instance globale de Service Discovery
service_discovery = ServiceDiscovery()