"""
Distributed Tracing - Système de traçage distribué pour architecture SOA
Permet de suivre une requête à travers tous les microservices
"""
import uuid
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import asyncio
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """
    Span de trace - représente une opération dans une requête distribuée
    """
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service_name: str = ""
    operation_name: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: str = "started"  # started, success, error
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.span_id:
            self.span_id = str(uuid.uuid4())[:8]
    
    def finish(self, status: str = "success"):
        """Termine le span"""
        self.end_time = time.time()
        self.duration = (self.end_time - self.start_time) * 1000  # ms
        self.status = status
    
    def add_tag(self, key: str, value: Any):
        """Ajoute un tag au span"""
        self.tags[key] = value
    
    def add_log(self, message: str, level: str = "info", **kwargs):
        """Ajoute un log au span"""
        log_entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.logs.append(log_entry)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le span en dictionnaire"""
        data = asdict(self)
        # Convertir les timestamps en ISO format
        if self.start_time:
            data["start_time_iso"] = datetime.fromtimestamp(self.start_time).isoformat()
        if self.end_time:
            data["end_time_iso"] = datetime.fromtimestamp(self.end_time).isoformat()
        return data


@dataclass
class Trace:
    """
    Trace complète - collection de spans pour une requête distribuée
    """
    trace_id: str
    root_span: Optional[TraceSpan] = None
    spans: Dict[str, TraceSpan] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_duration: Optional[float] = None
    services_involved: set = field(default_factory=set)
    status: str = "active"  # active, completed, error
    
    def add_span(self, span: TraceSpan):
        """Ajoute un span à la trace"""
        self.spans[span.span_id] = span
        self.services_involved.add(span.service_name)
        
        # Premier span = root span
        if not self.root_span and not span.parent_span_id:
            self.root_span = span
    
    def finish(self):
        """Termine la trace"""
        self.end_time = time.time()
        self.total_duration = (self.end_time - self.start_time) * 1000
        
        # Déterminer le statut global
        error_spans = [s for s in self.spans.values() if s.status == "error"]
        if error_spans:
            self.status = "error"
        else:
            self.status = "completed"
    
    def get_trace_tree(self) -> Dict[str, Any]:
        """
        Construit l'arbre de la trace avec relations parent-enfant
        """
        if not self.root_span:
            return {"error": "No root span found"}
        
        def build_span_tree(span: TraceSpan) -> Dict[str, Any]:
            children = [
                build_span_tree(child_span) 
                for child_span in self.spans.values() 
                if child_span.parent_span_id == span.span_id
            ]
            
            span_data = span.to_dict()
            if children:
                span_data["children"] = children
            
            return span_data
        
        return {
            "trace_id": self.trace_id,
            "total_duration": self.total_duration,
            "services_involved": list(self.services_involved),
            "status": self.status,
            "root_span": build_span_tree(self.root_span)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la trace en dictionnaire"""
        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration": self.total_duration,
            "services_involved": list(self.services_involved),
            "status": self.status,
            "spans_count": len(self.spans),
            "spans": [span.to_dict() for span in self.spans.values()]
        }


