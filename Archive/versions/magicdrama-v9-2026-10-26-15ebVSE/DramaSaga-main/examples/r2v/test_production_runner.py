"""Fault-injection tests for production_runner spend-safety. Stubbed transport; no network.
Rule under test: a reservation without a verified provider outcome ALWAYS halts;
only definitive pre-network failure or provider rejection releases it. Balance is diagnostic only."""
import json, sys, types, subprocess
REAL_RUN = subprocess.run  # capture before make_env stubs pr.subprocess.run (same module object)
import os, tempfile as _tf
_dummy_key = _tf.NamedTemporaryFile("w", suffix=".key", delete=False)
_dummy_key.write("TEST-DUMMY-KEY-NOT-REAL"); _dummy_key.close()
os.environ.setdefault("MAGICHOUR_KEY_FILE", _dummy_key.name)
import production_runner as _pre
REAL_AUDIO_LOCK = _pre._audio_lock  # capture before make_env stubs it
from pathlib import Path
from unittest import mock
import requests as real_requests

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT.parents[1]))
import production_runner as pr

class StubResp:
    def __init__(self, code, payload): self.status_code, self._p = code, payload
    def json(self): return self._p
    @property
    def text(self): return json.dumps(self._p)
    @property
    def content(self): return b"video-bytes"

class StubNet:
    exceptions = real_requests.exceptions
    def __init__(self, balance=131219):
        self.bal = balance; self.posts = 0; self.crash_mode = None; self.reject_once = False
    def get(self, url, headers=None, timeout=None):
        if url.endswith("/v1/account"): return StubResp(200, {"credits": self.bal})
        if "/v1/video-projects/" in url:
            return StubResp(200, {"id": "j", "status": "complete", "downloads": [{"url": "https://x/y.mp4"}]})
        return StubResp(200, {}) if not url.startswith("https://api") else StubResp(404, {})
    def post(self, url, headers=None, json=None, timeout=None):
        if url.endswith("/v1/files/upload-urls"):
            return StubResp(200, {"items": [{"upload_url": "https://up", "file_path": "fp-x"}]})
        if url.endswith("/v1/text-to-video"):
            self.posts += 1
            if self.reject_once:
                self.reject_once = False
                return StubResp(400, {"error": "bad request"})
            charge = json["end_seconds"] * 96
            if self.crash_mode == "pre_network":
                raise real_requests.exceptions.ConnectionError("Failed to establish a new connection: [Errno 111] Connection refused")
            if self.crash_mode == "unknown_transport":
                raise real_requests.exceptions.ReadTimeout("HTTPSConnectionPool: Read timed out.")
            if self.crash_mode == "after_accept":
                self.bal -= charge
                raise real_requests.exceptions.ReadTimeout("Read timed out after server accepted")
            self.bal -= charge
            return StubResp(200, {"id": "job-stub-%d" % self.posts, "credits_charged": charge})
        return StubResp(404, {})
    def put(self, *a, **k): return StubResp(200, {})

def make_env(tmp, tag, stub):
    pr.RUN_DIR = Path(tmp) / tag; pr.RUN_DIR.mkdir(parents=True, exist_ok=True)
    pr.POLL_SLEEP = 0
    pr.sha256 = lambda p: "x"
    pr._audio_lock = lambda: {}
    for name in pr.BANK_BY_NAME: pr.BANK_BY_NAME[name]["sha256"] = "x"
    pr.REF_FILES = {n: "/tmp/fake-%s.png" % n for n in pr.REF_FILES}
    for n, f in pr.REF_FILES.items(): Path(f).write_bytes(b"fake")
    pr.requests = stub
    def fake_run(cmd, capture_output=False, text=False):
        vdir = Path(cmd[4]); vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "verify.json").write_text(json.dumps({"video": {"r_frame_rate": "30/1"},
            "envelope_correlation": 0.99, "motion": {"near_static": 0, "sampled": 240}, "audio_track": True, "asr_match": True}))
        return types.SimpleNamespace(returncode=0, stderr="")
    pr.subprocess.run = fake_run

def run_main(argv):
    with mock.patch.object(sys, "argv", ["production_runner.py"] + argv):
        try: pr.main()
        except SystemExit as e: return e.code
    return 0

GO = ["--legacy-t2v", "--approved-cap", "28896", "--approval-ref", "[private-record-reference]", "--only", "e01:3"]
import tempfile

with tempfile.TemporaryDirectory() as tmp:  # T1: exactly one job then gate stop
    stub = StubNet(); make_env(tmp, "t1", stub)
    run_main(GO)
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert stub.posts == 1 and "STOP GATE" in rec.get("stopped", "")
    print("T1 PASS: --only e01:3 = one job, gate stop")

