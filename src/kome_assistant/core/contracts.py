from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class ToolResult:
    ok: bool
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AssistantTurnResult:
    reply_text: str
    language: str
    used_tool: str | None = None
    timestamp_utc: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class Intent:
    name: str
    language: str
    confidence: float
    slots: dict[str, Any] = field(default_factory=dict)
