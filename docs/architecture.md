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
- `integrations/*`: Model/backend adapter stubs.

## Migration path

1. Keep deterministic router as fast path.
2. Add STT model integration (`faster-whisper`) behind adapter.
3. Add LLM planner adapter (`llama.cpp` runtime).
4. Keep strict tool schema validation before execution.
5. Add TTS adapter (`Piper`) for response output.