with tempfile.TemporaryDirectory() as tmp:  # T2: definitive pre-network failure releases
    stub = StubNet(); make_env(tmp, "t2", stub)
    stub.crash_mode = "pre_network"
    run_main(GO)
    stub.crash_mode = None
    run_main(GO + ["--resume"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    states = [s["state"] for s in rec["shots"]]
    assert "released_pre_network" in states and "verified" in states, states
    print("T2 PASS: pre-network evidence releases reservation, one resubmission")

with tempfile.TemporaryDirectory() as tmp:  # T3: unknown transport, balance UNCHANGED -> still halt
    stub = StubNet(); make_env(tmp, "t3", stub)
    stub.crash_mode = "unknown_transport"
    run_main(GO)
    assert stub.bal == 131219  # balance unchanged - must NOT authorize resubmit
    stub.crash_mode = None
    code = run_main(GO + ["--resume"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "UNKNOWN TRANSPORT OUTCOME" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 1, "no resubmission over unknown outcome despite unchanged balance"
    print("T3 PASS: unchanged balance does NOT release; unknown transport halts")

with tempfile.TemporaryDirectory() as tmp:  # T4: crash after acceptance (reserved, no evidence) -> halt
    stub = StubNet(); make_env(tmp, "t4", stub)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps({"shots": [
        {"ep": "e01", "shot": 3, "state": "reserved", "intended": 768, "balance_before": 131219}]}))
    code = run_main(GO + ["--resume"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "UNKNOWN SUBMISSION STATE" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0, "reserved-without-outcome must halt before any POST"
    print("T4 PASS: reserved without provider outcome halts regardless of balance")

with tempfile.TemporaryDirectory() as tmp:  # T5: provider rejection releases on resume
    stub = StubNet(); make_env(tmp, "t5", stub)
    stub.reject_once = True
    run_main(GO)
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert rec["shots"][-1]["state"] == "rejected", rec["shots"][-1]
    code = run_main(GO + ["--resume"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    states = [s["state"] for s in rec["shots"]]
    assert "released_provider_rejection" in states and "verified" in states, states
    print("T5 PASS: provider rejection evidence releases reservation")



# T6: exception AFTER server accepted (balance moved) - unknown outcome, must halt, never release
with tempfile.TemporaryDirectory() as tmp:
    stub = StubNet(); make_env(tmp, "t6", stub)
    stub.crash_mode = "after_accept"
    code = run_main(GO)
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code != 0 and stub.posts == 1
    assert rec["shots"][-1]["state"] == "post_exception" and rec["shots"][-1].get("evidence") == "unknown_transport"
    posts_before = stub.posts
    code2 = run_main(GO + ["--resume"])
    rec2 = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code2 != 0 and stub.posts == posts_before, "must halt without resubmitting"
    assert "UNKNOWN TRANSPORT OUTCOME" in str(rec2.get("stopped", "")), rec2.get("stopped")
    print("T6 PASS: post-accept transport exception halts, no release, no resubmit")

# T7: resume with state=submitted polls the known job; never re-POSTs
import time as _time
_orig_sleep = _time.sleep
_time.sleep = lambda s: None
with tempfile.TemporaryDirectory() as tmp:
    stub = StubNet(); make_env(tmp, "t7", stub)
    receipts = {"manifest_total": 28896, "approval_ref": "[private-record-reference]", "started": "",
                "charged_total": 768, "stopped": None,
                "shots": [{"ep": "e01", "shot": 3, "charged": 768, "state": "submitted", "job": "job-live-1"}]}
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    run_main(GO + ["--resume"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    s3 = [s for s in rec["shots"] if s["shot"] == 3][0]
    assert stub.posts == 0, "resume must never re-POST a submitted job"
    assert s3["state"] == "verified", s3["state"]
    assert rec["charged_total"] == 768
    print("T7 PASS: resume polls known submitted job, zero new POSTs, verify runs")
_time.sleep = _orig_sleep


# T8: ref-mention validator catches a missing @-mention for any attached ref
from production_prompts import missing_mentions, MANIFEST as PM
all_ok = all(not missing_mentions(s) for s in PM["shots"])
assert all_ok, "production manifest itself must pass mention validation"
probe = dict(PM["shots"][2])  # e01 s03, two-body
import production_prompts as pp
_orig = pp.prompt_for
pp.prompt_for = lambda s: _orig(s).replace("@two_shot_dialogue", "two_shot_dialogue").replace("@yule_ball_location", "the ballroom")
try:
    miss = missing_mentions(probe)
finally:
    pp.prompt_for = _orig
assert "two_shot_dialogue" in miss and "yule_ball_location" in miss, miss
print("T8 PASS: mention validator flags missing @two_shot/@location; manifest passes")


# T9: accepted-audio hash drift halts before any POST
with tempfile.TemporaryDirectory() as tmp:
    stub = StubNet(); make_env(tmp, "t9", stub)
    pr._audio_lock = lambda: {"e01-l02-draconia.mp3": "wrong-hash"}
    code = run_main(GO)
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code != 0 and stub.posts == 0
    assert "audio drifted" in str(rec.get("stopped", "")), rec.get("stopped")
    print("T9 PASS: accepted-audio hash drift halts before any POST")

print("ALL FAULT TESTS PASS")

# ---- staged pipeline artifact gating (T10-T13) ----
import stages as STAGES
def cap_for(ep, n):
    s = [x for x in pr.MANIFEST["shots"] if x["episode"]==ep and x["shot"]==n][0]
    if s.get("beats"):
        return sum(STAGES.next_gen_s(b["dur_s"]) * 96 for b in s["beats"])
    return STAGES.next_gen_s(s["billing_s"]) * 96
CAP_E01S03 = cap_for("e01", 3)  # provider whole-second generation: 3.9->4, 0.6->2, 3.5->4 = 10s = 960

def make_stage_env(tmp, tag):
    pr.RUN_DIR = Path(tmp) / tag; pr.RUN_DIR.mkdir(parents=True, exist_ok=True)
    pr.POLL_SLEEP = 0
    pr.subprocess.run = REAL_RUN  # undo any network-stub pollution of the shared subprocess module
    pr._audio_lock = REAL_AUDIO_LOCK  # undo make_env's lock stub; stage tests exercise the real lock
    rec = {"shots": [], "charged_total": 0}
    (pr.RUN_DIR / "run-receipts.json").read_text() if False else None
    return rec


def record_s03_frames(receipts, state, tmp_run, acceptance=True):
    """s03 now has 3 beats; the video stage requires a per-beat frames artifact."""
    for b in (1, 2, 3):
        f = Path(tmp_run) / ("e01-s03-b%d-start.png" % b)
        f.write_bytes(b"frame-bytes-b%d" % b)
        STAGES.record_artifact(receipts, "e01", 3, "frames", f, state, beat=b,
                               acceptance_ref="[private-record-reference]" if acceptance else None)

with tempfile.TemporaryDirectory() as tmp:  # T10: video stage refuses without accepted frame
    make_stage_env(tmp, "t10")
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "blocked" in rec.get("stopped", ""), rec.get("stopped")
    print("T10 PASS: video stage blocked without recorded frames artifact")

with tempfile.TemporaryDirectory() as tmp:  # T11: generated-but-unaccepted frame still blocks
    make_stage_env(tmp, "t11")
    receipts = {"shots": [], "charged_total": 0}
    record_s03_frames(receipts, "frame_generated", pr.RUN_DIR, acceptance=False)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "frame_generated" in rec.get("stopped", ""), rec.get("stopped")
    print("T11 PASS: unaccepted frame blocks video stage")

with tempfile.TemporaryDirectory() as tmp:  # T12: drifted accepted frame blocks
    make_stage_env(tmp, "t12")
    receipts = {"shots": [], "charged_total": 0}
    record_s03_frames(receipts, "frame_accepted", pr.RUN_DIR)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    (pr.RUN_DIR / "e01-s03-b1-start.png").write_bytes(b"TAMPERED")
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "drifted" in rec.get("stopped", ""), rec.get("stopped")
    print("T12 PASS: hash drift on accepted frame blocks video stage")

with tempfile.TemporaryDirectory() as tmp:  # T13: unimplemented stage refuses to propagate
    make_stage_env(tmp, "t13")
    code = run_main(["--stage", "colorgrade", "--approved-cap", "0", "--approval-ref", "[private-record-reference]"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "not implemented" in rec.get("stopped", ""), rec.get("stopped")
    print("T13 PASS: unimplemented stage refuses instead of silently skipping")

with tempfile.TemporaryDirectory() as tmp:  # T14: bare entrypoint stops with migration guidance, zero POSTs
    stub = StubNet(); make_env(tmp, "t14", stub)
    code = run_main([])
    assert code == 2 and stub.posts == 0
    print("T14 PASS: bare entrypoint stops with staged-pipeline guidance, no legacy fallback")

with tempfile.TemporaryDirectory() as tmp:  # T15: assemble muxes accepted audio onto verified video artifact
    make_stage_env(tmp, "t15")
    vid = pr.RUN_DIR / "e01-s04.mp4"
    r = REAL_RUN(["ffmpeg","-y","-v","error","-f","lavfi","-i","testsrc=duration=2:size=320x240:rate=30",
                        "-f","lavfi","-i","sine=frequency=440:duration=2","-c:v","libx264","-pix_fmt","yuv420p",str(vid)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-200:]
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 4, "video", vid, "video_verified", job="stub")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    pr.subprocess.run = REAL_RUN
    code = run_main(["--stage", "assemble", "--only", "e01:4"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    art = rec.get("stage_shots", {}).get("e01:4", {}).get("assemble", {})
    assert art.get("state") == "assembled", rec.get("stopped", art)
    out = Path(art["artifact"])
    probe = REAL_RUN(["ffprobe","-v","error","-show_entries","stream=codec_type","-of","csv=p=0",str(out)],
                           capture_output=True, text=True).stdout
    assert "audio" in probe and "video" in probe, probe
    print("T15 PASS: assemble muxes accepted audio onto verified video, artifact recorded")

# --- eye-test lip-sync decision rules ---
import importlib
stages_mod = importlib.import_module("examples.r2v.stages") if False else None
sys.path.insert(0, str(Path(__file__).parent))
import stages as st

s_cu = {"line": "Stay behind me.", "dialogue_on_screen": True, "framing_class": "cu_dialogue"}
s_wide = {"line": "Away from the entrance. Now.", "dialogue_on_screen": True, "framing_class": "wide_action"}
s_vo = {"line": "Away from the entrance. Now.", "dialogue_on_screen": False, "framing_class": "insert"}
s_silent = {"line": None, "dialogue_on_screen": False, "framing_class": "wide_action"}

p1 = st.lipsync_plan(s_cu)
assert p1["mode"] == "lipsync" and p1["needs_verdict"], p1
print("T16 PASS: cu_dialogue defaults to lipsync but still demands a real face verdict")

p2 = st.lipsync_plan(s_cu, face_verdict="not_readable")
assert p2["mode"] == "soundtrack" and not p2["needs_verdict"], p2
p3 = st.lipsync_plan(s_wide, face_verdict="readable")
assert p3["mode"] == "lipsync", p3
print("T17 PASS: actual-video face verdict overrides framing_class both directions")

assert st.lipsync_plan(s_vo)["mode"] == "soundtrack"
assert st.lipsync_plan(s_vo, face_verdict="readable")["mode"] == "soundtrack"
assert st.lipsync_plan(s_silent)["mode"] == "soundtrack"
p4 = st.lipsync_plan(s_wide)
assert p4["mode"] == "soundtrack" and p4["needs_verdict"], p4
print("T18 PASS: offscreen/voiceover and silent shots never lip-sync; wide default is soundtrack pending verdict")

# --- camera + framing wiring (eye-test implementation) ---
import production_prompts as pp

shot_cu = {"episode": "e01", "shot": 2, "action": "Draconia answers.", "two_body": False,
           "speaker": "draconia", "line": "Careful.", "audio": "e01-s02.mp3",
           "framing_class": "cu_dialogue", "refs": []}
pr.SCENES = getattr(pp, "SCENES")
out = pp.prompt_for(shot_cu)
assert "mouth clearly visible" in out and "Static locked camera" in out, out
print("T19 PASS: cu_dialogue framing note + default static camera in prompt")

shot_rev = dict(shot_cu, camera="slow_push_in", reveal=True, framing_class="reaction_cu", line=None, speaker=None)
out2 = pp.prompt_for(shot_rev)
assert "Slow steady push-in" in out2 and "Static locked camera" not in out2 and "reaction" in out2.lower(), out2
print("T20 PASS: declared reveal shot gets slow push-in, not camera lock")

import stages as st2
w = st2.validate_manifest([
    {"episode": "e01", "shot": 9, "line": "Run.", "dialogue_on_screen": True, "framing_class": "wide_action"},
    {"episode": "e01", "shot": 10, "line": "Now.", "dialogue_on_screen": None, "framing_class": "cu_dialogue"},
    {"episode": "e01", "shot": 11, "line": None, "dialogue_on_screen": False, "framing_class": "wide_action", "camera": "orbit"},
    {"episode": "e01", "shot": 12, "line": None, "dialogue_on_screen": False, "framing_class": "reaction_cu", "camera": "slow_push_in"},
])
assert len(w) == 4, w
print("T21 PASS: planner warnings fire on wide on-screen dialogue, missing flag, unknown camera, push-in without reveal")

w2 = st2.validate_manifest([
    {"episode": "e01", "shot": 1, "line": "Careful.", "dialogue_on_screen": True, "framing_class": "cu_dialogue"},
    {"episode": "e01", "shot": 2, "line": None, "dialogue_on_screen": False, "framing_class": "wide_action"},
])
assert w2 == [], w2
print("T22 PASS: clean manifest produces no warnings")

def synth_clip(path, secs=2, audio=False):
    cmd = ["ffmpeg","-y","-v","error","-f","lavfi","-i","testsrc=duration=%d:size=320x240:rate=30" % secs]
    if audio:
        cmd += ["-f","lavfi","-i","sine=frequency=440:duration=%d" % secs,"-c:a","aac","-shortest"]
    cmd += [str(path)]
    r = REAL_RUN(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-200:]

with tempfile.TemporaryDirectory() as tmp:  # T23: dialogue shot without face verdict stops, sheet produced
    make_stage_env(tmp, "t23")
    vid = pr.RUN_DIR / "e01-s02-assembled.mp4"; synth_clip(vid)
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 2, "assemble", vid, "assembled")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "lipsync", "--only", "e01:2"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "face verdict REQUIRED" in rec.get("stopped", ""), rec.get("stopped")
    assert (pr.RUN_DIR / "e01-s02-facecheck.png").exists()
    print("T23 PASS: dialogue shot without face verdict stops with sheet path, no paid call")

with tempfile.TemporaryDirectory() as tmp:  # T24: not_readable verdict -> soundtrack pass-through, no cap needed
    make_stage_env(tmp, "t24")
    vid = pr.RUN_DIR / "e01-s02-assembled.mp4"; synth_clip(vid)
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 2, "assemble", vid, "assembled")
    receipts["stage_shots"]["e01:2"]["face_verdict"] = "not_readable"
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "lipsync", "--only", "e01:2"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    art = STAGES.get_artifact(rec, "e01", 2, "lipsync")
    assert code == 2 and art and art["state"] == "lipsync_done" and art["mode"] == "soundtrack", (code, art)
    print("T24 PASS: not_readable verdict -> soundtrack pass-through, approved audio kept, zero credits")

with tempfile.TemporaryDirectory() as tmp:  # T25: readable verdict still needs exact cap + wamid before any POST
    stub = StubNet(); make_env(tmp, "t25", stub); pr.RUN_DIR = Path(tmp) / "t25"
    pr.subprocess.run = REAL_RUN  # two-pass validates (real facecheck) before the cap refusal
    vid = pr.RUN_DIR / "e01-s02-assembled.mp4"; synth_clip(vid)
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 2, "assemble", vid, "assembled")
    receipts["stage_shots"]["e01:2"]["face_verdict"] = "readable"
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    s02 = [s for s in pr.MANIFEST["shots"] if s["episode"]=="e01" and s["shot"]==2][0]
    code = run_main(["--stage", "lipsync", "--only", "e01:2"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    wins = pr._dialogue_windows(s02)
    expect = sum(int(-(-(w1 - w0) * 30 // 1)) for w0, w1 in wins)
    assert wins == [[0.0, 4.7]], wins  # beats: word-boundary-aligned single carrier window
    assert code == 2 and ("--approved-cap %d" % expect) in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0
    print("T25 PASS: readable verdict requires exact per-frame cap + wamid before any lip-sync POST")

with tempfile.TemporaryDirectory() as tmp:  # T26: edit concatenates lipsync_done clips in order; blocked when one missing
    make_stage_env(tmp, "t26")
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t9","shot":2,"shot_s":2,"billing_s":2,"line":None,"dialogue_on_screen":False,"framing_class":"wide_action"},
        {"episode":"t9","shot":1,"shot_s":2,"billing_s":2,"line":None,"dialogue_on_screen":False,"framing_class":"insert"}]}
    receipts = {"shots": [], "charged_total": 0}
    for n in (1, 2):
        v = pr.RUN_DIR / ("t9-s%02d.mp4" % n); synth_clip(v, secs=2, audio=True)
        STAGES.record_artifact(receipts, "t9", n, "lipsync", v, "lipsync_done", mode="soundtrack")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "edit"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    out = pr.RUN_DIR / "t9-edited.mp4"
    assert code == 2 and out.exists(), rec.get("stopped")
    probe = REAL_RUN(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(out)], capture_output=True, text=True)
    assert abs(float(probe.stdout.strip()) - 4.0) < 0.5, probe.stdout
    assert STAGES.get_artifact(rec, "t9", 0, "edit")["state"] == "edited"
    pr.MANIFEST = orig
    print("T26 PASS: edit concatenates lipsync_done clips in shot order, episode artifact recorded")

with tempfile.TemporaryDirectory() as tmp:  # T27: ambiguous verdict stays unresolved, never silently passes
    make_stage_env(tmp, "t27")
    vid = pr.RUN_DIR / "e01-s02-assembled.mp4"; synth_clip(vid)
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 2, "assemble", vid, "assembled")
    receipts["stage_shots"]["e01:2"]["face_verdict"] = "ambiguous"
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "lipsync", "--only", "e01:2"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "UNRESOLVED" in rec.get("stopped", ""), rec.get("stopped")
    assert STAGES.get_artifact(rec, "e01", 2, "lipsync") is None
    print("T27 PASS: ambiguous verdict blocks both modes; wide-vs-close ambiguity never silently passes")

with tempfile.TemporaryDirectory() as tmp:  # T28: bad beat split hard-stops before any cap/POST
    stub = StubNet(); make_env(tmp, "t28", stub); pr.RUN_DIR = Path(tmp) / "t28"
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t7","shot":1,"shot_s":5,"billing_s":5,"line":"Hi.","audio":"x.mp3","dialogue_on_screen":True,
         "framing_class":"cu_dialogue",
         "beats":[{"id":1,"dur_s":2,"carries_line":True,"framing_class":"cu_dialogue","frame":{"refs":[],"prompt":"a"}},
                  {"id":2,"dur_s":2,"carries_line":False,"framing_class":"insert","frame":{"refs":[],"prompt":"b"}}]}]}
    code = run_main(["--stage", "frames", "--approved-cap", "100", "--approval-ref", "[private-record-reference]"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    pr.MANIFEST = orig
    assert code == 2 and "preserve approved timing" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0
    print("T28 PASS: beat durations not summing to approved shot length hard-stops before any paid call")

def beat_env(tmp, tag):
    """2-shot episode t8: s1 beat-split dialogue (2+2=4s), s2 wordless wide 2s."""
    make_stage_env(tmp, tag)
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t8","shot":1,"shot_s":9,"billing_s":9,"line":"Stay.","audio":"e01-l01-draconia.mp3",
         "speaker":"draconia","dialogue_on_screen":True,"framing_class":"cu_dialogue",
         "beats":[{"id":1,"dur_s":5,"carries_line":True,"framing_class":"cu_dialogue","action":"a"},
                  {"id":2,"dur_s":4,"carries_line":False,"framing_class":"insert","action":"b"}]},
        {"episode":"t8","shot":2,"shot_s":2,"billing_s":2,"line":None,"audio":None,
         "dialogue_on_screen":False,"framing_class":"wide_action"}]}
    receipts = {"shots": [], "charged_total": 0}
    for n, bt, secs in ((1, 1, 5), (1, 2, 4), (2, None, 2)):
        v = pr.RUN_DIR / ("t8-s%02d%s.mp4" % (n, "" if bt is None else "-b%d" % bt))
        synth_clip(v, secs=secs)
        STAGES.record_artifact(receipts, "t8", n, "video", v, "video_verified",
                               beat=bt, job="stub")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    return orig

def probe_streams(path):
    return REAL_RUN(["ffprobe","-v","error","-show_entries","stream=codec_type","-of","csv=p=0",str(path)],
                    capture_output=True, text=True).stdout

def probe_dur(path):
    return float(REAL_RUN(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)],
                          capture_output=True, text=True).stdout.strip())

with tempfile.TemporaryDirectory() as tmp:  # T29: beat merge -> one shot clip, approved audio muxed once, duration preserved
    orig = beat_env(tmp, "t29")
    code = run_main(["--stage", "assemble", "--only", "t8:1"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    art = STAGES.get_artifact(rec, "t8", 1, "assemble")
    assert code == 2 and art and art["state"] == "assembled" and art.get("mode") == "mux", (code, rec.get("stopped"))
    out = Path(art["artifact"])
    assert abs(probe_dur(out) - 9.0) < 0.5, probe_dur(out)  # video length kept, not truncated to the 8.67s audio
    assert "audio" in probe_streams(out), probe_streams(out)
    assert art.get("audio_sha256") == STAGES.sha256_file(pr.AUDIO_DIR / "e01-l01-draconia.mp3")
    pr.MANIFEST = orig
    print("T29 PASS: beat videos merge to one 9s shot clip, approved audio muxed once, hash recorded, no -shortest truncation")

with tempfile.TemporaryDirectory() as tmp:  # T30: wordless shot passthrough carries uniform silent track
    orig = beat_env(tmp, "t30")
    code = run_main(["--stage", "assemble", "--only", "t8:2"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    art = STAGES.get_artifact(rec, "t8", 2, "assemble")
    assert code == 2 and art and art.get("mode") == "passthrough", (code, rec.get("stopped"))
    assert "audio" in probe_streams(art["artifact"]), probe_streams(art["artifact"])
    pr.MANIFEST = orig
    print("T30 PASS: wordless passthrough has a uniform silent audio track (concat-safe)")

with tempfile.TemporaryDirectory() as tmp:  # T31: free end-to-end fixture assemble->lipsync->edit, timing + audio integrity
    orig = beat_env(tmp, "t31")
    code = run_main(["--stage", "assemble"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "assemble stage batch done" in rec.get("stopped", ""), rec.get("stopped")
    code = run_main(["--face-verdict", "t8:1=not_readable", "--approval-ref", "main:t31-verdict"])
    assert code == 0
    code = run_main(["--stage", "lipsync"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "lipsync stage batch done" in rec.get("stopped", ""), rec.get("stopped")
    code = run_main(["--stage", "edit"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "edit stage batch done" in rec.get("stopped", ""), rec.get("stopped")
    out = pr.RUN_DIR / "t8-edited.mp4"
    assert out.exists() and abs(probe_dur(out) - 11.0) < 0.6, probe_dur(out)
    assert "audio" in probe_streams(out)
    assert rec.get("charged_total", 0) == 0
    pr.MANIFEST = orig
    print("T31 PASS: free end-to-end fixture assemble->lipsync->edit, 11s episode, audio intact, zero credits")

with tempfile.TemporaryManifest if False else tempfile.TemporaryDirectory() as tmp:  # T32: frames wiring selects real manifest frame specs, nonzero
    stub = StubNet(); make_env(tmp, "t32", stub); pr.RUN_DIR = Path(tmp) / "t32"
    code = run_main(["--stage", "frames"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    frame_specs = 0
    for s in pr.MANIFEST["shots"]:
        if s.get("beats"):
            frame_specs += sum(1 for b in s["beats"] if b.get("frame"))
        elif s.get("frame"):
            frame_specs += 1
    expect = 50 * frame_specs  # one paid attempt per declared frame spec
    assert code == 2 and ("--approved-cap %d" % expect) in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0
    print("T32 PASS: frames stage wires nonzero manifest frame specs (s01, s03, s02 x3 beats) into an exact cap demand")

with tempfile.TemporaryDirectory() as tmp:  # T33: readable-window splice preserves timeline + exact approved audio
    make_stage_env(tmp, "t33")
    # assembled 4s shot: grey video + approved 440Hz audio
    asm = pr.RUN_DIR / "t6-s01-assembled.mp4"
    r = REAL_RUN(["ffmpeg","-y","-v","error","-f","lavfi","-i","color=gray:duration=4:size=320x240:rate=30",
                  "-f","lavfi","-i","sine=frequency=440:duration=4","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(asm)],
                 capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-200:]
    # provider returns ONLY the 1-3s window clip (red, 2s)
    seg = pr.RUN_DIR / "t6-s01-window.mp4"
    r = REAL_RUN(["ffmpeg","-y","-v","error","-f","lavfi","-i","color=red:duration=2:size=320x240:rate=30",
                  "-f","lavfi","-i","sine=frequency=440:duration=2","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(seg)],
                 capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-200:]
    out = pr.RUN_DIR / "t6-s01-lipsynced.mp4"
    receipts = {"shots": [], "charged_total": 0}
    pr._splice_window(str(asm), str(seg), 1.0, 3.0, str(out), receipts)
    assert abs(probe_dur(out) - 4.0) < 0.35, probe_dur(out)
    assert "audio" in probe_streams(out), probe_streams(out)
    # audio must be the assembled file's exact stream: extract and compare content hash
    aout = pr.RUN_DIR / "a.aac"; ain = pr.RUN_DIR / "a-in.aac"
    REAL_RUN(["ffmpeg","-y","-v","error","-i",str(out),"-map","0:a:0","-c","copy",str(aout)], capture_output=True)
    REAL_RUN(["ffmpeg","-y","-v","error","-i",str(asm),"-map","0:a:0","-c","copy",str(ain)], capture_output=True)
    import hashlib as _hl
    assert _hl.sha256(aout.read_bytes()).hexdigest() == _hl.sha256(ain.read_bytes()).hexdigest()
    # middle frame must come from the red segment, first frame from grey assembled
    f_mid = pr.RUN_DIR / "mid.png"; f_pre = pr.RUN_DIR / "pre.png"
    REAL_RUN(["ffmpeg","-y","-v","error","-ss","2.0","-i",str(out),"-frames:v","1",str(f_mid)], capture_output=True)
    REAL_RUN(["ffmpeg","-y","-v","error","-ss","0.2","-i",str(out),"-frames:v","1",str(f_pre)], capture_output=True)
    from PIL import Image
    pm = Image.open(str(f_mid)).convert("RGB").getpixel((160,120))
    pp = Image.open(str(f_pre)).convert("RGB").getpixel((160,120))
    assert pm[0] > 150 and pm[1] < 100, pm   # red window
    assert abs(pp[0]-pp[1]) < 15 and abs(pp[1]-pp[2]) < 15, pp  # grey pre-window
    print("T33 PASS: window splice preserves 4s timeline, exact approved audio bytes, window frames only inside 1-3s")

with tempfile.TemporaryDirectory() as tmp:  # T35: audio longer than approved shot stops, never silently truncated
    make_stage_env(tmp, "t35")
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t4","shot":1,"shot_s":4,"billing_s":4,"line":"Stay.","audio":"e01-l01-draconia.mp3",
         "speaker":"draconia","dialogue_on_screen":True,"framing_class":"cu_dialogue"}]}
    v = pr.RUN_DIR / "t4-s01.mp4"; synth_clip(v, secs=4)
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "t4", 1, "video", v, "video_verified", job="stub")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "assemble", "--only", "t4:1"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    pr.MANIFEST = orig
    assert code == 2 and "exceeds approved shot length" in rec.get("stopped", ""), rec.get("stopped")
    assert STAGES.get_artifact(rec, "t4", 1, "assemble") is None
    print("T35 PASS: 8.67s approved audio on a 4s shot hard-stops instead of truncating audio or shot")

with tempfile.TemporaryDirectory() as tmp:  # T36: two-pass lipsync validates whole batch before ANY paid POST
    stub = StubNet(); make_env(tmp, "t36", stub); pr.RUN_DIR = Path(tmp) / "t36"
    pr.subprocess.run = REAL_RUN  # pre-pass generates real facecheck sheets before the stop
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t5","shot":1,"shot_s":2,"billing_s":2,"line":"A.","audio":"e01-l01-draconia.mp3","speaker":"d","dialogue_on_screen":True,"framing_class":"cu_dialogue"},
        {"episode":"t5","shot":2,"shot_s":2,"billing_s":2,"line":"B.","audio":"e01-l01-draconia.mp3","speaker":"d","dialogue_on_screen":True,"framing_class":"cu_dialogue"}]}
    receipts = {"shots": [], "charged_total": 0}
    for n in (1, 2):
        v = pr.RUN_DIR / ("t5-s%02d-assembled.mp4" % n); synth_clip(v, secs=2)
        STAGES.record_artifact(receipts, "t5", n, "assemble", v, "assembled")
    receipts["stage_shots"]["t5:1"]["face_verdict"] = "readable"  # paid-eligible shot comes FIRST
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "lipsync", "--approved-cap", "60", "--approval-ref", "[private-record-reference]"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    pr.MANIFEST = orig
    assert code == 2 and "face verdict REQUIRED" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0, stub.posts
    print("T36 PASS: batch with a paid-eligible shot first still stops pre-POST on the unverdicted shot")

with tempfile.TemporaryDirectory() as tmp:  # T37: resume idempotency - intact downstream artifacts skip, zero re-POST
    stub = StubNet(); make_env(tmp, "t37", stub); pr.RUN_DIR = Path(tmp) / "t37"
    cap4 = cap_for("e01", 4)
    v = pr.RUN_DIR / "e01-s04.mp4"; synth_clip(v, secs=2)
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 4, "video", v, "video_verified", job="old-job")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "video", "--approved-cap", str(cap4), "--approval-ref", "[private-record-reference]", "--only", "e01:4"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert stub.posts == 0, stub.posts
    print("T37 PASS: rerun of video stage skips hash-intact video_verified unit, zero duplicate POSTs")

with tempfile.TemporaryDirectory() as tmp:  # T38: audio outside the accepted lock hard-stops assemble
    make_stage_env(tmp, "t38")
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t3","shot":1,"shot_s":4,"billing_s":4,"line":"X.","audio":"not-in-lock.mp3",
         "speaker":"d","dialogue_on_screen":True,"framing_class":"cu_dialogue"}]}
    v = pr.RUN_DIR / "t3-s01.mp4"; synth_clip(v, secs=4)
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "t3", 1, "video", v, "video_verified", job="stub")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "assemble", "--only", "t3:1"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    pr.MANIFEST = orig
    assert code == 2 and "not in the accepted-audio lock" in rec.get("stopped", ""), rec.get("stopped")
    print("T38 PASS: audio with no recorded acceptance in the lock hard-stops assemble")

class I2VStub(StubNet):
    """StubNet that also serves the staged i2v endpoint with an exact-charge response."""
    def post(self, url, headers=None, json=None, timeout=None):
        if url.endswith("/v1/image-to-video"):
            self.posts += 1
            charge = int(json["end_seconds"] * 96)
            self.bal -= charge
            return StubResp(200, {"id": "job-i2v-%d" % self.posts, "credits_charged": charge})
        return super().post(url, headers=headers, json=json, timeout=timeout)

with tempfile.TemporaryDirectory() as tmp:  # T39: provider mid-poll failure stops, no blind rerun, ledger records
    class PollErr(I2VStub):
        def get(self, url, headers=None, timeout=None):
            if "/v1/video-projects/" in url:
                return StubResp(200, {"id": "j", "status": "error"})
            return super().get(url, headers=headers, timeout=timeout)
    stub = PollErr(); make_env(tmp, "t39", stub); pr.RUN_DIR = Path(tmp) / "t39"
    receipts = {"shots": [], "charged_total": 0}
    record_s03_frames(receipts, "frame_accepted", pr.RUN_DIR)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "error" in rec.get("stopped", "").lower(), rec.get("stopped")
    assert stub.posts == 1, (stub.posts, rec.get("stopped"))  # exactly one submit POST, NO rerun (upload-urls POSTs not counted)
    assert not STAGES.get_artifact(rec, "e01", 3, "video"), "no artifact may be recorded for a failed job"
    print("T39 PASS: provider mid-poll failure stops with no blind rerun and no artifact recorded")

with tempfile.TemporaryDirectory() as tmp:  # T40: stale face verdict (video changed since inspection) is not reused
    make_stage_env(tmp, "t40")
    vid = pr.RUN_DIR / "e01-s02-assembled.mp4"; synth_clip(vid)
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 2, "assemble", vid, "assembled")
    receipts["stage_shots"]["e01:2"]["face_verdict"] = "readable"
    receipts["stage_shots"]["e01:2"]["face_verdict_for_sha256"] = "old-hash"
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "lipsync", "--only", "e01:2"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "face verdict REQUIRED" in rec.get("stopped", ""), rec.get("stopped")
    print("T40 PASS: verdict bound to a different video hash is stale and blocks like no verdict")

with tempfile.TemporaryDirectory() as tmp:  # T41: video skip invalidates when the upstream accepted frame changed
    stub = I2VStub(); make_env(tmp, "t41", stub); pr.RUN_DIR = Path(tmp) / "t41"
    v = pr.RUN_DIR / "e01-s03-b1.mp4"; synth_clip(v, secs=2)
    receipts = {"shots": [], "charged_total": 0}
    record_s03_frames(receipts, "frame_accepted", pr.RUN_DIR)
    STAGES.record_artifact(receipts, "e01", 3, "video", v, "video_verified", beat=1, job="old", upstream_sha256="old-frame-hash")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "does not cover regeneration" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0, stub.posts  # drift demands FRESH approval; historical ref never auto-spends
    print("T41 PASS: changed upstream frame invalidates the completed unit and demands fresh approval, zero POSTs")

with tempfile.TemporaryDirectory() as tmp:  # T42: unknown prior submission outcome blocks blind re-POST
    stub = StubNet(); make_env(tmp, "t42", stub); pr.RUN_DIR = Path(tmp) / "t42"
    receipts = {"shots": [{"ep": "e01", "shot": 3, "beat": 1, "stage": "video",
                           "state": "post_exception", "error": "connection reset", "intended": 480}],
                "charged_total": 0}
    record_s03_frames(receipts, "frame_accepted", pr.RUN_DIR)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "UNKNOWN SUBMISSION OUTCOME" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0, stub.posts
    print("T42 PASS: prior reserved/post_exception entry without job id blocks blind re-submission")

with tempfile.TemporaryDirectory() as tmp:  # T43: beat boundary off the 30fps frame grid hard-stops
    stub = StubNet(); make_env(tmp, "t43", stub); pr.RUN_DIR = Path(tmp) / "t43"
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t2","shot":1,"shot_s":5,"billing_s":5,"line":"Hi.","audio":"x.mp3","dialogue_on_screen":True,
         "framing_class":"cu_dialogue",
         "beats":[{"id":1,"dur_s":4.73,"carries_line":True,"framing_class":"cu_dialogue","frame":{"refs":[],"prompt":"a"}},
                  {"id":2,"dur_s":0.27,"carries_line":False,"framing_class":"insert","frame":{"refs":[],"prompt":"b"}}]}]}
    code = run_main(["--stage", "frames", "--approved-cap", "100", "--approval-ref", "[private-record-reference]"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    pr.MANIFEST = orig
    assert code == 2 and "frame grid" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0
    print("T43 PASS: beat durations off the 30fps frame grid hard-stop before any paid call")

with tempfile.TemporaryDirectory() as tmp:  # T44: multi-carrier beats - two readable-face beats get two lip windows
    shot = {"episode":"t9","shot":1,"shot_s":8,"billing_s":8,"line":"Two halves.","audio":"x.mp3",
            "speaker":"d","dialogue_on_screen":True,"framing_class":"two_shot_dialogue",
            "beats":[{"id":1,"dur_s":3.5,"carries_line":True,"framing_class":"two_shot_dialogue"},
                     {"id":2,"dur_s":1.0,"carries_line":False,"framing_class":"insert"},
                     {"id":3,"dur_s":3.5,"carries_line":True,"framing_class":"cu_dialogue"}]}
    assert STAGES.validate_beats(shot) is None, STAGES.validate_beats(shot)
    wins = pr._dialogue_windows(shot)
    assert wins == [[0.0, 3.5], [4.5, 8.0]], wins
    total = sum(int(-(-(w1 - w0) * 30 // 1)) for w0, w1 in wins)
    assert total == 105 + 105, total
    print("T44 PASS: multi-carrier beat shot yields one lip window per carrier, quote sums both")

with tempfile.TemporaryDirectory() as tmp:  # T45: fractional beat lengths map to provider whole-second generation caps
    assert STAGES.next_gen_s(0.6) == 2 and STAGES.next_gen_s(3.9) == 4 and STAGES.next_gen_s(4.7) == 5
    assert STAGES.next_gen_s(10) == 10 and STAGES.next_gen_s(11) == 15 and STAGES.next_gen_s(31) is None
    stub = StubNet(); make_env(tmp, "t45", stub); pr.RUN_DIR = Path(tmp) / "t45"
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t9","shot":1,"shot_s":3,"billing_s":3,"line":"Hi.","audio":"x.mp3",
         "speaker":"d","dialogue_on_screen":True,"framing_class":"cu_dialogue",
         "beats":[{"id":1,"dur_s":0.6,"carries_line":True,"framing_class":"cu_dialogue","frame":{"refs":[],"prompt":"a"}},
                  {"id":2,"dur_s":2.4,"carries_line":False,"framing_class":"insert","frame":{"refs":[],"prompt":"b"}}]}]}
    code = run_main(["--stage", "video", "--approved-cap", "288", "--approval-ref", "[private-record-reference]"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    pr.MANIFEST = orig
    # gen seconds: 0.6->2, 2.4->3 = 5s -> 480, NOT 288 (3s*96) and NOT 480-56 from truncation
    assert code == 2 and "--approved-cap 480" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0
    print("T45 PASS: fractional beats demand whole-second generation cap (2+3=5s=480), no fractional or truncated quote")

with tempfile.TemporaryDirectory() as tmp:  # T46: REAL end-to-end wiring - video(mock API, whole-s beats) -> assemble -> multi-carrier lipsync(mock windows) -> edit
    class BytesResp(StubResp):
        @property
        def content(self): return self._p if isinstance(self._p, bytes) else b""
    class E2EStub(StubNet):
        def __init__(self):
            super().__init__()
            self.submitted, self.jobs, self.clips = [], {}, {}
        def post(self, url, headers=None, json=None, timeout=None):
            if url.endswith("/v1/files/upload-urls"):
                return StubResp(200, {"items": [{"upload_url": "https://up", "file_path": "fp-x"}]})
            if url.endswith("/v1/image-to-video"):
                es = json["end_seconds"]
                assert float(es).is_integer() and es in STAGES.I2V_ALLOWED_SECONDS, ("fractional/illegal end_seconds submitted", es)
                self.posts += 1
                jid = "job-i2v-%d" % self.posts
                self.jobs[jid] = ("i2v", es)
                charge = es * 96
                self.submitted.append(("i2v", es, charge))
                self.bal -= charge
                return StubResp(200, {"id": jid, "credits_charged": charge})
            if url.endswith("/v1/lip-sync"):
                w0, w1 = json["start_seconds"], json["end_seconds"]
                frames = int(-(-(w1 - w0) * 30 // 1))
                self.posts += 1
                jid = "job-lipsync-%d" % self.posts
                self.jobs[jid] = ("lipsync", w1 - w0)
                self.submitted.append(("lipsync", [w0, w1], frames))
                self.bal -= frames
                return StubResp(200, {"id": jid, "credits_charged": frames})
            return StubResp(404, {})
        def get(self, url, headers=None, timeout=None):
            if "/v1/video-projects/" in url:
                jid = url.rsplit("/", 1)[1]
                return StubResp(200, {"id": jid, "status": "complete", "downloads": [{"url": "https://dl/%s.mp4" % jid}]})
            if url.startswith("https://dl/"):
                jid = url.rsplit("/", 1)[1][:-4]
                if jid not in self.clips:
                    kind, dur = self.jobs[jid]
                    cp = Path(pr.RUN_DIR) / ("stub-%s.mp4" % jid)
                    r = REAL_RUN(["ffmpeg","-y","-v","error","-f","lavfi","-i","testsrc=duration=%.3f:size=320x240:rate=30" % dur,
                                  "-f","lavfi","-i","sine=frequency=440:duration=%.3f" % dur,"-c:a","aac","-shortest",str(cp)],
                                 capture_output=True, text=True)
                    assert r.returncode == 0, r.stderr[-200:]
                    self.clips[jid] = cp.read_bytes()
                return BytesResp(200, self.clips[jid])
            return super().get(url, headers=headers, timeout=timeout)

    stub = E2EStub(); pr.RUN_DIR = Path(tmp) / "t46"; pr.RUN_DIR.mkdir(parents=True, exist_ok=True)
    pr.POLL_SLEEP = 0
    pr.sha256 = lambda p: "x"
    for name in pr.BANK_BY_NAME: pr.BANK_BY_NAME[name]["sha256"] = "x"
    pr.REF_FILES = {n: "/tmp/fake-%s.png" % n for n in pr.REF_FILES}
    for n, f in pr.REF_FILES.items(): Path(f).write_bytes(b"fake")
    pr.requests = stub
    pr._audio_lock = REAL_AUDIO_LOCK
    REAL = REAL_RUN
    def hybrid_run(cmd, capture_output=False, text=False):
        if len(cmd) > 1 and str(cmd[1]).endswith("verify_shot.py"):
            vdir = Path(cmd[4]); vdir.mkdir(parents=True, exist_ok=True)
            (vdir / "verify.json").write_text(json.dumps({"video": {"r_frame_rate": "30/1"},
                "envelope_correlation": 0.99, "motion": {"near_static": 0, "sampled": 240}, "audio_track": True, "asr_match": True}))
            return types.SimpleNamespace(returncode=0, stderr="")
        return REAL(cmd, capture_output=capture_output, text=text)
    pr.subprocess.run = hybrid_run
    orig = pr.MANIFEST
    import production_prompts as PP
    PP.SCENES["t9"] = "fixture scene"
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t9","shot":1,"shot_s":9,"billing_s":9,"line":"Stay with me.","audio":"e01-l01-draconia.mp3",
         "speaker":"draconia","dialogue_on_screen":True,"framing_class":"two_shot_dialogue","refs":["draconia","harry"],"two_body":True,
         "beats":[{"id":1,"dur_s":3.5,"carries_line":True,"framing_class":"two_shot_dialogue","action":"a","frame":{"refs":[],"prompt":"a"}},
                  {"id":2,"dur_s":1.0,"carries_line":False,"framing_class":"insert","action":"b","frame":{"refs":[],"prompt":"b"}},
                  {"id":3,"dur_s":4.5,"carries_line":True,"framing_class":"cu_dialogue","action":"c","frame":{"refs":[],"prompt":"c"}}]}]}
    # human-accepted frames are seeded (acceptance is a human gate by design); everything downstream runs as REAL stage invocations
    receipts = {"shots": [], "charged_total": 0}
    for b in (1, 2, 3):
        f = pr.RUN_DIR / ("t9-s01-b%d-start.png" % b); f.write_bytes(b"frame-%d" % b)
        STAGES.record_artifact(receipts, "t9", 1, "frames", f, "frame_accepted", beat=b, acceptance_ref="[private-record-reference]")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    # gen seconds: 3.5->4, 1.0->2, 4.5->5 = 11s -> 1056
    code = run_main(["--stage", "video", "--approved-cap", "1056", "--approval-ref", "[private-record-reference]", "--only", "t9:1"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "video stage batch done" in rec.get("stopped", ""), rec.get("stopped")
    i2v_subs = [x for x in stub.submitted if x[0] == "i2v"]
    assert [x[1] for x in i2v_subs] == [4, 2, 5], i2v_subs  # whole-second generation for fractional beats
    assert rec["charged_total"] == 1056, rec["charged_total"]
    # rerun skips all three intact units, zero duplicate spend
    posts_before = stub.posts
    code = run_main(["--stage", "video", "--approved-cap", "1056", "--approval-ref", "[private-record-reference]", "--only", "t9:1"])
    assert stub.posts == posts_before, "skip failed - duplicate spend"
    code = run_main(["--stage", "assemble", "--only", "t9:1"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "assemble stage batch done" in rec.get("stopped", ""), rec.get("stopped")
    art = STAGES.get_artifact(rec, "t9", 1, "assemble")
    assert abs(probe_dur(art["artifact"]) - 9.0) < 0.05, probe_dur(art["artifact"])  # exact frame-grid trim
    assert art.get("audio_sha256") == STAGES.sha256_file(pr.AUDIO_DIR / "e01-l01-draconia.mp3")
    code = run_main(["--face-verdict", "t9:1=readable", "--approval-ref", "main:t46-verdict"])
    assert code == 0
    # multi-carrier windows [0,3.5]+[4.5,9] = 8s * 30 = 240 frames
    code = run_main(["--stage", "lipsync", "--approved-cap", "240", "--approval-ref", "[private-record-reference]", "--only", "t9:1"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "lipsync stage batch done" in rec.get("stopped", ""), rec.get("stopped")
    lip_subs = [x for x in stub.submitted if x[0] == "lipsync"]
    assert [x[1] for x in lip_subs] == [[0.0, 3.5], [4.5, 9.0]], lip_subs  # BOTH carrier windows paid and submitted
    lart = STAGES.get_artifact(rec, "t9", 1, "lipsync")
    assert lart["windows"] == [[0.0, 3.5], [4.5, 9.0]] and abs(probe_dur(lart["artifact"]) - 9.0) < 0.1
    # lipsync rerun skips (config+upstream intact)
    posts_before = stub.posts
    code = run_main(["--stage", "lipsync", "--approved-cap", "240", "--approval-ref", "[private-record-reference]", "--only", "t9:1"])
    assert stub.posts == posts_before, "lipsync skip failed - duplicate spend"
    code = run_main(["--stage", "edit"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "edit stage batch done" in rec.get("stopped", ""), rec.get("stopped")
    out = pr.RUN_DIR / "t9-edited.mp4"
    assert out.exists() and abs(probe_dur(out) - 9.0) < 0.3 and "audio" in probe_streams(out)
    pr.MANIFEST = orig
    print("T46 PASS: real wiring video->assemble->lipsync->edit, whole-second gen [4,2,5], trim 9.0s exact, 2 carrier windows, skips hold, zero real network")

with tempfile.TemporaryDirectory() as tmp:  # T47: quality acceptance records the ACTUAL decision actor
    make_stage_env(tmp, "t47")
    receipts = {"shots": [], "charged_total": 0}
    f1 = pr.RUN_DIR / "e01-s02-b1-start.png"; f1.write_bytes(b"frame-t47-1")
    STAGES.record_artifact(receipts, "e01", 2, "frames", f1, "frame_generated", beat=1)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--accept-frame", "e01:2#b1", "--approval-ref", "main:handoff-msg-01M5"])
    assert code == 0
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    art = STAGES.get_artifact(rec, "e01", 2, "frames", beat=1)
    assert art["state"] == "frame_accepted" and art["acceptance_actor"] == "main", art
    assert art["acceptance_ref"] == "main:handoff-msg-01M5", art  # main's decision recorded AS main's
    f2 = pr.RUN_DIR / "e01-s02-b2-start.png"; f2.write_bytes(b"frame-t47-2")
    STAGES.record_artifact(rec, "e01", 2, "frames", f2, "frame_generated", beat=2)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(rec))
    code = run_main(["--accept-frame", "e01:2#b2", "--approval-ref", "[private-record-reference]"])
    assert code == 0
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    art = STAGES.get_artifact(rec, "e01", 2, "frames", beat=2)
    assert art["acceptance_actor"] == "user" and art["acceptance_ref"] == "[private-record-reference]", art
    f3 = pr.RUN_DIR / "e01-s02-b3-start.png"; f3.write_bytes(b"frame-t47-3")
    STAGES.record_artifact(rec, "e01", 2, "frames", f3, "frame_generated", beat=3)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(rec))
    code = run_main(["--accept-frame", "e01:2#b3", "--approval-ref", "slack:unverifiable"])
    assert code == 2
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    art = STAGES.get_artifact(rec, "e01", 2, "frames", beat=3)
    assert art["state"] == "frame_generated", art  # unverifiable source cannot accept
    code = run_main(["--face-verdict", "e01:2=readable"])  # verdict with no source refused
    assert code == 2
    code = run_main(["--face-verdict", "e01:2=readable", "--approval-ref", "main:sheet-review-01M5"])
    assert code == 0
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    ent = rec["stage_shots"]["e01:2"]
    assert ent["face_verdict"] == "readable" and ent["face_verdict_actor"] == "main", ent
    print("T47 PASS: quality decisions record actual actor (main:/wamid.); unattributed and bogus sources refused")

with tempfile.TemporaryDirectory() as tmp:  # T48: a main: quality ref carries ZERO spend authority
    stub = StubNet(); make_env(tmp, "t48", stub)
    code = run_main(["--stage", "frames", "--approved-cap", "150", "--approval-ref", "main:not-money", "--only", "e01:2"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "REFUSED" in rec.get("stopped", "") and stub.posts == 0, rec.get("stopped")
    code = run_main(["--stage", "video", "--approved-cap", "1056", "--approval-ref", "main:not-money", "--only", "e01:2"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "REFUSED" in rec.get("stopped", "") and stub.posts == 0, rec.get("stopped")
    print("T48 PASS: main: decision ref refused for frames/video spend (wamid grant still required), zero POSTs")

with tempfile.TemporaryDirectory() as tmp:  # T49: insert beats never get the two-body clause; s14 carries canonical shield/redirect/chain-hit
    import production_prompts as pp
    def unit(s, b):
        u = dict(s)
        if b: u.update(b)
        return u
    s14 = [s for s in pp.MANIFEST["shots"] if s["episode"] == "e01" and s["shot"] == 14][0]
    b1, b2 = s14["beats"]
    p1 = pp.prompt_for(unit(s14, b1)); p2 = pp.prompt_for(unit(s14, b2))
    assert "Both characters are present" not in p2, p2  # no-people insert must not demand both bodies
    assert "Both characters are present" in p1, p1      # two_shot dialogue keeps the anti-duplication clause
    assert "shield charm" in p1 and "wand still raised" in p1, p1  # canonical shield + redirect visible in b1
    assert "spell bolt strikes" in p2, p2  # chain hit is a required motion event in b2's video
    assert "bolt" not in b2["frame"]["prompt"], b2["frame"]["prompt"]  # but NOT mandated in the start frame
    assert "shimmer" in b1["frame"]["prompt"] and "wand still raised" in b1["frame"]["prompt"]  # valid start state carrying continuity
    s03 = [s for s in pp.MANIFEST["shots"] if s["episode"] == "e01" and s["shot"] == 3][0]
    p3i = pp.prompt_for(unit(s03, s03["beats"][1]))  # s03 b2 is also an insert in a two_body shot
    assert "Both characters are present" not in p3i, p3i
    print("T49 PASS: insert two-body leak fixed; s14 prompts carry shield/redirect/chain-hit; start frame vs motion event distinguished")

with tempfile.TemporaryDirectory() as tmp:  # T50: Harry wardrobe pinned against ref drift; s16 carries the canonical crash
    import production_prompts as pp
    def frames(o):
        if isinstance(o, dict):
            if 'prompt' in o and 'refs' in o: yield o
            for v in o.values(): yield from frames(v)
        elif isinstance(o, list):
            for v in o: yield from frames(v)
    harry_prompts = [f['prompt'] for f in frames(pp.MANIFEST['shots']) if 'dress robes' in f['prompt'] or 'black-haired boy' in f['prompt']]
    pinned = [p for p in harry_prompts if 'dress robes' in p]
    assert pinned and all('dark necktie' in p and 'red-lined' in p for p in pinned), pinned  # no bow-tie/necktie drift between refs
    s16 = [s for s in pp.MANIFEST['shots'] if s['episode'] == 'e01' and s['shot'] == 16][0]
    assert 'crashed chandelier' in s16['beats'][1]['frame']['prompt']  # CU aftermath background chains the crash event
    print("T50 PASS: Harry wardrobe pinned (necktie+red lining) in all %d prompts; s16 CU aftermath intact" % len(pinned))

with tempfile.TemporaryDirectory() as tmp:  # T51: s16 crash EVENT beat leads wordless; audio offset preserves canon order
    import stages as ST
    m = json.load(open('shot-manifest-wan30.json'))
    s16 = [s for s in m['shots'] if s['episode'] == 'e01' and s['shot'] == 16][0]
    b1, b2, b3 = s16['beats']
    assert [b['id'] for b in s16['beats']] == [1, 2, 3]
    assert abs(sum(b['dur_s'] for b in s16['beats']) - s16['shot_s']) < 1e-9 and s16['shot_s'] == 9.0
    assert not b1.get('carries_line') and b2.get('carries_line')  # wordless event head, line on the CU
    assert 'falls and crashes' in b1['action'] and 'applauds without sound' in b1['action']  # crash MOTION + applause, not aftermath
    assert 'mid-fall' in b1['frame']['prompt']  # start state shows the fall beginning, not a settled aftermath
    assert s16.get('audio_offset_s') == 2.0 == b1['dur_s']  # approved audio starts after the wordless head
    assert ST.validate_beats(s16) is None
    # offset validation: grid + wordless-head rule
    bad = dict(s16, beats=[dict(b) for b in s16['beats']]); bad['audio_offset_s'] = 1.23
    assert 'frame grid' in ST.validate_beats(bad)
    bad2 = dict(s16, beats=[dict(b) for b in s16['beats']]); bad2['audio_offset_s'] = 0
    assert 'audio_offset_s' in ST.validate_beats(bad2)
    # staged per-unit billing matches what stage_video demands; legacy total is shot-second billing
    import production_runner as pr
    staged = sum(sum(ST.next_gen_s(b['dur_s']) for b in s['beats']) if s.get('beats') else s['billing_s'] for s in m['shots']) * 96
    legacy = sum(s['billing_s'] for s in m['shots']) * 96
    assert m['total_cr_staged'] == staged == 29568 and m['total_cr'] == legacy == 28896
    # assemble must delay the audio by the offset rather than cut or misalign the take
    src = open('production_runner.py').read()
    assert 'adelay=%d:all=1' in src and 'audio_offset_s' in src
    print("T51 PASS: s16 crash event beat + audio offset 2.0s; staged total 29568 vs legacy 28896")

with tempfile.TemporaryDirectory() as tmp:  # T52: real ffmpeg assemble honors audio_offset_s (wordless crash head, intact delayed take)
    import importlib, subprocess as _sp
    importlib.reload(_sp)  # undo make_env's global subprocess.run patch
    pr.subprocess = _sp
    pr.RUN_DIR = Path(tmp) / "run"; pr.RUN_DIR.mkdir(parents=True)
    pr.AUDIO_DIR = Path(tmp) / "audio"; pr.AUDIO_DIR.mkdir(parents=True)
    def ff(args):
        r = _sp.run(["ffmpeg", "-y", "-v", "error"] + args, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    beats = {1: 2.0, 2: 4.4, 3: 2.6}
    for bid, dur in beats.items():
        ff(["-f", "lavfi", "-i", "testsrc=duration=%s:rate=30:size=320x240" % (dur if dur == int(dur) else int(dur) + 1),
            "-pix_fmt", "yuv420p", str(pr.RUN_DIR / ("b%d-src.mp4" % bid))])
    apath = pr.AUDIO_DIR / "e01-l15-draconia.mp3"
    ff(["-f", "lavfi", "-i", "sine=frequency=440:duration=6.0", "-ac", "2", str(apath)])
    import stages as ST
    pr._audio_lock = lambda: {"e01-l15-draconia.mp3": ST.sha256_file(apath)}
    receipts = {"started": "", "shots": [], "charged_total": 0, "stage_shots": {}}
    for bid in beats:
        receipts["stage_shots"]["e01:16#b%d" % bid] = {"video": {"state": "video_verified",
            "artifact": str(pr.RUN_DIR / ("b%d-src.mp4" % bid)), "job": None}}
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    try: pr.stage_assemble(types.SimpleNamespace(only="e01:16"))
    except SystemExit as e: assert e.code == 2  # stage batch stop() after success
    out = pr.RUN_DIR / "e01-s16-assembled.mp4"
    assert out.exists()
    dur = float(_sp.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip())
    assert abs(dur - 9.0) < 0.35, dur
    sil = _sp.run(["ffmpeg", "-i", str(out), "-af", "silencedetect=n=-45dB", "-f", "null", "-"],
                  capture_output=True, text=True).stderr
    import re as _re
    m_end = _re.search(r"silence_end: ([\d.]+)", sil)
    assert m_end and 1.7 < float(m_end.group(1)) < 2.3, sil[-400:]  # approved take intact, starting after the 2.0s wordless head
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    a = rec["stage_shots"]["e01:16"]["assemble"]
    assert a["mode"] == "mux" and a["audio"] == "e01-l15-draconia.mp3"
    print("T52 PASS: assemble offsets approved audio by 2.0s (silence_end %.2fs), merged duration %.2fs == shot_s 9.0, take intact" % (float(m_end.group(1)), dur))
