from kome_assistant.tools.builtin import get_time, toggle_light
from kome_assistant.tools.registry import ToolPolicy, ToolRegistry, ToolSpec


def test_confirmation_required_in_strict_mode() -> None:
    registry = ToolRegistry(
        policy=ToolPolicy(
            strict_confirmations=True,
            require_confirmation_for={"toggle_light"},
        )
    )
    registry.register(
        ToolSpec(
            name="toggle_light",
            fn=toggle_light,
            required_args=("room", "state"),
        )
    )

    denied = registry.execute("toggle_light", {"room": "salon", "state": "on"})
    assert denied.ok is False
    assert denied.payload and denied.payload.get("deny_code") == "CONFIRMATION_REQUIRED"

    accepted = registry.execute("toggle_light", {"room": "salon", "state": "on", "confirmed": True})
    assert accepted.ok is True


def test_rate_limit_denial() -> None:
    registry = ToolRegistry(policy=ToolPolicy(rate_limit_count=1, rate_limit_window_seconds=60.0))
    registry.register(ToolSpec(name="get_time", fn=get_time))

    first = registry.execute("get_time", {})
    assert first.ok is True

    second = registry.execute("get_time", {})
    assert second.ok is False
    assert second.payload and second.payload.get("deny_code") == "RATE_LIMIT"
