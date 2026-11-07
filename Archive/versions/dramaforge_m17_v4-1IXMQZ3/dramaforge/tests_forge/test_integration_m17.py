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


def _tiny_video(path, seconds=1.0):
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    f"testsrc=duration={seconds}:size=160x120:rate=10",
                    "-pix_fmt", "yuv420p", str(path)],
                   capture_output=True, check=True)


def test_lipsync_cli_no_detector_marks_unchecked(tmp_path):
    import json, subprocess, sys
    clip = tmp_path / "c.mp4"
    _tiny_video(clip)
    out = subprocess.run(
        [sys.executable, "-m", "forge.assemble.lipsync", str(clip),
         "a.wav", "--out", str(tmp_path / "o.mp4"), "--detector", "none"],
        capture_output=True, text=True)
    assert out.returncode == 0
    job = json.loads(out.stdout)
    assert job["refused"] is False
    assert job["face_policy"]["verdict"] == "unchecked"
    assert "scripts.inference" in job["cmd"]


def test_lipsync_cli_refuses_multiface(tmp_path, monkeypatch):
    import sys, types
    from forge.assemble import lipsync
    clip = tmp_path / "c.mp4"
    _tiny_video(clip)
    # fake mediapipe: two comparable-area faces in every frame -> unsupported
    lm = [types.SimpleNamespace(x=0.1 + (i % 22) * 0.02, y=0.1 + (i // 22) * 0.02) for i in range(478)]
    face_a = types.SimpleNamespace(landmark=lm)
    face_b = types.SimpleNamespace(landmark=lm)
    res = types.SimpleNamespace(multi_face_landmarks=[face_a, face_b])

    class FakeFM:
        def __init__(self, **kw):
            pass

        def process(self, frame):
            return res

    fake_mp = types.ModuleType("mediapipe")
    fake_mp.solutions = types.SimpleNamespace(
        face_mesh=types.SimpleNamespace(FaceMesh=FakeFM))
    monkeypatch.setitem(sys.modules, "mediapipe", fake_mp)
    rc = lipsync.main([str(clip), "a.wav", "--out", "o.mp4",
                       "--detector", "mediapipe"])
    assert rc == 3


def _fake_two_faces(_frame):
    lm = [(0.0, 0.0)] * 300
    return [{"landmarks": lm, "box": (10, 10, 100, 100)},
            {"landmarks": lm, "box": (200, 10, 290, 100)}]


def test_multiface_per_face_plan_with_speaker_box():
    from forge.assemble import lipsync
    clip = "/tmp/shots/multiface.mp4"
    job = lipsync.lipsync_job_multiface(clip, "a.wav", "o.mp4",
                                        speaker_box=(5, 5, 105, 105),
                                        detect_fn=_fake_two_faces)
    assert job["route"] == "per-face"
    assert len(job["cmds"]) == 3
    assert job["face_policy"]["review_required"] is True
    assert job["face_policy"]["verdict"] == "unsupported"


def test_multiface_guard_refuses_bystander_overlap():
    import pytest
    from forge.assemble import lipsync
    from forge.gates.common import GateLocked
    # speaker box over face A's area but excluding its centre, swallowing
    # half of face B -> compositing would modify the bystander
    with pytest.raises(GateLocked, match="bystander|overlaps"):
        lipsync.lipsync_job_multiface("/tmp/shots/multiface.mp4", "a.wav",
                                      "o.mp4", speaker_box=(50, 5, 210, 105),
                                      detect_fn=_fake_two_faces)


def test_composite_pixels_land_only_in_speaker_box(tmp_path):
    import subprocess, cv2, numpy as np
    from forge.assemble import lipsync
    src = tmp_path / "two.mp4"
    # 1s video: left half red (speaker), right half blue (bystander)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "color=red:size=160x240:duration=1:rate=10",
                    "-f", "lavfi", "-i", "color=blue:size=160x240:duration=1:rate=10",
                    "-filter_complex", "[0:v][1:v]hstack[v]",
                    "-map", "[v]", "-pix_fmt", "yuv420p", str(src)],
                   capture_output=True, check=True)
    out = tmp_path / "comp.mp4"
    cmds = lipsync.multiface_cmds(str(src), "a.wav", str(out),
                                  box=(0, 0, 160, 240))
    subprocess.run(cmds[0], shell=True, capture_output=True, check=True)
    # identity "sync": the GPU step is stubbed by re-encoding the crop
    subprocess.run(["ffmpeg", "-y", "-i", "/tmp/face_crop.mp4",
                    "-pix_fmt", "yuv420p", "/tmp/face_sync.mp4"],
                   capture_output=True, check=True)
    subprocess.run(cmds[2], shell=True, capture_output=True, check=True)
    cap_o, cap_c = cv2.VideoCapture(str(src)), cv2.VideoCapture(str(out))
    ok_o, f_o = cap_o.read()
    ok_c, f_c = cap_c.read()
    assert ok_o and ok_c
    left_o, right_o = f_o[:, :160], f_o[:, 160:]
    left_c, right_c = f_c[:, :160], f_c[:, 160:]
    # bystander side untouched; speaker side equals the crop content
    assert np.abs(right_c.astype(int) - right_o.astype(int)).mean() < 2.0
    assert left_c[:, :, 2].mean() > 150  # still red
    cap_o.release(); cap_c.release()


def test_speaker_captions_styles_and_render(tmp_path):
    import subprocess
    from forge.assemble.speaker_captions import write_speaker_ass, YELLOW
    ass = write_speaker_ass(
        [{"speaker": "VIVIAN", "text": "You fancy him?", "start": 0, "end": 1.5},
         {"speaker": "DRACONIA", "text": "I'd rather fail Potions",
          "start": 1.6, "end": 3.0}],
        str(tmp_path / "dlg.ass"),
        overrides={"DRACONIA": {"color": YELLOW, "italic": True, "prefix": ""}})
    content = open(ass).read()
    assert "spk_VIVIAN" in content and "spk_DRACONIA" in content
    assert ">> You fancy him?" in content  # default first-speaker prefix
    # renders onto a real frame through libass
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "color=black:size=1080x1920:duration=3.2:rate=10",
                    "-vf", f"ass={ass}", "-pix_fmt", "yuv420p",
                    str(tmp_path / "cap.mp4")],
                   capture_output=True, check=True)


