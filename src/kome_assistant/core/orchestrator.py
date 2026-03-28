from __future__ import annotations

from dataclasses import dataclass

from kome_assistant.core.contracts import AssistantTurnResult, Intent
from kome_assistant.core.router import IntentRouter
from kome_assistant.tools.registry import ToolRegistry


@dataclass(slots=True)
class AssistantOrchestrator:
    router: IntentRouter
    tools: ToolRegistry

    def handle_text_turn(self, text: str) -> AssistantTurnResult:
        intent = self.router.route(text)
        if intent.name == "fallback":
            language = intent.language
            if language == "fr":
                return AssistantTurnResult(
                    reply_text="Je n'ai pas compris. Peux-tu reformuler ?",
                    language="fr",
                )
            return AssistantTurnResult(
                reply_text="I did not understand. Can you rephrase?",
                language="en",
            )

        if intent.name in {"ask_time", "set_timer", "toggle_light", "search_docs", "calendar_today", "list_timers"}:
            tool_name, args = self._intent_to_tool(intent)
            result = self.tools.execute(tool_name, args)
            if intent.language == "fr":
                reply = result.message
            else:
                reply = self._translate_response(result.message, intent.language)
            return AssistantTurnResult(reply_text=reply, language=intent.language, used_tool=tool_name)

        return AssistantTurnResult(
            reply_text="Unhandled intent.",
            language=intent.language,
        )

    def _intent_to_tool(self, intent: Intent) -> tuple[str, dict]:
        if intent.name == "ask_time":
            return "get_time", {}
        if intent.name == "set_timer":
            return "set_timer", {"minutes": int(intent.slots["minutes"])}
        if intent.name == "toggle_light":
            return "toggle_light", {
                "room": intent.slots.get("room", "salon"),
                "state": intent.slots.get("state", "on"),
            }
        if intent.name == "search_docs":
            return "search_docs", {"query": str(intent.slots.get("query", ""))}
        if intent.name == "calendar_today":
            return "calendar_today", {}
        if intent.name == "list_timers":
            return "list_timers", {}
        return "noop", {}

    def _translate_response(self, message: str, language: str) -> str:
        if language == "en":
            return (
                message.replace("Heure locale", "Local time")
                .replace("Minuteur", "Timer")
                .replace("Lumiere", "Light")
                .replace("allumee", "on")
                .replace("eteinte", "off")
                .replace("Aucun evenement", "No event")
                .replace("Aucun minuteur actif", "No active timers")
                .replace("Minuteurs actifs", "Active timers")
                .replace("Recherche locale", "Local search")
            )
        return message
