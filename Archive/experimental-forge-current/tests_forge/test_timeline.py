import os, subprocess, tempfile
from forge.assemble.timeline import build_timeline, export, durations
from forge.assemble.scenecheck import single_take

def test_timeline_roundtrip(tmp_path):
    shots = [{"n": 1, "clip": "a.mp4", "seconds": 10, "lines": [{"speaker": "Harry", "text": "x"}]},
             {"n": 2, "clip": "b.mp4", "seconds": 12.5, "audio": "v2.wav"}]
    p = export(build_timeline(shots), str(tmp_path / "e.otio"))
    assert durations(p) == [10.0, 12.5]

def test_single_take(tmp_path):
    f = str(tmp_path / "t.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=d=2:s=160x90:r=24", f], check=True)
    assert single_take(f)