class DistributedTracer:
    """
    Traceur distribué pour suivre les requêtes cross-services
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.active_traces: Dict[str, Trace] = {}
        self.completed_traces: Dict[str, Trace] = {}
        self.max_completed_traces = 1000  # Limite pour éviter la fuite mémoire
        
        # Statistiques
        self.stats = {
            "total_traces": 0,
            "active_traces": 0,
            "completed_traces": 0,
            "error_traces": 0,
            "average_duration": 0.0
        }
        
        logger.info(f"📊 DistributedTracer initialisé pour {service_name}")
    
    def start_trace(self, 
                   operation_name: str,
                   trace_id: str = None,
                   parent_span_id: str = None,
                   tags: Dict[str, Any] = None) -> TraceSpan:
        """
        Démarre une nouvelle trace ou continue une trace existante
        """
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        # Créer ou récupérer la trace
        if trace_id not in self.active_traces:
            trace = Trace(trace_id=trace_id)
            self.active_traces[trace_id] = trace
            self.stats["total_traces"] += 1
            self.stats["active_traces"] += 1
        else:
            trace = self.active_traces[trace_id]
        
        # Créer le span
        span = TraceSpan(
            trace_id=trace_id,
            span_id=str(uuid.uuid4())[:8],
            parent_span_id=parent_span_id,
            service_name=self.service_name,
            operation_name=operation_name,
            tags=tags or {}
        )
        
        # Ajouter à la trace
        trace.add_span(span)
        
        logger.debug(f"📊 Nouveau span: {operation_name} (trace:{trace_id[:8]}, span:{span.span_id})")
        return span
    
    def finish_span(self, span: TraceSpan, status: str = "success"):
        """Termine un span"""
        span.finish(status)
        
        # Vérifier si c'est le dernier span de la trace
        trace = self.active_traces.get(span.trace_id)
        if trace and self._is_trace_complete(trace):
            self._complete_trace(trace)
    
    def _is_trace_complete(self, trace: Trace) -> bool:
        """
        Vérifie si une trace est complète (tous les spans terminés)
        """
        for span in trace.spans.values():
            if span.status == "started":
                return False
        return True
    
    def _complete_trace(self, trace: Trace):
        """Marque une trace comme complétée et la déplace vers l'historique"""
        trace.finish()
        
        # Déplacer vers les traces complétées
        del self.active_traces[trace.trace_id]
        self.completed_traces[trace.trace_id] = trace
        
        # Mettre à jour les stats
        self.stats["active_traces"] -= 1
        self.stats["completed_traces"] += 1
        
        if trace.status == "error":
            self.stats["error_traces"] += 1
        
        # Calculer durée moyenne
        total_duration = sum(t.total_duration or 0 for t in self.completed_traces.values())
        self.stats["average_duration"] = total_duration / len(self.completed_traces)
        
        # Limiter la taille de l'historique
        if len(self.completed_traces) > self.max_completed_traces:
            oldest_trace_id = min(self.completed_traces.keys(), 
                                key=lambda tid: self.completed_traces[tid].start_time)
            del self.completed_traces[oldest_trace_id]
        
        logger.info(f"📊 Trace complétée: {trace.trace_id[:8]} ({trace.total_duration:.2f}ms)")
    
    @contextmanager
    def trace_operation(self, 
                       operation_name: str,
                       trace_id: str = None,
                       parent_span_id: str = None,
                       tags: Dict[str, Any] = None):
        """
        Context manager pour tracer une opération
        """
        span = self.start_trace(operation_name, trace_id, parent_span_id, tags)
        try:
            yield span
            self.finish_span(span, "success")
        except Exception as e:
            span.add_log(f"Error: {str(e)}", "error", exception_type=type(e).__name__)
            self.finish_span(span, "error")
            raise
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Récupère une trace par son ID"""
        return (self.active_traces.get(trace_id) or 
                self.completed_traces.get(trace_id))
    
    def get_active_traces(self) -> List[Dict[str, Any]]:
        """Retourne toutes les traces actives"""
        return [trace.to_dict() for trace in self.active_traces.values()]
    
    def get_completed_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retourne les traces complétées (les plus récentes)"""
        traces = list(self.completed_traces.values())
        traces.sort(key=lambda t: t.end_time or 0, reverse=True)
        return [trace.to_dict() for trace in traces[:limit]]
    
    def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Retourne une trace spécifique avec son arbre"""
        trace = self.get_trace(trace_id)
        if trace:
            return trace.get_trace_tree()
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du traceur"""
        return {
            "service_name": self.service_name,
            "stats": self.stats.copy(),
            "traces": {
                "active_count": len(self.active_traces),
                "completed_count": len(self.completed_traces),
                "max_completed": self.max_completed_traces
            }
        }
    
    def search_traces(self, 
                     service_name: str = None,
                     operation_name: str = None,
                     status: str = None,
                     min_duration: float = None,
                     limit: int = 50) -> List[Dict[str, Any]]:
        """
        Recherche de traces avec filtres
        """
        all_traces = list(self.completed_traces.values()) + list(self.active_traces.values())
        filtered_traces = []
        
        for trace in all_traces:
            # Filtres
            if service_name and service_name not in trace.services_involved:
                continue
            
            if status and trace.status != status:
                continue
            
            if min_duration and (trace.total_duration or 0) < min_duration:
                continue
            
            if operation_name:
                matching_spans = [s for s in trace.spans.values() 
                                if operation_name in s.operation_name]
                if not matching_spans:
                    continue
            
            filtered_traces.append(trace.to_dict())
        
        # Trier par date (plus récentes en premier)
        filtered_traces.sort(
            key=lambda t: t.get("end_time", t.get("start_time", 0)), 
            reverse=True
        )
        
        return filtered_traces[:limit]


class TracingMiddleware:
    """
    Middleware pour intégrer le tracing distribué dans l'API Gateway
    """
    
    def __init__(self, tracer: DistributedTracer):
        self.tracer = tracer
    
    def extract_trace_headers(self, headers: Dict[str, str]) -> Dict[str, Optional[str]]:
        """
        Extrait les headers de tracing de la requête
        """
        return {
            "trace_id": headers.get("X-Trace-ID"),
            "parent_span_id": headers.get("X-Parent-Span-ID"),
            "span_context": headers.get("X-Span-Context")
        }
    
    def inject_trace_headers(self, 
                           headers: Dict[str, str],
                           trace_id: str,
                           span_id: str) -> Dict[str, str]:
        """
        Injecte les headers de tracing dans la requête sortante
        """
        headers["X-Trace-ID"] = trace_id
        headers["X-Parent-Span-ID"] = span_id
        headers["X-Span-Context"] = f"{trace_id}:{span_id}"
        return headers
    
    async def trace_request(self, 
                           request,
                           operation_name: str,
                           service_name: str = None):
        """
        Trace une requête avec propagation du contexte
        """
        # Extraire contexte de tracing
        trace_context = self.extract_trace_headers(dict(request.headers))
        
        # Créer tags pour le span
        tags = {
            "http.method": request.method,
            "http.url": str(request.url),
            "service.name": service_name or "api-gateway",
            "component": "http-server"
        }
        
        # Démarrer le span
        with self.tracer.trace_operation(
            operation_name=operation_name,
            trace_id=trace_context["trace_id"],
            parent_span_id=trace_context["parent_span_id"],
            tags=tags
        ) as span:
            yield span


# Instance globale du traceur pour l'API Gateway
gateway_tracer = DistributedTracer("api-gateway")