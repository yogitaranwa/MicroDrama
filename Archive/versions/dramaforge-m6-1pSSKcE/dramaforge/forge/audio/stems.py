"""Demucs (MIT) stem separation: strip background from voice references, and build a ducked music bed."""
import subprocess, pathlib

def separate_vocals(wav: str, out_dir: str = "out/stems", model: str = "htdemucs") -> tuple:
    subprocess.run(["python", "-m", "demucs", "--two-stems=vocals", "-n", model, "-o", out_dir, wav], check=True)
    d = pathlib.Path(out_dir) / model / pathlib.Path(wav).stem
    return str(d / "vocals.wav"), str(d / "no_vocals.wav")
