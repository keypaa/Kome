from kome_assistant.integrations.wake_word import PhraseWakeWordDetector


def test_phrase_wake_word_triggers_and_strips_prefix() -> None:
    detector = PhraseWakeWordDetector(["ok kome"])
    decision = detector.evaluate("ok kome allume la lumiere")
    assert decision.triggered is True
    assert decision.text_without_wake_word == "allume la lumiere"


def test_phrase_wake_word_does_not_trigger_without_prefix() -> None:
    detector = PhraseWakeWordDetector(["ok kome"])
    decision = detector.evaluate("allume la lumiere")
    assert decision.triggered is False
    assert decision.text_without_wake_word == ""


def test_phrase_wake_word_triggers_with_leading_filler() -> None:
    detector = PhraseWakeWordDetector(["ok kome"])
    decision = detector.evaluate("euh ok kome allume la lumiere")
    assert decision.triggered is True
    assert decision.text_without_wake_word == "allume la lumiere"


def test_phrase_wake_word_alias_triggers() -> None:
    detector = PhraseWakeWordDetector(["ok kome", "ok paul"])
    decision = detector.evaluate("bonjour ok paul mets un minuteur 2")
    assert decision.triggered is True
    assert decision.text_without_wake_word == "mets un minuteur 2"
