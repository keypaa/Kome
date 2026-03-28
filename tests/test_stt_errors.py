import builtins

from kome_assistant.integrations.stt import FasterWhisperSTTEngine


def test_faster_whisper_import_error_reports_not_installed(monkeypatch) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001
        if name == "faster_whisper":
            raise ImportError("No module named faster_whisper")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    engine = FasterWhisperSTTEngine()
    try:
        engine._load_model()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "not installed" in str(exc)


def test_faster_whisper_blocked_dll_reports_policy_issue(monkeypatch) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001
        if name == "faster_whisper":
            raise OSError("Une strategie de controle d'application a bloque ce fichier")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    engine = FasterWhisperSTTEngine()
    try:
        engine._load_model()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "application control policy" in str(exc)
