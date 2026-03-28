from kome_assistant.core.router import IntentRouter


def test_detect_french_timer() -> None:
    router = IntentRouter()
    intent = router.route("mets un minuteur 12")
    assert intent.name == "set_timer"
    assert intent.language == "fr"
    assert intent.slots["minutes"] == 12


def test_detect_english_time_request() -> None:
    router = IntentRouter()
    intent = router.route("what time is it")
    assert intent.name == "ask_time"
    assert intent.language == "en"


def test_detect_list_timers_request() -> None:
    router = IntentRouter()
    intent = router.route("liste minuteurs")
    assert intent.name == "list_timers"
    assert intent.language == "fr"
