from __future__ import annotations

import json
import subprocess
from pathlib import Path


def ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except FileNotFoundError:
        return False


def extract_contact_frames(video: str | Path, out_dir: str | Path, fps: int = 2) -> list[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pattern = str(out / "frame-%05d.jpg")
    cmd = ["ffmpeg", "-y", "-i", str(video), "-vf", f"fps={fps}", pattern]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return sorted(str(p) for p in out.glob("frame-*.jpg"))


def make_contact_sheet(input_dir: str | Path, out_path: str | Path, tile: str = "4x5") -> None:
    files = sorted(Path(input_dir).glob("*.jpg")) + sorted(Path(input_dir).glob("*.png"))
    if not files:
        raise ValueError("No jpg/png images found")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(files[0]),
        "-vf", f"tile={tile}",
        str(out_path)
    ]
    raise RuntimeError("Use montage or a Pillow-based sheet for arbitrary image lists; ffmpeg tile accepts one video stream")


def qa_report(video: str | Path) -> dict[str, object]:
    report: dict[str, object] = {"video": str(video), "checks": {}}
    if not Path(video).exists():
        report["checks"]["exists"] = False
        return report
    report["checks"]["exists"] = True
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,r_frame_rate", "-of", "json", str(video)
    ], check=True, capture_output=True, text=True)
    report["ffprobe"] = json.loads(probe.stdout)
    black = subprocess.run([
        "ffmpeg", "-i", str(video), "-vf", "blackdetect=d=0.25:pix_th=0.10", "-an", "-f", "null", "-"
    ], capture_output=True, text=True)
    report["blackdetect_stderr"] = black.stderr
    return report


def full_qa_report(video: str | Path,
                   dialogue_windows: list[dict[str, float]] | None = None) -> dict[str, object]:
    """Legacy probe/blackdetect checks plus the mechanical detector report.

    Everything here is signal measurement. It does not establish actions,
    emotion or lip sync; see reviewgate.py for the review-bound gate.
    """
    from .detectors import mechanical_report
    report = qa_report(video)
    report["mechanical"] = mechanical_report(video, dialogue_windows=dialogue_windows)
    report["mechanical_pass"] = report["mechanical"]["mechanical_pass"]
    return report
