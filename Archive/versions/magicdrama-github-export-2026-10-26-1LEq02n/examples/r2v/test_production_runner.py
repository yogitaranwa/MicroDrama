"""Fault-injection tests for production_runner spend-safety. Stubbed transport; no network.
Rule under test: a reservation without a verified provider outcome ALWAYS halts;
only definitive pre-network failure or provider rejection releases it. Balance is diagnostic only."""
import json, sys, types, subprocess
REAL_RUN = subprocess.run  # capture before make_env stubs pr.subprocess.run (same module object)
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

GO = ["--legacy-t2v", "--approved-cap", "28704", "--approval-ref", "[private-record-reference]", "--only", "e01:3"]
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
    receipts = {"manifest_total": 28704, "approval_ref": "[private-record-reference]", "started": "",
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
CAP_E01S03 = [s for s in pr.MANIFEST["shots"] if s["episode"]=="e01" and s["shot"]==3][0]["billing_s"] * 96

def make_stage_env(tmp, tag):
    pr.RUN_DIR = Path(tmp) / tag; pr.RUN_DIR.mkdir(parents=True, exist_ok=True)
    pr.subprocess.run = REAL_RUN  # undo any network-stub pollution of the shared subprocess module
    rec = {"shots": [], "charged_total": 0}
    (pr.RUN_DIR / "run-receipts.json").read_text() if False else None
    return rec

with tempfile.TemporaryDirectory() as tmp:  # T10: video stage refuses without accepted frame
    make_stage_env(tmp, "t10")
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "blocked" in rec.get("stopped", ""), rec.get("stopped")
    print("T10 PASS: video stage blocked without recorded frames artifact")

with tempfile.TemporaryDirectory() as tmp:  # T11: generated-but-unaccepted frame still blocks
    make_stage_env(tmp, "t11")
    frame = pr.RUN_DIR / "e01-s03-start.png"; frame.write_bytes(b"frame-bytes")
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 3, "frames", frame, "frame_generated")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "frame_generated" in rec.get("stopped", ""), rec.get("stopped")
    print("T11 PASS: unaccepted frame blocks video stage")

