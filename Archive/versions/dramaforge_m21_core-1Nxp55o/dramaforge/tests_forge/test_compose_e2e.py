"""End-to-end: the ORDINARY compose() path burns the caption hierarchy.
Real moviepy + ffmpeg + libass, free fixtures (color clips + sine tone).
Skipped only if the media toolchain is missing."""
import shutil
import subprocess
import pytest

moviepy = pytest.importorskip("moviepy")
pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")


def _fixtures(tmp_path):
    shots = []
    for i, colour in enumerate(("0x1a1a2e", "0x2e1a1a")):
        p = str(tmp_path / f"shot{i}.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"color=c={colour}:s=540x960:d=2:r=24", "-pix_fmt", "yuv420p", p], check=True)
        shots.append(p)
    voice = str(tmp_path / "voice.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=4", voice], check=True)
    return shots, voice


def test_compose_burns_hierarchy_in_ordinary_path(tmp_path):
    from forge.assemble.compose import compose
    from forge.assemble.hook_captions import hooks_from_episode
    shots, voice = _fixtures(tmp_path)
    out = str(tmp_path / "episode.mp4")
    words = [{"word": w, "start": 0.2 + i * 0.4, "end": 0.5 + i * 0.4}
             for i, w in enumerate(["Your", "office", "closed", "early."])]
    hooks = hooks_from_episode("She lied about tonight...", "What happens next?", 4.0)
    compose(shots, voice, None, out, words=words, hooks=hooks,
            ass_kw={"w": 540, "h": 960, "size": 28})

    # frame at 1s: yellow hook on top, white dialogue at the bottom
    frame = str(tmp_path / "f1.png")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "1.0", "-i", out,
                    "-frames:v", "1", frame], check=True)
    from PIL import Image
    img = Image.open(frame).convert("RGB")
    w, h = img.size
    px = img.load()
    def count(box, pred):
        l, t, r, b = box
        return sum(1 for y in range(t, b, 2) for x in range(l, r, 2) if pred(px[x, y]))
    yellow = lambda c: c[0] > 180 and c[1] > 180 and c[2] < 110
    white = lambda c: c[0] > 225 and c[1] > 225 and c[2] > 225
    assert count((0, int(h*0.03), w, int(h*0.25)), yellow) > 40, "no yellow hook at top"
    assert count((0, int(h*0.65), w, int(h*0.95)), white) > 40, "no white dialogue at bottom"
    assert count((0, int(h*0.65), w, int(h*0.95)), yellow) < 10, "yellow leaked to bottom"

    # frame at 3.8s: yellow cliffhanger on top, dialogue already over
    frame2 = str(tmp_path / "f2.png")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "3.8", "-i", out,
                    "-frames:v", "1", frame2], check=True)
    img = Image.open(frame2).convert("RGB")
    px = img.load()
    assert count((0, int(h*0.03), w, int(h*0.25)), yellow) > 40, "no yellow cliffhanger at top"


def test_compose_without_captions_unchanged(tmp_path):
    from forge.assemble.compose import compose
    shots, voice = _fixtures(tmp_path)
    out = str(tmp_path / "plain.mp4")
    compose(shots, voice, None, out)  # no words/hooks: pre-m11 behaviour
    assert not __import__("os").path.exists(out + ".nocaptions.mp4")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", out], capture_output=True, text=True)
    assert 3.0 < float(probe.stdout.strip()) < 5.0
