"""
Circuit Breaker Pattern - Protection contre les cascades de pannes
Implémentation complète pour architecture SOA résiliente
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """États du circuit breaker"""
    CLOSED = "closed"       # Circuit fermé - tout va bien
    OPEN = "open"           # Circuit ouvert - service en panne
    HALF_OPEN = "half_open" # Circuit semi-ouvert - test de récupération


@dataclass
class CircuitBreakerConfig:
    """Configuration d'un circuit breaker"""
    failure_threshold: int = 5          # Nb d'échecs avant ouverture
    timeout: float = 60.0               # Timeout en secondes pour rester ouvert
    recovery_timeout: float = 30.0      # Timeout pour test de récupération
    success_threshold: int = 2          # Nb de succès pour fermer le circuit
    monitored_exceptions: tuple = (httpx.RequestError, httpx.TimeoutException, httpx.HTTPStatusError)


@dataclass
class CircuitStats:
    """Statistiques d'un circuit breaker"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0
    opened_count: int = 0
    half_opened_count: int = 0


class CircuitBreaker:
    """
    Circuit Breaker avancé pour protection des services
    """
    
    def __init__(self, 
                 name: str,
                 config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # État du circuit
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        
        # Timestamps pour gestion des timeouts
        self._last_failure_time = None
        self._opened_time = None
        self._last_test_time = None
        
        # Lock pour thread safety
        self._lock = asyncio.Lock()
        
        logger.info(f"🔒 Circuit Breaker créé: {name}")
    
    @property
    def state(self) -> CircuitState:
        """État actuel du circuit"""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Circuit fermé (fonctionnement normal)"""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Circuit ouvert (service indisponible)"""
        return self._state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Circuit semi-ouvert (test de récupération)"""
        return self._state == CircuitState.HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs):
        """
        Exécute une fonction protégée par le circuit breaker
        """
        async with self._lock:
            # Vérifier si on peut exécuter la fonction
            if not await self._can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker ouvert pour {self.name}"
                )
            
            # Si circuit semi-ouvert, passer en mode test
            if self._state == CircuitState.HALF_OPEN:
                self._last_test_time = datetime.now()
        
        # Exécuter la fonction (hors du lock pour éviter les blocages)
        try:
            self._stats.total_requests += 1
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
            
        except Exception as e:
            # Vérifier si c'est une exception monitorée
            if isinstance(e, self.config.monitored_exceptions):
                await self._on_failure()
            raise
    
    async def _can_execute(self) -> bool:
        """
        Vérifie si le circuit permet l'exécution
        """
        now = datetime.now()
        
        if self._state == CircuitState.CLOSED:
            return True
        
        elif self._state == CircuitState.OPEN:
            # Vérifier si le timeout d'ouverture est écoulé
            if (self._opened_time and 
                now - self._opened_time >= timedelta(seconds=self.config.timeout)):
                
                logger.info(f"🔄 Circuit {self.name}: Passage en HALF_OPEN pour test")
                await self._transition_to_half_open()
                return True
            
            return False
        
        elif self._state == CircuitState.HALF_OPEN:
            # En mode semi-ouvert, on limite les requêtes de test
            if (self._last_test_time and 
                now - self._last_test_time < timedelta(seconds=self.config.recovery_timeout)):
                return False
            
            return True
        
        return False
    
    async def _on_success(self):
        """Traite un succès d'exécution"""
        async with self._lock:
            self._stats.successful_requests += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = datetime.now()
            
            logger.debug(f"✅ Circuit {self.name}: Succès #{self._stats.consecutive_successes}")
            
            # Si en mode semi-ouvert et assez de succès, fermer le circuit
            if (self._state == CircuitState.HALF_OPEN and 
                self._stats.consecutive_successes >= self.config.success_threshold):
                
                await self._transition_to_closed()
    
    async def _on_failure(self):
        """Traite un échec d'exécution"""
        async with self._lock:
            self._stats.failed_requests += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = datetime.now()
            
            logger.warning(f"❌ Circuit {self.name}: Échec #{self._stats.consecutive_failures}")
            
            # Si circuit fermé et seuil d'échecs atteint, ouvrir le circuit
            if (self._state == CircuitState.CLOSED and 
                self._stats.consecutive_failures >= self.config.failure_threshold):
                
                await self._transition_to_open()
            
            # Si circuit semi-ouvert et échec, le reouvrir
            elif self._state == CircuitState.HALF_OPEN:
                await self._transition_to_open()
    
    async def _transition_to_open(self):
        """Transition vers l'état OUVERT"""
        old_state = self._state
        self._state = CircuitState.OPEN
        self._opened_time = datetime.now()
        self._stats.state_changes += 1
        self._stats.opened_count += 1
        
        logger.warning(f"🔴 Circuit {self.name}: {old_state.value} → OPEN")
    
    async def _transition_to_half_open(self):
        """Transition vers l'état SEMI-OUVERT"""
        old_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._stats.state_changes += 1
        self._stats.half_opened_count += 1
        
        logger.info(f"🟡 Circuit {self.name}: {old_state.value} → HALF_OPEN")
    
    async def _transition_to_closed(self):
        """Transition vers l'état FERMÉ"""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._opened_time = None
        self._last_test_time = None
        self._stats.state_changes += 1
        
        logger.info(f"🟢 Circuit {self.name}: {old_state.value} → CLOSED")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du circuit"""
        return {
            "name": self.name,
            "state": self._state.value,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "timeout": self.config.timeout,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold
            },
            "stats": {
                "total_requests": self._stats.total_requests,
                "successful_requests": self._stats.successful_requests,
                "failed_requests": self._stats.failed_requests,
                "success_rate": (
                    self._stats.successful_requests / max(1, self._stats.total_requests) * 100
                ),
                "consecutive_failures": self._stats.consecutive_failures,
                "consecutive_successes": self._stats.consecutive_successes,
                "last_failure_time": self._stats.last_failure_time.isoformat() if self._stats.last_failure_time else None,
                "last_success_time": self._stats.last_success_time.isoformat() if self._stats.last_success_time else None,
                "state_changes": self._stats.state_changes,
                "opened_count": self._stats.opened_count,
                "half_opened_count": self._stats.half_opened_count
            },
            "timestamps": {
                "opened_time": self._opened_time.isoformat() if self._opened_time else None,
                "last_test_time": self._last_test_time.isoformat() if self._last_test_time else None
            }
        }
    
    async def reset(self):
        """Remet le circuit à zéro (état fermé)"""
        async with self._lock:
            old_state = self._state
            self._state = CircuitState.CLOSED
            self._stats.consecutive_failures = 0
            self._stats.consecutive_successes = 0
            self._opened_time = None
            self._last_test_time = None
            
            logger.info(f"🔄 Circuit {self.name}: Reset {old_state.value} → CLOSED")
    
    async def force_open(self):
        """Force l'ouverture du circuit (pour maintenance)"""
        async with self._lock:
            old_state = self._state
            await self._transition_to_open()
            logger.warning(f"⚠️ Circuit {self.name}: Ouverture forcée {old_state.value} → OPEN")


