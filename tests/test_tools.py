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
