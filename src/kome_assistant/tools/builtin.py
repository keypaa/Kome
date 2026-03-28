from __future__ import annotations

from datetime import datetime

from kome_assistant.core.contracts import ToolResult
from kome_assistant.memory.state_store import StateStore


def get_time() -> ToolResult:
    now = datetime.now().strftime("%H:%M")
    return ToolResult(ok=True, message=f"Heure locale: {now}")


def set_timer(minutes: int, store: StateStore) -> ToolResult:
    if minutes <= 0 or minutes > 180:
        return ToolResult(ok=False, message="Minuteur invalide")
    timer_id = store.add_timer(minutes=minutes)
    return ToolResult(
        ok=True,
        message=f"Minuteur defini pour {minutes} minute(s)",
        payload={"minutes": minutes, "timer_id": timer_id},
    )


def toggle_light(room: str, state: str) -> ToolResult:
    normalized_state = "allumee" if state == "on" else "eteinte"
    return ToolResult(ok=True, message=f"Lumiere {room} {normalized_state}", payload={"room": room, "state": state})


def search_docs(query: str) -> ToolResult:
    if not query.strip():
        return ToolResult(ok=False, message="Recherche locale vide")
    return ToolResult(ok=True, message=f"Recherche locale: aucun index configure pour '{query}'", payload={"query": query})


def calendar_today() -> ToolResult:
    return ToolResult(ok=True, message="Aucun evenement aujourd'hui")


def list_timers(store: StateStore) -> ToolResult:
    timers = store.list_active_timers()
    if not timers:
        return ToolResult(ok=True, message="Aucun minuteur actif", payload={"timers": []})

    formatted = ", ".join(f"#{item['id']} ({item['minutes']} min)" for item in timers)
    return ToolResult(ok=True, message=f"Minuteurs actifs: {formatted}", payload={"timers": timers})
