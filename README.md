# Kome Assistant Brain

Local-first assistant brain for a custom smart clock.

## Current state

- Fully local text-first MVP pipeline (no cloud API usage)
- Deterministic intent routing for French-first commands
- Tool execution framework with whitelist and argument guardrails
- SQLite local state persistence for timers
- Interactive CLI loop for end-to-end testing

## Architecture (current MVP baseline)

1. Input (text for now, voice later)
2. Intent router (regex-based fast path)
3. Tool planner (deterministic; LLM planner hook provided)
4. Tool executor (whitelisted tools)
5. Response generation
6. Output (text for now, TTS hook provided)

## Run

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
kome
```

Simulated voice pipeline mode:

```bash
kome --mode voice-sim
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
kome
```

Simulated voice pipeline mode:

```powershell
kome --mode voice-sim
```

Type a command in French or English.

Examples:

- `mets un minuteur de 5 minutes`
- `quelle heure est-il`
- `allume la lumiere du salon`
- `search docs raspberry pi`
- `liste minuteurs`

## GitHub workflow

1. Create a new GitHub repository (empty).
2. Add the remote:

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
```

3. First push:

```bash
git add .
git commit -m "feat: bootstrap local assistant brain MVP"
git push -u origin main
```

## Next implementation goals

- Replace mock voice adapters with real wake-word + VAD + STT integrations
- Replace mock TTS with Piper runtime and audio playback
- Add benchmark harness for 2-4s latency targets
