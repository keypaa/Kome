from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from kome_assistant.core.contracts import ToolResult
from kome_assistant.memory.state_store import StateStore
from kome_assistant.tools import builtin

ToolFn = Callable[..., ToolResult]


@dataclass(slots=True)
class ToolSpec:
    name: str
    fn: ToolFn
    required_args: tuple[str, ...] = field(default_factory=tuple)
    arg_validators: dict[str, Callable[[Any], bool]] = field(default_factory=dict)


@dataclass(slots=True)
class ToolPolicy:
    strict_confirmations: bool = False
    require_confirmation_for: set[str] = field(default_factory=set)
    cooldown_seconds_by_tool: dict[str, float] = field(default_factory=dict)
    rate_limit_count: int = 20
    rate_limit_window_seconds: float = 60.0


class ToolRegistry:
    def __init__(self, policy: ToolPolicy | None = None) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._policy = policy or ToolPolicy()
        self._recent_exec_ts: list[float] = []
        self._last_exec_by_tool: dict[str, float] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def execute(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        if tool_name not in self._tools:
            return ToolResult(ok=False, message=f"Tool interdit ou inconnu: {tool_name}")

        denial = self._policy_denial(tool_name, args)
        if denial is not None:
            return denial

        exec_args = {k: v for k, v in args.items() if k != "confirmed"}
        spec = self._tools[tool_name]
        missing = [arg for arg in spec.required_args if arg not in exec_args]
        if missing:
            return ToolResult(ok=False, message=f"Arguments manquants pour {tool_name}: {', '.join(missing)}")

        invalid = [
            name
            for name, validator in spec.arg_validators.items()
            if name in exec_args and not validator(exec_args[name])
        ]
        if invalid:
            return ToolResult(ok=False, message=f"Arguments invalides pour {tool_name}: {', '.join(invalid)}")

        try:
            result = spec.fn(**exec_args)
            self._record_exec(tool_name)
            return result
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, message=f"Erreur outil {tool_name}: {exc}")

    def _policy_denial(self, tool_name: str, args: dict[str, Any]) -> ToolResult | None:
        now = time.monotonic()
        window_start = now - self._policy.rate_limit_window_seconds
        self._recent_exec_ts = [item for item in self._recent_exec_ts if item >= window_start]
        if len(self._recent_exec_ts) >= self._policy.rate_limit_count:
            return ToolResult(
                ok=False,
                message="Execution refusee: trop de commandes, reessayez dans un instant",
                payload={"deny_code": "RATE_LIMIT"},
            )

        cooldown = self._policy.cooldown_seconds_by_tool.get(tool_name, 0.0)
        last = self._last_exec_by_tool.get(tool_name)
        if cooldown > 0 and last is not None and now - last < cooldown:
            return ToolResult(
                ok=False,
                message="Execution refusee: outil temporairement en cooldown",
                payload={"deny_code": "COOLDOWN"},
            )

        requires_confirmation = self._policy.strict_confirmations and tool_name in self._policy.require_confirmation_for
        if requires_confirmation and not bool(args.get("confirmed", False)):
            return ToolResult(
                ok=False,
                message="Confirmation requise pour cette action",
                payload={"deny_code": "CONFIRMATION_REQUIRED"},
            )
        return None

    def _record_exec(self, tool_name: str) -> None:
        now = time.monotonic()
        self._recent_exec_ts.append(now)
        self._last_exec_by_tool[tool_name] = now


def _is_valid_minutes(value: Any) -> bool:
    return isinstance(value, int) and 1 <= value <= 180


def _is_allowed_room(value: Any) -> bool:
    return value in {"salon", "chambre", "cuisine", "living room", "bedroom", "kitchen"}


def _is_allowed_light_state(value: Any) -> bool:
    return value in {"on", "off"}


def _is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 256


def default_tool_registry(data_dir: Path | None = None) -> ToolRegistry:
    strict_confirmations = os.getenv("KOME_SAFE_CONFIRM", "0").strip().lower() in {"1", "true", "yes", "on"}
    registry = ToolRegistry(
        policy=ToolPolicy(
            strict_confirmations=strict_confirmations,
            require_confirmation_for={"toggle_light"},
            cooldown_seconds_by_tool={"toggle_light": 1.0},
            rate_limit_count=20,
            rate_limit_window_seconds=60.0,
        )
    )
    resolved_data_dir = data_dir if data_dir is not None else Path("data")
    store = StateStore(db_path=resolved_data_dir / "assistant_state.db")

    registry.register(ToolSpec(name="get_time", fn=builtin.get_time))
    registry.register(
        ToolSpec(
            name="set_timer",
            fn=lambda minutes: builtin.set_timer(minutes=minutes, store=store),
            required_args=("minutes",),
            arg_validators={"minutes": _is_valid_minutes},
        )
    )
    registry.register(
        ToolSpec(
            name="toggle_light",
            fn=builtin.toggle_light,
            required_args=("room", "state"),
            arg_validators={"room": _is_allowed_room, "state": _is_allowed_light_state},
        )
    )
    registry.register(
        ToolSpec(
            name="search_docs",
            fn=builtin.search_docs,
            required_args=("query",),
            arg_validators={"query": _is_non_empty_text},
        )
    )
    registry.register(ToolSpec(name="calendar_today", fn=builtin.calendar_today))
    registry.register(ToolSpec(name="list_timers", fn=lambda: builtin.list_timers(store=store)))
    return registry
