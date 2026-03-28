from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from kome_assistant.core.contracts import ToolResult
from kome_assistant.tools import builtin

ToolFn = Callable[..., ToolResult]


@dataclass(slots=True)
class ToolSpec:
    name: str
    fn: ToolFn
    required_args: tuple[str, ...] = field(default_factory=tuple)


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

        try:
            return spec.fn(**args)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, message=f"Erreur outil {tool_name}: {exc}")


def default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec(name="get_time", fn=builtin.get_time))
    registry.register(ToolSpec(name="set_timer", fn=builtin.set_timer, required_args=("minutes",)))
    registry.register(ToolSpec(name="toggle_light", fn=builtin.toggle_light, required_args=("room", "state")))
    registry.register(ToolSpec(name="search_docs", fn=builtin.search_docs, required_args=("query",)))
    registry.register(ToolSpec(name="calendar_today", fn=builtin.calendar_today))
    return registry
