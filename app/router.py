"""
Service Router - Gestion intelligente du routage vers les microservices
"""
import logging
from typing import Dict, Any, Tuple
from fastapi import HTTPException, status
import httpx
import asyncio

from config import SERVICES, LEGACY_ROUTE_MAPPING

logger = logging.getLogger(__name__)


class ServiceRouter:
    """Router intelligent avec compatibilité frontend existant + optimisations O(1)"""
    
    def __init__(self):
        self.services = SERVICES
        self.legacy_mapping = LEGACY_ROUTE_MAPPING
        
        # OPTIMISATION Milestone 2.1: HashMap pré-compilé pour résolution O(1)
        self._route_cache = {}
        self._prefix_map = {}
        self._compile_route_cache()
        
        logger.info(f"🚀 ServiceRouter optimisé initialisé - {len(self._route_cache)} routes exactes, {len(self._prefix_map)} préfixes")
    
    def _compile_route_cache(self):
        """
        Pré-compile tous les mappings en HashMap pour résolution O(1).
        OPTIMISATION: Évite les boucles O(n) à chaque requête.
        """
        # 1. Cache exact pour LEGACY_ROUTE_MAPPING
        for legacy_route, (service_name, target_path) in self.legacy_mapping.items():
            if service_name in self.services:
                service_url = self.services[service_name]["url"]
                self._route_cache[legacy_route] = (service_url, target_path)
                logger.debug(f"📋 Cache exact: '{legacy_route}' → {service_name} ({service_url})")
        
        # 2. Cache préfixes pour LEGACY_ROUTE_MAPPING (routes dynamiques)
        for legacy_route, (service_name, new_route) in self.legacy_mapping.items():
            if service_name in self.services:
                legacy_prefix = legacy_route.rstrip('/')
                service_url = self.services[service_name]["url"]
                new_route_prefix = new_route.rstrip('/')
                self._prefix_map[legacy_prefix] = (service_url, legacy_prefix, new_route_prefix)
                logger.debug(f"📋 Cache préfixe: '{legacy_prefix}' → {service_name} ('{legacy_prefix}' → '{new_route_prefix}')")
        
        # 3. Cache pour configuration normale des services
        for service_name, config in self.services.items():
            service_url = config["url"]
            for route_prefix in config["routes"]:
                self._prefix_map[route_prefix] = (service_url, route_prefix, route_prefix)  # Pas de transformation
                logger.debug(f"📋 Cache service: '{route_prefix}' → {service_name} ({service_url})")
        
        # 4. Trier préfixes par longueur décroissante pour matching optimal
        self._sorted_prefixes = sorted(self._prefix_map.keys(), key=len, reverse=True)
        logger.info(f"🚀 Route cache compilé: {len(self._route_cache)} exacts, {len(self._sorted_prefixes)} préfixes")
    
    def resolve_service(self, path: str) -> Tuple[str, str]:
        """
        OPTIMISÉ Milestone 2.1: Résolution O(1) avec HashMap pré-compilé.
        Remplace les boucles O(n) par lookup direct pour performance gateway.
        """
        logger.debug(f"🚀 RESOLVE_SERVICE_OPTIMIZED: Résolution O(1) pour path='{path}'")
        
        # ÉTAPE 1: Cache exact O(1) - le plus rapide
        if path in self._route_cache:
            service_url, target_path = self._route_cache[path]
            logger.debug(f"⚡ Résolution exacte O(1): '{path}' → {service_url} + '{target_path}'")
            return service_url, target_path
        
        # ÉTAPE 2: Matching préfixe optimisé - O(p) où p = nb préfixes (trié par longueur)
        for prefix in self._sorted_prefixes:
            if path.startswith(prefix):
                service_url, old_prefix, new_prefix = self._prefix_map[prefix]
                
                # Transformation path si nécessaire
                if old_prefix != new_prefix:
                    target_path = path.replace(old_prefix, new_prefix, 1)
                else:
                    target_path = path
                
                logger.debug(f"⚡ Résolution préfixe: '{prefix}' match → {service_url} + '{target_path}'")
                
                # OPTIMISATION: Mise en cache pour futures requêtes identiques
                self._route_cache[path] = (service_url, target_path)
                
                return service_url, target_path
        
        # Aucune route trouvée - log optimisé (moins verbose)
        logger.warning(f"❌ Route non trouvée: '{path}' (cache: {len(self._route_cache)} routes, {len(self._sorted_prefixes)} préfixes)")
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route non configurée: {path}"
        )
    
    def get_router_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques de performance du routeur optimisé.
        OPTIMISATION Milestone 2.1: Métriques pour validation.
        """
        return {
            "routing_optimization": {
                "milestone": "2.1",
                "algorithm": "HashMap O(1)",
                "exact_routes_cached": len(self._route_cache),
                "prefix_routes": len(self._sorted_prefixes),
                "performance_improvement": "O(n) → O(1) for exact matches",
                "cache_enabled": True
            },
            "routes_breakdown": {
                "legacy_mappings": len(self.legacy_mapping),
                "service_routes": sum(len(config["routes"]) for config in self.services.values()),
                "total_prefixes": len(self._sorted_prefixes)
            },
            "optimization_features": [
                "Exact route HashMap cache",
                "Sorted prefix matching",
                "Dynamic cache population",
                "Reduced logging verbosity"
            ]
        }

    async def health_check_all(self) -> Dict[str, Any]:
        """Vérifie la santé de tous les services backend"""
        
        health_status = {
            "gateway": {"status": "healthy", "version": "1.0.0"},
            "services": {},
            "legacy_compatibility": "enabled"
        }
        
        overall_healthy = True
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            tasks = []
            
            for service_name, config in self.services.items():
                health_url = f"{config['url']}{config['health']}"
                tasks.append(self._check_service_health(client, service_name, health_url))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for service_name, result in zip(self.services.keys(), results):
                if isinstance(result, Exception):
                    health_status["services"][service_name] = {
                        "status": "unreachable",
                        "error": str(result)
                    }
                    overall_healthy = False
                else:
                    health_status["services"][service_name] = result
                    if result["status"] != "healthy":
                        overall_healthy = False
        
        health_status["gateway"]["overall_status"] = "healthy" if overall_healthy else "degraded"
        return health_status
    
    async def _check_service_health(self, client: httpx.AsyncClient, service_name: str, health_url: str) -> Dict[str, Any]:
        """Vérifie la santé d'un service individuel"""
        
        try:
            response = await client.get(health_url)
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "url": health_url,
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                return {
                    "status": "unhealthy", 
                    "url": health_url,
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                "status": "unreachable",
                "url": health_url, 
                "error": str(e)
            }


# Instance globale du router
router = ServiceRouter()