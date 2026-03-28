from __future__ import annotations

import re

from kome_assistant.core.contracts import Intent


class IntentRouter:
    _timer_fr = re.compile(r"(?:minuteur|timer).{0,12}?(\d{1,3})", re.IGNORECASE)
    _timer_en = re.compile(r"(?:timer).{0,12}?(\d{1,3})", re.IGNORECASE)
    _search = re.compile(r"(?:search|cherche|recherche)\s+(.+)", re.IGNORECASE)

    def route(self, text: str) -> Intent:
        normalized = text.strip()
        language = self._detect_language(normalized)

        if self._is_time_request(normalized):
            return Intent(name="ask_time", language=language, confidence=0.95)

        minutes = self._extract_timer_minutes(normalized, language)
        if minutes is not None:
            return Intent(
                name="set_timer",
                language=language,
                confidence=0.9,
                slots={"minutes": minutes},
            )

        light_slots = self._extract_light_command(normalized)
        if light_slots is not None:
            return Intent(
                name="toggle_light",
                language=language,
                confidence=0.85,
                slots=light_slots,
            )

        search_query = self._extract_search_query(normalized)
        if search_query:
            return Intent(
                name="search_docs",
                language=language,
                confidence=0.8,
                slots={"query": search_query},
            )

        if self._is_calendar_request(normalized):
            return Intent(name="calendar_today", language=language, confidence=0.8)

        return Intent(name="fallback", language=language, confidence=0.1)

    def _detect_language(self, text: str) -> str:
        fr_markers = ["quelle", "heure", "minuteur", "allume", "eteins", "calendrier", "cherche"]
        en_markers = ["what", "time", "timer", "turn", "light", "calendar", "search"]
        low = text.lower()
        fr_score = sum(1 for marker in fr_markers if marker in low)
        en_score = sum(1 for marker in en_markers if marker in low)
        return "fr" if fr_score >= en_score else "en"

    def _is_time_request(self, text: str) -> bool:
        low = text.lower()
        return any(
            key in low
            for key in [
                "quelle heure",
                "heure est",
                "what time",
                "current time",
                "time is it",
            ]
        )

    def _extract_timer_minutes(self, text: str, language: str) -> int | None:
        matcher = self._timer_fr if language == "fr" else self._timer_en
        match = matcher.search(text)
        if not match:
            return None
        value = int(match.group(1))
        if value <= 0 or value > 180:
            return None
        return value

    def _extract_light_command(self, text: str) -> dict[str, str] | None:
        low = text.lower()
        state = None
        if any(token in low for token in ["allume", "on", "turn on"]):
            state = "on"
        if any(token in low for token in ["eteins", "éteins", "off", "turn off"]):
            state = "off"
        if state is None:
            return None
        if not any(token in low for token in ["lumiere", "lumière", "light"]):
            return None
        room = "salon"
        for candidate in ["salon", "chambre", "cuisine", "living room", "bedroom", "kitchen"]:
            if candidate in low:
                room = candidate
                break
        return {"state": state, "room": room}

    def _extract_search_query(self, text: str) -> str | None:
        match = self._search.search(text)
        if not match:
            return None
        return match.group(1).strip()

    def _is_calendar_request(self, text: str) -> bool:
        low = text.lower()
        return any(token in low for token in ["agenda", "calendrier", "calendar", "events", "evenement", "événement"])
