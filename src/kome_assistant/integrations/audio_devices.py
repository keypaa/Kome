from __future__ import annotations


def list_audio_devices() -> list[str]:
    """Return a formatted list of local audio devices.

    If sounddevice is unavailable, return a single explanation line.
    """
    try:
        import sounddevice as sd
    except ImportError:
        return ["sounddevice not installed; install optional audio dependencies"]

    devices = sd.query_devices()
    result: list[str] = []
    for idx, device in enumerate(devices):
        name = str(device.get("name", "unknown"))
        max_in = int(device.get("max_input_channels", 0) or 0)
        max_out = int(device.get("max_output_channels", 0) or 0)
        default_rate = float(device.get("default_samplerate", 0.0) or 0.0)
        result.append(
            f"[{idx}] {name} | in={max_in} out={max_out} rate={default_rate:.0f}"
        )
    return result
