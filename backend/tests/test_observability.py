from app.observability.service import RuntimeMetrics


def test_runtime_metrics_never_store_request_payloads():
    metrics = RuntimeMetrics()
    metrics.request(status_code=200, duration_seconds=0.25)
    metrics.request(error=True, status_code=500, duration_seconds=0.75)
    metrics.request(status_code=404, duration_seconds=0.5)
    snapshot = metrics.snapshot()
    assert snapshot["requests"] == 2
    assert snapshot["errors"] == 1
    assert snapshot["client_errors"] == 1
    assert snapshot["server_errors"] == 1
    assert snapshot["error_rate"] == 0.3333
    assert snapshot["average_duration_seconds"] == 0.5
    assert snapshot["max_duration_seconds"] == 0.75
    assert "patient_id" not in snapshot
    assert "payload" not in snapshot


def test_runtime_metrics_starts_empty():
    snapshot = RuntimeMetrics().snapshot()
    assert snapshot["requests"] == 0
    assert snapshot["errors"] == 0
    assert snapshot["error_rate"] == 0.0
