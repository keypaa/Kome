from pathlib import Path

from kome_assistant.tools.registry import default_tool_registry


def test_get_time_tool_executes() -> None:
    tools = default_tool_registry()
    result = tools.execute("get_time", {})
    assert result.ok is True
    assert "Heure locale" in result.message


def test_missing_args_returns_error() -> None:
    tools = default_tool_registry()
    result = tools.execute("set_timer", {})
    assert result.ok is False
    assert "Arguments manquants" in result.message


def test_invalid_timer_arg_is_rejected(tmp_path: Path) -> None:
    tools = default_tool_registry(data_dir=tmp_path)
    result = tools.execute("set_timer", {"minutes": 999})
    assert result.ok is False
    assert "Arguments invalides" in result.message


def test_timer_is_persisted_and_listed(tmp_path: Path) -> None:
    tools = default_tool_registry(data_dir=tmp_path)
    created = tools.execute("set_timer", {"minutes": 7})
    listed = tools.execute("list_timers", {})
    assert created.ok is True
    assert listed.ok is True
    assert listed.payload["timers"]
    assert listed.payload["timers"][0]["minutes"] == 7
