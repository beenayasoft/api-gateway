"""
Service Registry - Découverte dynamique des services
Implémente un registre de services pour SOA 100%
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import httpx
from dataclasses import dataclass, asdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ServiceInstance:
    """Instance d'un service enregistré"""
    service_name: str
    instance_id: str
    host: str
    port: int
    health_endpoint: str
    routes: List[str]
    status: str = "healthy"  # healthy, unhealthy, unknown
    last_heartbeat: Optional[datetime] = None
    registration_time: Optional[datetime] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.registration_time is None:
            self.registration_time = datetime.now()
    
    @property
    def url(self) -> str:
        """URL de base du service"""
        return f"http://{self.host}:{self.port}"
    
    @property
    def health_url(self) -> str:
        """URL complète du health check"""
        return f"{self.url}{self.health_endpoint}"
    
    def is_expired(self, ttl_seconds: int = 60) -> bool:
        """Vérifie si l'instance a expiré (pas de heartbeat récent)"""
        if not self.last_heartbeat:
            return True
        return datetime.now() - self.last_heartbeat > timedelta(seconds=ttl_seconds)


class ServiceRegistry:
    """
    Service Registry pour découverte dynamique des services
    Remplace la configuration statique par un système dynamique
    """
    
    def __init__(self, health_check_interval: int = 30, service_ttl: int = 60):
        self._services: Dict[str, Dict[str, ServiceInstance]] = {}
        self._health_check_interval = health_check_interval
        self._service_ttl = service_ttl
        self._running = False
        self._health_check_task = None
        self._persistence_file = Path("service_registry.json")
        
        # Charger les services persistés au démarrage
        self._load_from_disk()
        
        logger.info("🏛️ Service Registry initialisé")
    
    async def start(self):
        """Démarre le service registry et les health checks"""
        if self._running:
            return
            
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("🚀 Service Registry démarré")
    
    async def stop(self):
        """Arrête le service registry"""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Sauvegarder avant arrêt
        self._save_to_disk()
        logger.info("🛑 Service Registry arrêté")
    
    def register_service(
        self, 
        service_name: str,
        instance_id: str,
        host: str, 
        port: int,
        health_endpoint: str = "/health/",
        routes: List[str] = None,
        metadata: Dict = None
    ) -> bool:
        """
        Enregistre une nouvelle instance de service
        """
        if routes is None:
            routes = []
        
        instance = ServiceInstance(
            service_name=service_name,
            instance_id=instance_id,
            host=host,
            port=port,
            health_endpoint=health_endpoint,
            routes=routes,
            metadata=metadata or {},
            last_heartbeat=datetime.now()
        )
        
        # Créer le namespace du service s'il n'existe pas
        if service_name not in self._services:
            self._services[service_name] = {}
        
        # Enregistrer l'instance
        self._services[service_name][instance_id] = instance
        
        logger.info(f"📝 Service enregistré: {service_name}#{instance_id} @ {instance.url}")
        
        # Sauvegarder
        self._save_to_disk()
        return True
    
    def unregister_service(self, service_name: str, instance_id: str) -> bool:
        """Désenregistre une instance de service"""
        if service_name in self._services and instance_id in self._services[service_name]:
            del self._services[service_name][instance_id]
            
            # Nettoyer si plus d'instances
            if not self._services[service_name]:
                del self._services[service_name]
            
            logger.info(f"🗑️ Service désenregistré: {service_name}#{instance_id}")
            self._save_to_disk()
            return True
        
        return False
    
    def heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Met à jour le heartbeat d'une instance"""
        if service_name in self._services and instance_id in self._services[service_name]:
            self._services[service_name][instance_id].last_heartbeat = datetime.now()
            self._services[service_name][instance_id].status = "healthy"
            return True
        return False
    
    def discover_service(self, service_name: str) -> List[ServiceInstance]:
        """
        Découvre toutes les instances saines d'un service
        """
        if service_name not in self._services:
            return []
        
        healthy_instances = []
        for instance in self._services[service_name].values():
            if instance.status == "healthy" and not instance.is_expired(self._service_ttl):
                healthy_instances.append(instance)
        
        return healthy_instances
    
    def get_service_url(self, service_name: str, load_balance: str = "round_robin") -> Optional[str]:
        """
        Obtient l'URL d'une instance de service avec load balancing
        """
        instances = self.discover_service(service_name)
        if not instances:
            logger.warning(f"⚠️ Aucune instance saine trouvée pour {service_name}")
            return None
        
        # Simple round-robin pour l'instant
        if load_balance == "round_robin":
            # Utiliser un hash simple basé sur le temps pour la rotation
            index = int(time.time()) % len(instances)
            selected = instances[index]
            logger.debug(f"🎯 Load balancing: {service_name} → {selected.url}")
            return selected.url
        
        # Fallback: première instance
        return instances[0].url
    
    def get_all_services(self) -> Dict[str, List[Dict]]:
        """Retourne tous les services enregistrés"""
        result = {}
        for service_name, instances in self._services.items():
            result[service_name] = [
                {
                    **asdict(instance),
                    "last_heartbeat": instance.last_heartbeat.isoformat() if instance.last_heartbeat else None,
                    "registration_time": instance.registration_time.isoformat() if instance.registration_time else None,
                }
                for instance in instances.values()
            ]
        return result
    
    async def _health_check_loop(self):
        """Boucle de health check des services enregistrés"""
        while self._running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except Exception as e:
                logger.error(f"💥 Erreur dans health check loop: {e}")
                await asyncio.sleep(5)  # Retry après erreur
    
    async def _perform_health_checks(self):
        """Effectue les health checks de tous les services"""
        if not self._services:
            return
        
        tasks = []
        for service_name, instances in self._services.items():
            for instance_id, instance in instances.items():
                task = asyncio.create_task(
                    self._check_instance_health(service_name, instance_id, instance)
                )
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
        # Nettoyer les instances expirées
        self._cleanup_expired_services()
    
    async def _check_instance_health(self, service_name: str, instance_id: str, instance: ServiceInstance):
        """Vérifie la santé d'une instance spécifique"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(instance.health_url)
                
                if response.status_code == 200:
                    instance.status = "healthy"
                    instance.last_heartbeat = datetime.now()
                    logger.debug(f"✅ Health check OK: {service_name}#{instance_id}")
                else:
                    instance.status = "unhealthy"
                    logger.warning(f"⚠️ Health check failed: {service_name}#{instance_id} → {response.status_code}")
                    
        except Exception as e:
            instance.status = "unhealthy"
            logger.warning(f"❌ Health check error: {service_name}#{instance_id} → {type(e).__name__}")
    
    def _cleanup_expired_services(self):
        """Nettoie les services expirés"""
        services_to_remove = []
        instances_to_remove = []
        
        for service_name, instances in self._services.items():
            for instance_id, instance in instances.items():
                if instance.is_expired(self._service_ttl):
                    instances_to_remove.append((service_name, instance_id))
        
        # Supprimer les instances expirées
        for service_name, instance_id in instances_to_remove:
            logger.info(f"🧹 Nettoyage instance expirée: {service_name}#{instance_id}")
            del self._services[service_name][instance_id]
        
        # Supprimer les services vides
        for service_name in list(self._services.keys()):
            if not self._services[service_name]:
                logger.info(f"🧹 Nettoyage service vide: {service_name}")
                del self._services[service_name]
    
    def _save_to_disk(self):
        """Sauvegarde l'état du registry sur disque"""
        try:
            data = {}
            for service_name, instances in self._services.items():
                data[service_name] = {}
                for instance_id, instance in instances.items():
                    instance_data = asdict(instance)
                    # Convertir datetime en ISO string
                    if instance_data["last_heartbeat"]:
                        instance_data["last_heartbeat"] = instance.last_heartbeat.isoformat()
                    if instance_data["registration_time"]:
                        instance_data["registration_time"] = instance.registration_time.isoformat()
                    data[service_name][instance_id] = instance_data
            
            with open(self._persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"💾 Erreur sauvegarde registry: {e}")
    
    def _load_from_disk(self):
        """Charge l'état du registry depuis le disque"""
        if not self._persistence_file.exists():
            return
        
        try:
            with open(self._persistence_file, 'r') as f:
                data = json.load(f)
            
            for service_name, instances in data.items():
                self._services[service_name] = {}
                for instance_id, instance_data in instances.items():
                    # Reconvertir les datetime
                    if instance_data["last_heartbeat"]:
                        instance_data["last_heartbeat"] = datetime.fromisoformat(instance_data["last_heartbeat"])
                    if instance_data["registration_time"]:
                        instance_data["registration_time"] = datetime.fromisoformat(instance_data["registration_time"])
                    
                    self._services[service_name][instance_id] = ServiceInstance(**instance_data)
            
            logger.info(f"📂 Registry chargé depuis disque: {len(self._services)} services")
            
        except Exception as e:
            logger.error(f"💾 Erreur chargement registry: {e}")
    
    def get_registry_stats(self) -> Dict:
        """Statistiques du service registry"""
        total_services = len(self._services)
        total_instances = sum(len(instances) for instances in self._services.values())
        healthy_instances = 0
        unhealthy_instances = 0
        
        for instances in self._services.values():
            for instance in instances.values():
                if instance.status == "healthy" and not instance.is_expired(self._service_ttl):
                    healthy_instances += 1
                else:
                    unhealthy_instances += 1
        
        return {
            "total_services": total_services,
            "total_instances": total_instances,
            "healthy_instances": healthy_instances,
            "unhealthy_instances": unhealthy_instances,
            "health_check_interval": self._health_check_interval,
            "service_ttl": self._service_ttl,
            "running": self._running
        }


# Instance globale du service registry
service_registry = ServiceRegistry()