class CircuitBreakerOpenError(Exception):
    """Exception levée quand le circuit breaker est ouvert"""
    pass


class CircuitBreakerManager:
    """
    Gestionnaire global des circuit breakers pour tous les services
    """
    
    def __init__(self):
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
        logger.info("🔧 Circuit Breaker Manager initialisé")
    
    def get_circuit(self, 
                    service_name: str,
                    config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """
        Récupère ou crée un circuit breaker pour un service
        """
        if service_name not in self._circuits:
            circuit_config = config or self._default_config
            self._circuits[service_name] = CircuitBreaker(service_name, circuit_config)
            logger.info(f"🔒 Nouveau circuit breaker créé: {service_name}")
        
        return self._circuits[service_name]
    
    async def call_with_circuit_breaker(self,
                                       service_name: str,
                                       func: Callable,
                                       *args,
                                       config: CircuitBreakerConfig = None,
                                       fallback: Callable = None,
                                       **kwargs):
        """
        Exécute une fonction avec protection circuit breaker et fallback optionnel
        """
        circuit = self.get_circuit(service_name, config)
        
        try:
            return await circuit.call(func, *args, **kwargs)
        except CircuitBreakerOpenError:
            logger.warning(f"🔴 Circuit ouvert pour {service_name}")
            if fallback:
                logger.info(f"🔄 Exécution fallback pour {service_name}")
                return await fallback(*args, **kwargs)
            raise
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de tous les circuit breakers"""
        return {
            "circuit_breakers": {
                name: circuit.get_stats()
                for name, circuit in self._circuits.items()
            },
            "summary": {
                "total_circuits": len(self._circuits),
                "open_circuits": len([c for c in self._circuits.values() if c.is_open]),
                "half_open_circuits": len([c for c in self._circuits.values() if c.is_half_open]),
                "closed_circuits": len([c for c in self._circuits.values() if c.is_closed])
            }
        }
    
    async def reset_all_circuits(self):
        """Remet tous les circuits à zéro"""
        for circuit in self._circuits.values():
            await circuit.reset()
        logger.info("🔄 Tous les circuit breakers ont été remis à zéro")
    
    async def health_check_all_circuits(self) -> Dict[str, Any]:
        """Vérifie la santé de tous les circuits"""
        health_report = {
            "overall_health": "healthy",
            "circuits": {}
        }
        
        unhealthy_count = 0
        
        for name, circuit in self._circuits.items():
            stats = circuit.get_stats()
            
            # Déterminer la santé du circuit
            if circuit.is_open:
                circuit_health = "critical"
                unhealthy_count += 1
            elif circuit.is_half_open:
                circuit_health = "warning"
            else:
                success_rate = stats["stats"]["success_rate"]
                if success_rate < 50:
                    circuit_health = "warning"
                elif success_rate < 90:
                    circuit_health = "degraded"
                else:
                    circuit_health = "healthy"
            
            health_report["circuits"][name] = {
                "health": circuit_health,
                "state": stats["state"],
                "success_rate": stats["stats"]["success_rate"],
                "consecutive_failures": stats["stats"]["consecutive_failures"]
            }
        
        # Déterminer la santé globale
        if unhealthy_count > len(self._circuits) / 2:
            health_report["overall_health"] = "critical"
        elif unhealthy_count > 0:
            health_report["overall_health"] = "degraded"
        
        return health_report


# Instance globale du manager
circuit_breaker_manager = CircuitBreakerManager()