from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _ts() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(slots=True)
class JsonlSink:
    path: Path
    max_bytes: int = 5_000_000

    def write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rotate_if_needed()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _rotate_if_needed(self) -> None:
        if not self.path.exists():
            return
        if self.path.stat().st_size < self.max_bytes:
            return
        rotated = self.path.with_suffix(self.path.suffix + ".1")
        if rotated.exists():
            rotated.unlink()
        self.path.rename(rotated)


@dataclass(slots=True)
class RuntimeLogger:
    sink: JsonlSink

    def event(self, name: str, **fields: Any) -> None:
        self.sink.write({"ts": _ts(), "type": "event", "name": name, **fields})


@dataclass(slots=True)
class MetricsLogger:
    sink: JsonlSink

    def turn(self, **fields: Any) -> None:
        self.sink.write({"ts": _ts(), "type": "turn", **fields})


def summarize_metrics(path: Path) -> dict[str, float | int]:
    if not path.exists():
        return {"count": 0, "p50_total_ms": 0.0, "p95_total_ms": 0.0, "avg_total_ms": 0.0}

    values: list[float] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if payload.get("type") != "turn":
                continue
            total = payload.get("total_ms")
            if isinstance(total, (int, float)):
                values.append(float(total))

    if not values:
        return {"count": 0, "p50_total_ms": 0.0, "p95_total_ms": 0.0, "avg_total_ms": 0.0}

    values.sort()
    return {
        "count": len(values),
        "p50_total_ms": _percentile(values, 0.50),
        "p95_total_ms": _percentile(values, 0.95),
        "avg_total_ms": sum(values) / len(values),
    }


def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    index = max(0, min(len(sorted_values) - 1, math.ceil(q * len(sorted_values)) - 1))
    return sorted_values[index]