def test_speaker_captions_clean_input_no_collision(tmp_path):
    """Clean-input integration: burn a two-speaker ASS onto video with NO
    pre-existing captions and verify each speaker's line renders as one
    caption band (no stacked/colliding text rows) with readable contrast."""
    import subprocess
    import numpy as np
    import cv2
    from forge.assemble.speaker_captions import write_speaker_ass

    # clean 1280x720 video: gradient background, no text anywhere
    vw = cv2.VideoWriter(str(tmp_path / "clean.mp4"),
                         cv2.VideoWriter_fourcc(*"mp4v"), 30, (1280, 720))
    for i in range(150):
        f = np.tile(np.linspace(40, 160, 720, dtype=np.uint8)[:, None, None],
                    (1, 1280, 3))
        vw.write(f)
    vw.release()
    segs = [
        {"speaker": "Malfoid", "start": 0.0, "end": 2.4,
         "text": "You followed me through the gate."},
        {"speaker": "Wren", "start": 2.4, "end": 4.4,
         "text": "I followed the light, not you."},
    ]
    ass = write_speaker_ass(segs, str(tmp_path / "spk.ass"),
                            w=1280, h=720, margin_v=60)
    subprocess.run(["ffmpeg", "-y", "-i", str(tmp_path / "clean.mp4"),
                    "-vf", f"ass={ass}", str(tmp_path / "burned.mp4")],
                   check=True, capture_output=True)

    def frame_at(t):
        n = int(t * 30)
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(tmp_path / "burned.mp4"),
             "-vf", f"select='eq(n\\,{n})'", "-frames:v", "1",
             str(tmp_path / f"f{t}.png")], check=True, capture_output=True)
        return cv2.imread(str(tmp_path / f"f{t}.png"))

    for t in (1.0, 3.0):
        fr = frame_at(t)
        assert fr is not None
        bottom = fr[600:720]  # caption zone above the margin
        bright_rows = (bottom.max(axis=(1, 2)) > 220).nonzero()[0]
        assert len(bright_rows) > 20, f"no caption rendered at t={t}"
        # a single caption line: bright rows form ONE contiguous band
        gaps = np.diff(bright_rows)
        assert (gaps > 10).sum() == 0, \
            f"caption collision: split into multiple text bands at t={t}"
        # contrast: dark outline pixels surround the bright glyph pixels
        band = bottom[bright_rows.min():bright_rows.max() + 1]
        assert (band.max(axis=2) < 60).sum() > 500, \
            f"no dark outline around caption at t={t}"


