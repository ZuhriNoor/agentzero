"""
Lightweight in-memory metrics collector for AgentZero observability.
Tracks per-node latency, error rates, and domain distribution.
Thread-safe with a capped ring buffer to prevent unbounded growth.
"""
import time
import threading
import statistics
from collections import deque, defaultdict
from typing import Dict, List, Optional, Any


class MetricsCollector:
    """Singleton metrics collector with ring buffer storage."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, max_entries: int = 10_000):
        if self._initialized:
            return
        self._initialized = True
        self._records = deque(maxlen=max_entries)
        self._request_traces: deque = deque(maxlen=200)
        self._current_traces: Dict[str, dict] = {}  # keyed by request_id
        self._write_lock = threading.Lock()
        self._start_time = time.time()
    
    def record(self, node: str, duration_ms: float, had_error: bool = False,
               domain: Optional[str] = None, request_id: Optional[str] = None):
        """Record a single node execution."""
        entry = {
            "node": node,
            "duration_ms": round(duration_ms, 2),
            "error": had_error,
            "domain": domain or "unknown",
            "timestamp": time.time(),
        }
        with self._write_lock:
            self._records.append(entry)
            
            # Also append to the current request trace if we have a request_id
            if request_id and request_id in self._current_traces:
                self._current_traces[request_id]["nodes"].append(entry)
    
    def start_request(self, request_id: str, user_input: str, domain: str = ""):
        """Mark the start of a new pipeline request."""
        with self._write_lock:
            self._current_traces[request_id] = {
                "request_id": request_id,
                "user_input": user_input[:100],  # truncate for privacy
                "domain": domain,
                "start_time": time.time(),
                "nodes": [],
                "error": False,
            }
    
    def end_request(self, request_id: str, had_error: bool = False, domain: str = ""):
        """Mark the end of a pipeline request and archive the trace."""
        with self._write_lock:
            trace = self._current_traces.pop(request_id, None)
            if trace:
                trace["end_time"] = time.time()
                trace["total_ms"] = round((trace["end_time"] - trace["start_time"]) * 1000, 2)
                trace["error"] = had_error
                if domain:
                    trace["domain"] = domain
                self._request_traces.append(trace)
    
    def get_summary(self, window_seconds: int = 3600) -> dict:
        """Get aggregated metrics for the given time window."""
        cutoff = time.time() - window_seconds
        
        with self._write_lock:
            recent = [r for r in self._records if r["timestamp"] > cutoff]
        
        # Per-node stats
        node_groups: Dict[str, List[float]] = defaultdict(list)
        node_errors: Dict[str, int] = defaultdict(int)
        domain_counts: Dict[str, int] = defaultdict(int)
        total_errors = 0
        
        for r in recent:
            node_groups[r["node"]].append(r["duration_ms"])
            if r["error"]:
                node_errors[r["node"]] += 1
                total_errors += 1
            domain_counts[r["domain"]] += 1
        
        nodes = {}
        for node, durations in node_groups.items():
            sorted_d = sorted(durations)
            nodes[node] = {
                "count": len(durations),
                "avg_ms": round(statistics.mean(durations), 2) if durations else 0,
                "p95_ms": round(sorted_d[int(len(sorted_d) * 0.95)] if len(sorted_d) > 1 else (sorted_d[0] if sorted_d else 0), 2),
                "p99_ms": round(sorted_d[int(len(sorted_d) * 0.99)] if len(sorted_d) > 1 else (sorted_d[0] if sorted_d else 0), 2),
                "max_ms": round(max(durations), 2) if durations else 0,
                "errors": node_errors.get(node, 0),
            }
        
        # Error timeline (errors per minute, last hour)
        error_timeline = defaultdict(int)
        for r in recent:
            if r["error"]:
                minute_bucket = int(r["timestamp"] // 60) * 60
                error_timeline[minute_bucket] += 1
        
        # Request throughput timeline (requests per minute)
        throughput_timeline = defaultdict(int)
        with self._write_lock:
            recent_traces = [t for t in self._request_traces if t.get("end_time", 0) > cutoff]
        for t in recent_traces:
            minute_bucket = int(t.get("end_time", 0) // 60) * 60
            throughput_timeline[minute_bucket] += 1
        
        return {
            "window_seconds": window_seconds,
            "total_records": len(recent),
            "total_errors": total_errors,
            "uptime_seconds": int(time.time() - self._start_time),
            "nodes": nodes,
            "domains": dict(domain_counts),
            "error_timeline": dict(sorted(error_timeline.items())),
            "throughput_timeline": dict(sorted(throughput_timeline.items())),
        }
    
    def get_recent_requests(self, limit: int = 50) -> List[dict]:
        """Get the most recent request traces."""
        with self._write_lock:
            traces = list(self._request_traces)
        # Return most recent first
        return list(reversed(traces[-limit:]))
    
    def reset(self):
        """Reset all metrics (for testing)."""
        with self._write_lock:
            self._records.clear()
            self._request_traces.clear()
            self._current_traces.clear()
            self._start_time = time.time()
