from pathlib import Path

from kome_assistant.core.observability import JsonlSink, MetricsLogger, summarize_metrics


def test_metrics_summary_percentiles(tmp_path: Path) -> None:
    sink = JsonlSink(tmp_path / "metrics.jsonl")
    logger = MetricsLogger(sink=sink)

    logger.turn(total_ms=100.0)
    logger.turn(total_ms=200.0)
    logger.turn(total_ms=300.0)

    summary = summarize_metrics(tmp_path / "metrics.jsonl")
    assert summary["count"] == 3
    assert summary["p50_total_ms"] == 200.0
    assert summary["p95_total_ms"] == 300.0
