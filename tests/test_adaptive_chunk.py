from kome_assistant.cli import _next_chunk_size


def test_next_chunk_increases_when_no_actionable_speech() -> None:
    updated = _next_chunk_size(
        current=1.0,
        min_seconds=0.8,
        max_seconds=2.0,
        step_seconds=0.2,
        actionable=False,
        total_ms=1000,
    )
    assert updated == 1.2


def test_next_chunk_decreases_when_latency_high() -> None:
    updated = _next_chunk_size(
        current=2.0,
        min_seconds=1.0,
        max_seconds=3.0,
        step_seconds=0.25,
        actionable=True,
        total_ms=3000,
    )
    assert updated == 1.75


def test_next_chunk_stays_within_bounds() -> None:
    updated = _next_chunk_size(
        current=1.0,
        min_seconds=1.0,
        max_seconds=2.0,
        step_seconds=0.3,
        actionable=True,
        total_ms=500,
    )
    assert updated == 1.0
