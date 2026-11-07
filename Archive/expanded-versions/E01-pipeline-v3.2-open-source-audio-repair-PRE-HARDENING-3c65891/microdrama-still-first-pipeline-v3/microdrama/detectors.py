"""Mechanical ffmpeg-based detectors for delivered or candidate video.

Scope, stated plainly: these checks establish measurable signal facts only -
freeze windows, silence windows, loudness levels, black frames. They do NOT
establish that a scripted action happened, that a performance is emotional,
or that lip sync is correct. Those require competent review of actual frames
and listening; see reviewgate.py.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


def _run_stderr(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return proc.stderr


def has_audio_stream(video: str | Path) -> bool:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=index", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=False)
    return bool(proc.stdout.strip())


def detect_freezes(video: str | Path, noise_db: float = -60.0,
                   min_duration_s: float = 2.0) -> list[dict[str, float]]:
    """Return freeze windows >= min_duration_s using ffmpeg freezedetect.

    A window means the measured frames did not change beyond encoder noise.
    It does not say why (static insert, stalled generation, intentional hold).
    """
    stderr = _run_stderr([
        "ffmpeg", "-nostdin", "-i", str(video),
        "-vf", f"freezedetect=n={noise_db}dB:d={min_duration_s}",
        "-an", "-f", "null", "-"])
    starts = [float(m) for m in re.findall(r"freeze_start:\s*([\d.]+)", stderr)]
    ends = [float(m) for m in re.findall(r"freeze_end:\s*([\d.]+)", stderr)]
    durs = [float(m) for m in re.findall(r"freeze_duration:\s*([\d.]+)", stderr)]
    windows = []
    for i, start in enumerate(starts):
        end = ends[i] if i < len(ends) else None
        dur = durs[i] if i < len(durs) else None
        windows.append({"start": start, "end": end, "duration": dur})
    return windows


def detect_silence(video: str | Path, noise_db: float = -38.0,
                   min_duration_s: float = 1.0) -> list[dict[str, float]]:
    """Return silence windows >= min_duration_s using ffmpeg silencedetect."""
    if not has_audio_stream(video):
        return []
    stderr = _run_stderr([
        "ffmpeg", "-nostdin", "-i", str(video),
        "-af", f"silencedetect=n={noise_db}dB:d={min_duration_s}",
        "-vn", "-f", "null", "-"])
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", stderr)]
    windows = []
    for i, start in enumerate(starts):
        windows.append({"start": start, "end": ends[i] if i < len(ends) else None})
    return windows


def measure_loudness(video: str | Path) -> dict[str, float | None]:
    """Integrated LUFS (ebur128) plus volumedetect mean/max for the full file."""
    if not has_audio_stream(video):
        return {"integrated_lufs": None, "mean_db": None, "max_db": None}
    loud = _run_stderr([
        "ffmpeg", "-nostdin", "-i", str(video),
        "-af", "loudnorm=print_format=json", "-vn", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", loud, re.DOTALL)
    integrated = None
    if m:
        try:
            integrated = float(json.loads(m.group(0))["input_i"])
        except (ValueError, KeyError, json.JSONDecodeError):
            integrated = None
    vol = _run_stderr([
        "ffmpeg", "-nostdin", "-i", str(video),
        "-af", "volumedetect", "-vn", "-f", "null", "-"])
    mean = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", vol)
    peak = re.search(r"max_volume:\s*([-\d.]+)\s*dB", vol)
    return {
        "integrated_lufs": integrated,
        "mean_db": float(mean.group(1)) if mean else None,
        "max_db": float(peak.group(1)) if peak else None,
    }


def measure_window_level(video: str | Path, start: float, end: float) -> dict[str, float | None]:
    """volumedetect mean/max over one time window."""
    vol = _run_stderr([
        "ffmpeg", "-nostdin", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
        "-i", str(video), "-af", "volumedetect", "-vn", "-f", "null", "-"])
    mean = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", vol)
    peak = re.search(r"max_volume:\s*([-\d.]+)\s*dB", vol)
    return {
        "start": start, "end": end,
        "mean_db": float(mean.group(1)) if mean else None,
        "max_db": float(peak.group(1)) if peak else None,
    }


def dialogue_free_gaps(duration: float, dialogue_windows: list[dict[str, float]],
                       min_gap_s: float = 0.5, pad_s: float = 0.15) -> list[dict[str, float]]:
    """Compute the gaps between dialogue windows (padded) worth level-checking."""
    spans = sorted((float(w["start"]) - pad_s, float(w["end"]) + pad_s)
                   for w in dialogue_windows)
    merged: list[list[float]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    gaps = []
    cursor = 0.0
    for start, end in merged:
        if start - cursor >= min_gap_s:
            gaps.append({"start": cursor, "end": start})
        cursor = max(cursor, end)
    if duration - cursor >= min_gap_s:
        gaps.append({"start": cursor, "end": duration})
    return gaps


def probe_duration(video: str | Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True)
    return float(proc.stdout.strip())


def mechanical_report(video: str | Path,
                      dialogue_windows: list[dict[str, float]] | None = None,
                      freeze_min_s: float = 2.0, freeze_noise_db: float = -60.0,
                      silence_min_s: float = 1.0, silence_noise_db: float = -38.0,
                      opening_silence_s: float = 0.75,
                      bed_below_mean_db: float = 12.0) -> dict[str, object]:
    """Full mechanical report. Defects are signal facts, each with its scope.

    bed_below_mean_db: a dialogue-free gap whose mean level sits more than this
    many dB below the full-file mean is flagged (music bed effectively absent).
    Level measurements are not audibility verdicts; listening is still required.
    """
    video = str(video)
    duration = probe_duration(video)
    freezes = detect_freezes(video, freeze_noise_db, freeze_min_s)
    silences = detect_silence(video, silence_noise_db, silence_min_s)
    loudness = measure_loudness(video)

    defects: list[dict[str, object]] = []
    for w in freezes:
        defects.append({"type": "freeze", "start": w["start"], "end": w["end"],
                        "duration": w["duration"],
                        "fact": "frames unchanged beyond encoder noise in this window"})
    for w in silences:
        if w["start"] <= 0.05 and (w["end"] or 0) >= opening_silence_s:
            defects.append({"type": "opening_silence", "start": w["start"], "end": w["end"],
                            "fact": "dead air at the open, including no music bed"})
        elif w["start"] > 0.05:
            defects.append({"type": "internal_silence", "start": w["start"], "end": w["end"],
                            "fact": "silence window above threshold"})

    gap_report: list[dict[str, object]] = []
    if dialogue_windows and loudness["mean_db"] is not None:
        for gap in dialogue_free_gaps(duration, dialogue_windows):
            level = measure_window_level(video, gap["start"], gap["end"])
            entry: dict[str, object] = dict(level)
            if level["mean_db"] is not None:
                delta = level["mean_db"] - loudness["mean_db"]
                entry["delta_vs_full_mean_db"] = round(delta, 1)
                if delta <= -bed_below_mean_db:
                    entry["flag"] = "gap far below full-file mean; any bed is effectively absent"
                    defects.append({"type": "bed_level", "start": gap["start"], "end": gap["end"],
                                    "mean_db": level["mean_db"], "delta_db": round(delta, 1),
                                    "fact": "dialogue-free gap level far below full-file mean"})
            gap_report.append(entry)

    return {
        "video": video,
        "duration_seconds": duration,
        "freeze_windows": freezes,
        "silence_windows": silences,
        "loudness": loudness,
        "gap_levels": gap_report,
        "defects": defects,
        "mechanical_pass": not defects,
        "scope": ("Signal measurements only: freeze, silence, levels, black frames. "
                  "Does not establish scripted actions, performance emotion, "
                  "lip-sync correctness, or audibility in real playback."),
    }
