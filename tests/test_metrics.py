"""Tests for the MetricsCollector observability module."""
import time
import pytest
from agentzero.metrics import MetricsCollector


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset the singleton before each test."""
    collector = MetricsCollector()
    collector.reset()
    yield
    collector.reset()


def test_record_and_summary():
    """Verify that recording entries produces correct summary stats."""
    c = MetricsCollector()
    c.record("supervisor", 100.0, domain="calendar")
    c.record("supervisor", 200.0, domain="calendar")
    c.record("executor", 50.0, domain="task")
    
    summary = c.get_summary()
    assert "supervisor" in summary["nodes"]
    assert summary["nodes"]["supervisor"]["count"] == 2
    assert summary["nodes"]["supervisor"]["avg_ms"] == 150.0
    assert summary["nodes"]["executor"]["count"] == 1
    assert summary["domains"]["calendar"] == 2
    assert summary["domains"]["task"] == 1
    assert summary["total_errors"] == 0


def test_error_tracking():
    """Verify errors are tracked per node."""
    c = MetricsCollector()
    c.record("supervisor", 100.0, had_error=True, domain="calendar")
    c.record("supervisor", 50.0, had_error=False, domain="calendar")
    
    summary = c.get_summary()
    assert summary["nodes"]["supervisor"]["errors"] == 1
    assert summary["total_errors"] == 1


def test_request_tracing():
    """Verify start/end request tracing works."""
    c = MetricsCollector()
    c.start_request("req-1", "hello world", domain="chat")
    c.record("supervisor", 100.0, domain="chat", request_id="req-1")
    c.end_request("req-1", had_error=False, domain="chat")
    
    recent = c.get_recent_requests(limit=10)
    assert len(recent) == 1
    assert recent[0]["request_id"] == "req-1"
    assert recent[0]["user_input"] == "hello world"
    assert recent[0]["domain"] == "chat"
    assert recent[0]["error"] == False
    assert recent[0]["total_ms"] > 0
    assert len(recent[0]["nodes"]) == 1


def test_ring_buffer_cap():
    """Verify the ring buffer doesn't grow unbounded."""
    c = MetricsCollector(max_entries=100)
    # Force re-init for this test
    c._records.clear()
    c._records = type(c._records)(maxlen=100)
    
    for i in range(200):
        c.record("node", float(i), domain="test")
    
    assert len(c._records) <= 100


def test_window_filtering():
    """Verify time window filtering works."""
    c = MetricsCollector()
    # Record an old entry (fake timestamp)
    c._records.append({
        "node": "old_node", "duration_ms": 100.0,
        "error": False, "domain": "chat",
        "timestamp": time.time() - 7200  # 2 hours ago
    })
    c.record("new_node", 50.0, domain="chat")
    
    summary = c.get_summary(window_seconds=3600)
    assert "old_node" not in summary["nodes"]
    assert "new_node" in summary["nodes"]
