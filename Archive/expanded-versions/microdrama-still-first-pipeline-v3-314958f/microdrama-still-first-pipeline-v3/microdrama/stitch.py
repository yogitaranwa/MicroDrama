from __future__ import annotations

import json
import subprocess
from pathlib import Path


def stitch(timeline_path: str | Path, out_path: str | Path) -> None:
    timeline = json.loads(Path(timeline_path).read_text())
    concat = Path(out_path).with_suffix(".concat.txt")
    with concat.open("w") as f:
        for item in timeline:
            clip = Path(item["video"])
            if not clip.exists():
                raise FileNotFoundError(clip)
            f.write(f"file '{clip}'\n")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(out_path)
    ], check=True)
