from __future__ import annotations

from kome_assistant.core.orchestrator import AssistantOrchestrator
from kome_assistant.core.router import IntentRouter
from kome_assistant.tools.registry import default_tool_registry


def main() -> None:
    router = IntentRouter()
    tools = default_tool_registry()
    orchestrator = AssistantOrchestrator(router=router, tools=tools)

    print("Kome local assistant (text mode). Type 'exit' to quit.")
    while True:
        user_input = input("you> ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("bye")
            break
        result = orchestrator.handle_text_turn(user_input)
        print(f"assistant> {result.reply_text}")


if __name__ == "__main__":
    main()
