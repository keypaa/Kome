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

Live microphone mode:

```bash
kome --mode voice-live --voice-profile local --live-mode continuous --record-seconds 2.5
```

In continuous mode, microphone capture uses chunk streaming (callback-based audio input).
Adaptive chunk sizing is enabled by default in continuous mode.

Latency benchmark mode:

```bash
kome --mode bench
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

Live microphone mode:

```powershell
kome --mode voice-live --voice-profile local --live-mode continuous --record-seconds 2.5
```

Latency benchmark mode:

```powershell
kome --mode bench
```

Voice backend profile selection:

```powershell
kome --mode voice-sim --voice-profile local
```

Enable real local STT/TTS backends for local profile:

```powershell
$env:KOME_STT_MODE="faster-whisper"
$env:KOME_STT_MODEL="small"
$env:KOME_STT_DEVICE="cpu"
$env:KOME_STT_COMPUTE_TYPE="int8"

$env:KOME_TTS_MODE="piper1-gpl"
$env:KOME_PIPER_BIN="piper"
$env:KOME_PIPER_MODEL="C:\models\fr_FR-upmc-medium.onnx"
kome --mode voice-live --voice-profile local
```

Optional wake-word phrase gate:

```powershell
kome --mode voice-live --voice-profile local --wake-word "ok kome"
```

Optional openWakeWord audio gate:

```powershell
kome --mode voice-live --voice-profile local --wake-word "ok kome" --wake-backend openwakeword --wake-threshold 0.5
```

Tune adaptive chunk bounds:

```powershell
kome --mode voice-live --live-mode continuous --chunk-min-seconds 0.8 --chunk-max-seconds 3.0 --chunk-step-seconds 0.2
```

Disable barge-in interruption (default is enabled):

```powershell
kome --mode voice-live --no-barge-in
```

Disable adaptive chunk tuning:

```powershell
kome --mode voice-live --no-adaptive-chunk
```

Manual capture mode (press Enter each turn):

```powershell
kome --mode voice-live --live-mode manual --record-seconds 3
```

Install optional Python dependencies for real STT adapter:

```powershell
pip install -e .[voice]
```

Install optional Python dependencies for live audio I/O:

```powershell
pip install -e .[audio]
```

Notes:

- The maintained Piper project is piper1-gpl.
- The TTS adapter executes a local piper-compatible binary via subprocess.
- If faster-whisper or Piper model/binary are not available, local profile falls back to mock adapters.
- If microphone or playback optional dependencies are missing, voice-live mode reports a local setup error and exits safely.
- If openwakeword is unavailable and `--wake-backend openwakeword` is requested, runtime falls back to phrase wake-word.
- In voice-live mode, barge-in is enabled by default: user speech during playback interrupts TTS.
- When openWakeWord backend is active, runtime logs wake-word confidence per turn.

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

- Add wake-word backend alternatives (Porcupine/openWakeWord) with richer confidence logging
- Add robust device arbitration for full-duplex capture/playback across different audio hardware
- Add adaptive chunk sizing and buffering controls to tune latency vs accuracy
