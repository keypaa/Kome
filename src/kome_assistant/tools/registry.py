from __future__ import annotations

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


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def execute(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
        if tool_name not in self._tools:
            return ToolResult(ok=False, message=f"Tool interdit ou inconnu: {tool_name}")

        spec = self._tools[tool_name]
        missing = [arg for arg in spec.required_args if arg not in args]
        if missing:
            return ToolResult(ok=False, message=f"Arguments manquants pour {tool_name}: {', '.join(missing)}")

        invalid = [name for name, validator in spec.arg_validators.items() if name in args and not validator(args[name])]
        if invalid:
            return ToolResult(ok=False, message=f"Arguments invalides pour {tool_name}: {', '.join(invalid)}")

        try:
            return spec.fn(**args)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, message=f"Erreur outil {tool_name}: {exc}")


def _is_valid_minutes(value: Any) -> bool:
    return isinstance(value, int) and 1 <= value <= 180


def _is_allowed_room(value: Any) -> bool:
    return value in {"salon", "chambre", "cuisine", "living room", "bedroom", "kitchen"}


def _is_allowed_light_state(value: Any) -> bool:
    return value in {"on", "off"}


def _is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 256


def default_tool_registry(data_dir: Path | None = None) -> ToolRegistry:
    registry = ToolRegistry()
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