def test_speaker_captions_margin_override_raises_block(tmp_path):
    """Inputs that already carry bottom captions: a larger margin_v must
    move the new caption block up, verified from the generated ASS."""
    import pysubs2
    from forge.assemble.speaker_captions import write_speaker_ass
    segs = [{"speaker": "Malfoid", "start": 0.0, "end": 1.0, "text": "hi"}]
    low = write_speaker_ass(segs, str(tmp_path / "low.ass"), margin_v=60)
    high = write_speaker_ass(segs, str(tmp_path / "high.ass"), margin_v=420)
    mv_low = pysubs2.load(low).styles["spk_Malfoid"].marginv
    mv_high = pysubs2.load(high).styles["spk_Malfoid"].marginv
    assert (mv_low, mv_high) == (60, 420)


def test_compose_wires_speaker_segments_to_speaker_ass(tmp_path, monkeypatch):
    """The assembly entrypoint must route speaker_segments through the
    per-speaker caption writer, not the plain two-layer hierarchy."""
    import forge.assemble.compose as compose_mod
    calls = {}

    def fake_run(cmd, check):
        calls["cmd"] = cmd
        return None
    monkeypatch.setattr(compose_mod.subprocess, "run", fake_run)
    segs = [{"speaker": "Malfoid", "start": 0.0, "end": 1.0, "text": "hi"},
            {"speaker": "Wren", "start": 1.0, "end": 2.0, "text": "yo"}]
    out = compose_mod.burn_speaker_captions(
        "in.mp4", segs, str(tmp_path / "out.mp4"),
        ass_path=str(tmp_path / "spk.ass"), w=1280, h=720)
    text = (tmp_path / "spk.ass").read_text()
    assert "spk_Malfoid" in text and "spk_Wren" in text
    assert ">> hi" in text  # first speaker prefix present in burned dialogue
    assert any("ass=" in str(c) for c in calls["cmd"])
    assert out.endswith("out.mp4")


def test_compose_prefers_speaker_segments_over_plain_hierarchy(tmp_path, monkeypatch):
    """compose() with speaker_segments burns the speaker ASS after writing
    the silent assembly; the plain hierarchy is not stacked on top."""
    import forge.assemble.compose as compose_mod
    burned = {}
    monkeypatch.setattr(compose_mod, "burn_speaker_captions",
                        lambda v, s, o, **kw: burned.update(route="speaker") or o)
    monkeypatch.setattr(compose_mod, "burn_caption_hierarchy",
                        lambda *a, **kw: burned.update(route="plain") or a[3])

    class FakeClip:
        def close(self):
            pass
    class FakeV:
        def write_videofile(self, path, **kw):
            open(path, "w").write("vid")  # stand-in silent assembly
        def with_audio(self, a):
            return self
        duration = 1.0
    monkeypatch.setattr(compose_mod, "VideoFileClip", lambda p: FakeClip())
    monkeypatch.setattr(compose_mod, "concatenate_videoclips",
                        lambda clips, method=None: FakeV())
    out = compose_mod.compose(["a.mp4"], None, None, str(tmp_path / "o.mp4"),
                              speaker_segments=[{"speaker": "M", "start": 0.0,
                                                 "end": 1.0, "text": "hi"}],
                              words=[{"word": "hi", "start": 0.0, "end": 0.4}])
    assert burned["route"] == "speaker"


def test_kaggle_scripts_wire_speaker_box_route():
    """Both GPU job scripts pass --speaker-box through the gate, infer on
    the crop, and composite back - the per-face route end to end."""
    for script in ("docs/kaggle_lipsync_job.sh", "docs/kaggle_lipsync_infer.sh"):
        text = open(script).read()
        assert '--speaker-box $SPEAKER_BOX' in text
        assert "crop=$((X2-X1)):$((Y2-Y1)):$X1:$Y1" in text
        assert "--video_path $INFER_IN" in text
        assert "overlay=$X1:$Y1" in text
        assert "STEP_COMPOSITE_DONE_" in text