with tempfile.TemporaryDirectory() as tmp:  # T12: drifted accepted frame blocks
    make_stage_env(tmp, "t12")
    frame = pr.RUN_DIR / "e01-s03-start.png"; frame.write_bytes(b"frame-bytes")
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 3, "frames", frame, "frame_accepted", acceptance_ref="[private-record-reference]")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    frame.write_bytes(b"TAMPERED")
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
    vid = pr.RUN_DIR / "e01-s03.mp4"
    r = REAL_RUN(["ffmpeg","-y","-v","error","-f","lavfi","-i","testsrc=duration=2:size=320x240:rate=30",
                        "-f","lavfi","-i","sine=frequency=440:duration=2","-c:v","libx264","-pix_fmt","yuv420p",str(vid)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-200:]
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 3, "video", vid, "video_verified", job="stub")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    pr.subprocess.run = REAL_RUN
    code = run_main(["--stage", "assemble", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    art = rec.get("stage_shots", {}).get("e01:3", {}).get("assemble", {})
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
    vid = pr.RUN_DIR / "e01-s02-assembled.mp4"; synth_clip(vid)
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "e01", 2, "assemble", vid, "assembled")
    receipts["stage_shots"]["e01:2"]["face_verdict"] = "readable"
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    s02 = [s for s in pr.MANIFEST["shots"] if s["episode"]=="e01" and s["shot"]==2][0]
    code = run_main(["--stage", "lipsync", "--only", "e01:2"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    w0, w1 = pr._dialogue_window(s02)
    expect = int(-(-(w1 - w0) * 30 // 1))
    assert (w0, w1) == (0.0, 4.0), (w0, w1)  # beats: only the carries_line beat window is paid
    assert code == 2 and ("--approved-cap %d" % expect) in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0
    print("T25 PASS: readable verdict requires exact per-frame cap + wamid before any lip-sync POST")

with tempfile.TemporaryDirectory() as tmp:  # T26: edit concatenates lipsync_done clips in order; blocked when one missing
    make_stage_env(tmp, "t26")
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t9","shot":2,"billing_s":2,"line":None,"dialogue_on_screen":False,"framing_class":"wide_action"},
        {"episode":"t9","shot":1,"billing_s":2,"line":None,"dialogue_on_screen":False,"framing_class":"insert"}]}
    receipts = {"shots": [], "charged_total": 0}
    for n in (1, 2):
        v = pr.RUN_DIR / ("t9-s%02d.mp4" % n); synth_clip(v, secs=1)
        STAGES.record_artifact(receipts, "t9", n, "lipsync", v, "lipsync_done", mode="soundtrack")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "edit"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    out = pr.RUN_DIR / "t9-edited.mp4"
    assert code == 2 and out.exists(), rec.get("stopped")
    probe = REAL_RUN(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(out)], capture_output=True, text=True)
    assert abs(float(probe.stdout.strip()) - 2.0) < 0.3, probe.stdout
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
        {"episode":"t8","shot":1,"shot_s":4,"billing_s":4,"line":"Stay.","audio":"e01-l01-draconia.mp3",
         "speaker":"draconia","dialogue_on_screen":True,"framing_class":"cu_dialogue",
         "beats":[{"id":1,"dur_s":2,"carries_line":True,"framing_class":"cu_dialogue","action":"a"},
                  {"id":2,"dur_s":2,"carries_line":False,"framing_class":"insert","action":"b"}]},
        {"episode":"t8","shot":2,"shot_s":2,"billing_s":2,"line":None,"audio":None,
         "dialogue_on_screen":False,"framing_class":"wide_action"}]}
    receipts = {"shots": [], "charged_total": 0}
    for n, bt in ((1, 1), (1, 2), (2, None)):
        v = pr.RUN_DIR / ("t8-s%02d%s.mp4" % (n, "" if bt is None else "-b%d" % bt))
        synth_clip(v, secs=2)
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
    assert abs(probe_dur(out) - 4.0) < 0.5, probe_dur(out)
    assert "audio" in probe_streams(out), probe_streams(out)
    assert art.get("audio_sha256") == STAGES.sha256_file(pr.AUDIO_DIR / "e01-l01-draconia.mp3")
    pr.MANIFEST = orig
    print("T29 PASS: beat videos merge to one 4s shot clip with the approved audio muxed once, hash recorded")

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
    code = run_main(["--face-verdict", "t8:1=not_readable"])
    assert code == 0
    code = run_main(["--stage", "lipsync"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "lipsync stage batch done" in rec.get("stopped", ""), rec.get("stopped")
    code = run_main(["--stage", "edit"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "edit stage batch done" in rec.get("stopped", ""), rec.get("stopped")
    out = pr.RUN_DIR / "t8-edited.mp4"
    assert out.exists() and abs(probe_dur(out) - 6.0) < 0.6, probe_dur(out)
    assert "audio" in probe_streams(out)
    assert rec.get("charged_total", 0) == 0
    pr.MANIFEST = orig
    print("T31 PASS: free end-to-end fixture assemble->lipsync->edit, 6s episode, audio intact, zero credits")

with tempfile.TemporaryManifest if False else tempfile.TemporaryDirectory() as tmp:  # T32: frames wiring selects real manifest frame specs, nonzero
    stub = StubNet(); make_env(tmp, "t32", stub); pr.RUN_DIR = Path(tmp) / "t32"
    code = run_main(["--stage", "frames"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    s02_units = 3  # e01 s02 has 3 beat frame specs
    expect = 50 * (2 + s02_units)  # e01 s01, s03 shot-level + s02 beats
    assert code == 2 and ("--approved-cap %d" % expect) in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0
    print("T32 PASS: frames stage wires nonzero manifest frame specs (s01, s03, s02 x3 beats) into an exact cap demand")
