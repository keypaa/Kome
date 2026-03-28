# Architecture Notes

## Goals

- Local-first runtime
- French-first interactions with English fallback
- 2-4 second end-to-end response target
- Modular pipeline with swappable model backends

## Baseline modules

- `core/contracts.py`: Shared data contracts and tool schemas.
- `core/router.py`: Deterministic intent extraction.
- `core/orchestrator.py`: End-to-end turn orchestration.
- `tools/registry.py`: Tool registration, validation, execution.
- `memory/state_store.py`: SQLite-backed local state persistence.
- `integrations/*`: Model/backend adapter stubs.

## Implemented guardrails

- Tool whitelist in registry.
- Required argument checks per tool.
- Argument validator checks (bounds/enums/non-empty constraints).
- Unknown or invalid tool invocations return deterministic denials.

## Migration path

1. Keep deterministic router as fast path.
2. Add STT model integration (`faster-whisper`) behind adapter.
3. Add LLM planner adapter (`llama.cpp` runtime).
4. Keep strict tool schema validation before execution.
5. Add TTS adapter (`Piper`) for response output.
