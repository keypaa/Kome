from __future__ import annotations

from datetime import datetime

from kome_assistant.core.contracts import ToolResult


def get_time() -> ToolResult:
    now = datetime.now().strftime("%H:%M")
    return ToolResult(ok=True, message=f"Heure locale: {now}")


def set_timer(minutes: int) -> ToolResult:
    if minutes <= 0 or minutes > 180:
        return ToolResult(ok=False, message="Minuteur invalide")
    return ToolResult(ok=True, message=f"Minuteur defini pour {minutes} minute(s)", payload={"minutes": minutes})


def toggle_light(room: str, state: str) -> ToolResult:
    normalized_state = "allumee" if state == "on" else "eteinte"
    return ToolResult(ok=True, message=f"Lumiere {room} {normalized_state}", payload={"room": room, "state": state})


def search_docs(query: str) -> ToolResult:
    if not query.strip():
        return ToolResult(ok=False, message="Recherche locale vide")
    return ToolResult(ok=True, message=f"Recherche locale: aucun index configure pour '{query}'", payload={"query": query})


def calendar_today() -> ToolResult:
    return ToolResult(ok=True, message="Aucun evenement aujourd'hui")
