from __future__ import annotations

from dataclasses import dataclass

from kome_assistant.core.contracts import Intent, ToolCall


@dataclass(slots=True)
class LocalPlanner:
    """Placeholder planner.

    Replace this with a local model backend (for example llama.cpp) that emits
    structured tool calls.
    """

    def plan(self, intent: Intent) -> ToolCall | None:
        return None
