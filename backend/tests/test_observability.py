from app.observability.service import RuntimeMetrics


def test_runtime_metrics_never_store_request_payloads():
    metrics = RuntimeMetrics()
    metrics.request()
    metrics.request(error=True)
    snapshot = metrics.snapshot()
    assert snapshot["requests"] == 2
    assert snapshot["errors"] == 1
    assert "patient_id" not in snapshot
    assert "payload" not in snapshot
