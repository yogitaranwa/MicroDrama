"""m17 integration: the new modules wired into real entry points, exercised
through CLIs and pipeline pickups, not only as isolated functions."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from forge.gates.common import GateLocked, state_dir

REPO = Path(__file__).resolve().parent.parent


def _cli(module, *args, cwd=None, expect=0):
    r = subprocess.run([sys.executable, "-m", module, *map(str, args)],
                       cwd=cwd or REPO, capture_output=True, text=True)
    if expect is not None and r.returncode != expect:
        raise AssertionError(f"{module} {args} -> {r.returncode}\n{r.stderr[-800:]}")
    return r


# --- archive: CLI roundtrip + continuity gate --------------------------------

def test_archive_cli_roundtrip_and_continuity(tmp_path):
    s1 = tmp_path / "s1"
    (s1 / "characters").mkdir(parents=True)
    (s1 / "characters" / "a.png").write_bytes(b"aaa")
    arc = tmp_path / "s1.zip"
    _cli("forge.season_archive", "write", s1, arc, "--season", "S1")
    r = _cli("forge.season_archive", "read", arc, tmp_path / "out")
    assert "verified 1 assets" in r.stdout
    r = _cli("forge.season_archive", "continuity", arc, tmp_path / "out")
    assert "continuity ok" in r.stdout
    # next season missing the inherited character -> the CLI gate fails closed
    (tmp_path / "out" / "characters" / "a.png").unlink()
    _cli("forge.season_archive", "continuity", arc, tmp_path / "out", expect=1)


# --- intake: CLI binds, script stage picks the form's brief up ----------------

def test_intake_cli_binds_and_script_stage_uses_it(tmp_path):
    img = tmp_path / "c.png"
    img.write_bytes(b"\x89PNG fake")
    form = {"genre": "gothic rivalry", "num_characters": 1,
            "description": "A botanist duels a critic over one rare flower.",
            "characters": [{"name": "Ivy", "description": "precise, wry",
                            "reference": {"mode": "upload", "path": str(img)}}]}
    f = tmp_path / "form.json"
    f.write_text(json.dumps(form))
    r = _cli("forge.intake", tmp_path, f)
    assert "gothic rivalry" in r.stdout and "botanist" in r.stdout
    from forge.script_run import active_brief
    brief = active_brief(tmp_path)
    assert "A botanist duels a critic" in brief
    assert "Ivy" in brief
    # a project with no intake keeps the development brief
    from forge.script_run import BRIEF
    assert active_brief(tmp_path / "other") == BRIEF


# --- preflight: CLI walks the real plan, quality check on a real file ---------

def test_preflight_cli_on_project(tmp_path):
    plan = [{"plan_n": 1, "src_shot": 1, "kind": "dialogue", "speaker": "A",
             "camera": "close-up", "location": "hall", "action": "turns",
             "line": {"speaker": "A", "text": "Line."}, "seconds": 6}]
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "e01_plan.json").write_text(json.dumps(plan))
    (state_dir(tmp_path) / "ledger.json").write_text(
        json.dumps({"approved": 1000, "spent": 0}))
    r = _cli("forge.preflight", tmp_path, "--model", "veo3.1-lite", expect=1)
    rep = json.loads(r.stdout)
    assert rep["n_jobs"] == 1 and not rep["ok"]  # stills not locked
    assert json.loads((state_dir(tmp_path) / "ledger.json").read_text())["spent"] == 0


def test_quality_cli_on_real_episode():
    ep = REPO / "out"
    # synthetic but full ffmpeg encode, produced here so the CLI path runs
    vid = REPO / "out" / "quality_cli_probe.mp4"
    vid.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc=duration=3:size=160x90:rate=10",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest",
                    str(vid)], check=True)
    try:
        r = _cli("forge.preflight", "--quality", vid)
        rep = json.loads(r.stdout)
        assert rep["ok"] and rep["audio_streams"] == 1
    finally:
        vid.unlink()


# --- vertical: CLI converts a real file ---------------------------------------

def test_vertical_cli_reframes(tmp_path):
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc=duration=2:size=160x90:rate=10",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)], check=True)
    dst = tmp_path / "out.mp4"
    r = _cli("forge.assemble.vertical", src, dst, "--mode", "center",
             "--size", "90x160")
    rep = json.loads(r.stdout)
    assert rep["out_size"] == [90, 160] and dst.exists()


# --- lipsync: face policy gates the GPU command --------------------------------

from forge.assemble.lipsync import lipsync_job
from forge.assemble import face_policy


def _lm(nose=0.5, le=0.4, re_=0.6):
    lm = np.zeros((478, 2))
    lm[1] = (nose * 100, 50); lm[33] = (le * 100, 50); lm[263] = (re_ * 100, 50)
    return lm


def test_lipsync_job_refuses_multiface_and_flags_unchecked(tmp_path):
    vid = tmp_path / "shot.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc=duration=1:size=64x64:rate=5",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(vid)], check=True)
    two_faces = lambda frame: [{"landmarks": _lm(), "box": (0, 0, 30, 30)},
                               {"landmarks": _lm(), "box": (32, 0, 62, 30)}]
    with pytest.raises(GateLocked, match="multi-face"):
        lipsync_job(str(vid), "a.wav", "out.mp4", detect_fn=two_faces)
    front = lambda frame: [{"landmarks": _lm(), "box": (0, 0, 30, 30)}]
    job = lipsync_job(str(vid), "a.wav", "out.mp4", detect_fn=front)
    assert job["face_policy"]["verdict"] == "ok"
    assert "latentsync" in job["cmd"] or "scripts.inference" in job["cmd"]
    job = lipsync_job(str(vid), "a.wav", "out.mp4")
    assert job["face_policy"]["verdict"] == "unchecked"  # never silently ok


# --- reception: CLI record + aggregate -----------------------------------------

def test_reception_cli(tmp_path):
    store = tmp_path / "r.jsonl"
    _cli("forge.reception", store, "record", "EP01", "viewer-a", 4, 3)
    _cli("forge.reception", store, "record", "EP01", "viewer-b", 2, 5)
    r = _cli("forge.reception", store, "aggregate")
    agg = json.loads(r.stdout)
    assert agg["episodes"]["EP01"]["viewings"] == 2
    _cli("forge.reception", store, "record", "EP01", "viewer-c", 9, 3, expect=1)


# --- gates CLI: fullspeed recorded through the CLI gates delivery --------------

def test_gates_cli_fullspeed_then_deliver(tmp_path):
    ep = tmp_path / "ep.mp4"
    ep.write_bytes(b"episode-bytes")
    _cli("forge.gates", "review", tmp_path, ep, "--shots", "s1:10", "--lip-sync-done")
    _cli("forge.gates", "signoff", tmp_path, "reviewer-a")
    _cli("forge.gates", "deliver", tmp_path, ep, tmp_path / "out", expect=1)  # no fullspeed yet
    _cli("forge.gates", "fullspeed", tmp_path, "reviewer-a",
         "--episode", ep, "--verdict", "approved",
         "--obs", "3.0:visual:clean cut")
    r = _cli("forge.gates", "deliver", tmp_path, ep, tmp_path / "out")
    assert "delivered" in r.stdout
    r = _cli("forge.gates", "status", tmp_path)
    assert "fullspeed_review.json" in r.stdout
