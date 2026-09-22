from app.services.live.live_latency_trace_service import compute_metrics, deterministic_trace_id


def test_t0_t17_derived_metrics_are_milliseconds():
    trace = {
        "t0_expected_close_at": "2026-01-01T00:00:00+00:00",
        "t1_broker_event_received_at": "2026-01-01T00:00:00.800000+00:00",
        "t3_candle_db_commit_at": "2026-01-01T00:00:00.900000+00:00",
        "t4_redis_event_published_at": "2026-01-01T00:00:00.920000+00:00",
        "t5_strategy_event_received_at": "2026-01-01T00:00:00.950000+00:00",
        "t6_strategy_started_at": "2026-01-01T00:00:00.970000+00:00",
        "t7_strategy_finished_at": "2026-01-01T00:00:01.020000+00:00",
        "t8_signal_persisted_at": "2026-01-01T00:00:01.030000+00:00",
        "t11_order_request_queued_at": "2026-01-01T00:00:01.100000+00:00",
        "t12_order_request_sent_at": "2026-01-01T00:00:01.120000+00:00",
        "t13_broker_order_accepted_at": "2026-01-01T00:00:01.300000+00:00",
        "t14_broker_fill_received_at": "2026-01-01T00:00:01.400000+00:00",
    }
    metrics = compute_metrics(trace)
    assert metrics["broker_candle_latency_ms"] == 800.0
    assert metrics["event_bus_latency_ms"] == 30.0
    assert metrics["close_to_order_send_ms"] == 1120.0
    assert metrics["close_to_fill_ms"] == 1400.0


def test_trace_id_is_deterministic_per_deployment_and_candle():
    first = deterministic_trace_id("deployment-a", "2026-01-01T00:00:00+00:00")
    second = deterministic_trace_id("deployment-a", "2026-01-01T00:00:00Z")
    assert first == second

