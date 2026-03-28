from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kome_assistant.integrations.wake_word import AudioWakeWordDetector


@dataclass(slots=True)
class CalibrationPoint:
    threshold: float
    tp: int
    tn: int
    fp: int
    fn: int


def run_wake_calibration(
    detector: AudioWakeWordDetector,
    wav_dir: Path,
    thresholds: list[float],
) -> list[CalibrationPoint]:
    samples = _collect_labeled_samples(wav_dir)
    points: list[CalibrationPoint] = []

    for threshold in thresholds:
        tp = tn = fp = fn = 0
        for expected_positive, wav_path in samples:
            confidence = detector.evaluate_audio(wav_path.read_bytes()).confidence
            predicted_positive = confidence >= threshold
            if expected_positive and predicted_positive:
                tp += 1
            elif not expected_positive and not predicted_positive:
                tn += 1
            elif not expected_positive and predicted_positive:
                fp += 1
            else:
                fn += 1

        points.append(CalibrationPoint(threshold=threshold, tp=tp, tn=tn, fp=fp, fn=fn))
    return points


def _collect_labeled_samples(wav_dir: Path) -> list[tuple[bool, Path]]:
    files = sorted(wav_dir.glob("*.wav"))
    labeled: list[tuple[bool, Path]] = []
    for wav_path in files:
        low = wav_path.name.lower()
        # convention: wake_* is positive, nonwake_* is negative
        if low.startswith("wake_"):
            labeled.append((True, wav_path))
        elif low.startswith("nonwake_"):
            labeled.append((False, wav_path))
    if not labeled:
        raise ValueError("No labeled wav files found. Expected wake_*.wav and nonwake_*.wav")
    return labeled
