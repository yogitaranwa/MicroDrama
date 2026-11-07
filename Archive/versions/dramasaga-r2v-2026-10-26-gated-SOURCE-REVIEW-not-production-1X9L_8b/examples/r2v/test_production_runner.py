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
        self.bal = balance; self.posts = 0; self.img_posts = 0; self.crash_mode = None; self.reject_once = False
    def get(self, url, headers=None, timeout=None):
        if url.endswith("/v1/account"): return StubResp(200, {"credits": self.bal})
        if "/v1/video-projects/" in url:
            return StubResp(200, {"id": "j", "status": "complete", "downloads": [{"url": "https://x/y.mp4"}]})
        if "/v1/image-projects/" in url:
            return StubResp(200, {"id": "j", "status": "complete", "downloads": [{"url": "https://up/img.png"}]})
        return StubResp(200, {}) if not url.startswith("https://api") else StubResp(404, {})
    def post(self, url, headers=None, json=None, timeout=None):
        if url.endswith("/v1/files/upload-urls"):
            return StubResp(200, {"items": [{"upload_url": "https://up", "file_path": "fp-x"}]})
        if url.endswith("/v1/ai-image-editor"):
            self.img_posts += 1
            self.bal -= 50
            return StubResp(200, {"id": "img-job-%d" % self.img_posts, "credits_charged": 50})
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

# Private-asset boundary: the take-dependent tests below need the accepted-audio takes and
# the sha256 lock, which are private working assets and are NOT in the source review ZIP.
# When they are absent (e.g. an extracted review archive), say so plainly and exit 3 =
# NOT EXECUTED. A missing-asset run is never a pass.
_LOCK_PATH = Path(__file__).resolve().parent / "production-2026-10-26" / "accepted-audio-sha256-lock.json"
if not (pr.AUDIO_DIR.exists() and any(pr.AUDIO_DIR.iterdir()) and _LOCK_PATH.exists()):
    print("NOT EXECUTED: this suite needs the private accepted-audio takes + sha256 lock "
          "(absent from the source review ZIP by design). Repo-root tests (tests/) do not "
          "need them. Exit 3 = not executed, never a fake pass.")
    sys.exit(3)

import copy as _copy
_MAN = _copy.deepcopy(pr.MANIFEST)
_s12 = next(s for s in _MAN["shots"] if s["episode"] == "e02" and s["shot"] == 12)
_s12.pop("beats", None); _s12.pop("audio_offset_s", None)  # synthetic undivided stand-in: real e02s12 is beat-subdivided now (legacy route correctly refuses beat shots)
pr.MANIFEST = _MAN

GO = ["--legacy-t2v", "--approved-cap", "28896", "--approval-ref", "[private-record-reference]", "--only", "e02:12"]  # e02s12: undivided 768cr (legacy refuses beat shots)
import tempfile

with tempfile.TemporaryDirectory() as tmp:  # T1: exactly one job then gate stop
    stub = StubNet(); make_env(tmp, "t1", stub)
    code = run_main(GO)
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 0 and stub.posts == 1 and rec["charged_total"] == 768
    assert [s for s in rec["shots"] if (s["ep"], s["shot"]) == ("e02", 12)][0]["state"] == "verified"
    print("T1 PASS: --only e02:12 = exactly one job, verified, charged 768")

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
        {"ep": "e02", "shot": 12, "state": "reserved", "intended": 768, "balance_before": 131219}]}))
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
                "shots": [{"ep": "e02", "shot": 12, "charged": 768, "state": "submitted", "job": "job-live-1"}]}
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    run_main(GO + ["--resume"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    s3 = [s for s in rec["shots"] if (s["ep"], s["shot"]) == ("e02", 12)][0]
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
    pr._audio_lock = lambda: {"e02-l11-draconia.mp3": "wrong-hash"}  # e02s12 audio (GO selects e02:12)
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
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [{"episode": "t15", "shot": 1, "shot_s": 11.0, "billing_s": 11.0,
                   "line": "After.", "audio": "e01-l01-draconia.mp3", "speaker": "draconia",
                   "dialogue_on_screen": True, "framing_class": "cu_dialogue"}]}
    vid = pr.RUN_DIR / "t15-s01.mp4"
    r = REAL_RUN(["ffmpeg","-y","-v","error","-f","lavfi","-i","testsrc=duration=2:size=320x240:rate=30",
                        "-f","lavfi","-i","sine=frequency=440:duration=2","-c:v","libx264","-pix_fmt","yuv420p",str(vid)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-200:]
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "t15", 1, "video", vid, "video_verified", job="stub")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    pr.subprocess.run = REAL_RUN
    code = run_main(["--stage", "assemble", "--only", "t15:1"])
    pr.MANIFEST = orig
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    art = rec.get("stage_shots", {}).get("t15:1", {}).get("assemble", {})
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

def stamp_fp(receipts, manifest=None):
    """Stamp hand-recorded 'assembled' fixtures with the input fingerprint the freshness
    gates require (real assembles record it themselves at --stage assemble)."""
    m = manifest or pr.MANIFEST
    by = {(s["episode"], s["shot"]): s for s in m["shots"]}
    for key, st in receipts.get("stage_shots", {}).items():
        arec = st.get("assemble")
        if arec and arec.get("state") == "assembled":
            ep, shot = key.split(":")[0], int(key.split(":")[1])
            if (ep, shot) in by:
                arec["inputs_sha256"] = pr._assemble_inputs_fp(receipts, by[(ep, shot)])


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
    stamp_fp(receipts)
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
    stamp_fp(receipts)
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
    stamp_fp(receipts)
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
        STAGES.record_artifact(receipts, "t9", n, "assemble", v, "assembled")
        STAGES.record_artifact(receipts, "t9", n, "lipsync", v, "lipsync_done", mode="soundtrack")
    stamp_fp(receipts)
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
    stamp_fp(receipts)
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
         "beats":[{"id":1,"dur_s":2,"carries_line":True,"audio_intent":"dialogue","framing_class":"cu_dialogue","frame":{"refs":[],"prompt":"a"}},
                  {"id":2,"dur_s":2,"carries_line":False,"audio_intent":"sound_fx","framing_class":"insert","frame":{"refs":[],"prompt":"b"}}]}]}
    code = run_main(["--stage", "frames", "--approved-cap", "100", "--approval-ref", "[private-record-reference]"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    pr.MANIFEST = orig
    assert code == 2 and "preserve approved timing" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0
    print("T28 PASS: beat durations not summing to approved shot length hard-stops before any paid call")

def fx_silence_seed(receipts, ep, shot, beat=None):
    """Test fixture: the attributed human decision that a sound_fx unit ships silent."""
    p = pr.RUN_DIR / ("%s-fx-silence.json" % pr._tag(ep, shot, {"id": beat} if beat else None))
    p.write_text(json.dumps({"decision": "fx_silence_accepted", "actor": "main", "ref": "main:TEST"}))
    STAGES.record_artifact(receipts, ep, shot, "fx", p, "fx_silence_accepted",
                           beat=beat, acceptance_ref="main:TEST", acceptance_actor="main")

def beat_env(tmp, tag):
    """2-shot episode t8: s1 beat-split dialogue (2+2=4s), s2 wordless wide 2s."""
    make_stage_env(tmp, tag)
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t8","shot":1,"shot_s":9,"billing_s":9,"line":"Stay.","audio":"e01-l01-draconia.mp3",
         "speaker":"draconia","dialogue_on_screen":True,"framing_class":"cu_dialogue",
         "beats":[{"id":1,"dur_s":5,"carries_line":True,"audio_intent":"dialogue","framing_class":"cu_dialogue","action":"a"},
                  {"id":2,"dur_s":4,"carries_line":False,"audio_intent":"sound_fx","framing_class":"insert","action":"b"}]},
        {"episode":"t8","shot":2,"shot_s":2,"billing_s":2,"line":None,"audio":None,
         "dialogue_on_screen":False,"framing_class":"wide_action"}]}
    receipts = {"shots": [], "charged_total": 0}
    for n, bt, secs in ((1, 1, 5), (1, 2, 4), (2, None, 2)):
        v = pr.RUN_DIR / ("t8-s%02d%s.mp4" % (n, "" if bt is None else "-b%d" % bt))
        synth_clip(v, secs=secs)
        STAGES.record_artifact(receipts, "t8", n, "video", v, "video_verified",
                               beat=bt, job="stub")
    for n, bt in ((1, 2), (2, None)):  # both sound_fx units carry an explicit silence decision
        fx_silence_seed(receipts, "t8", n, bt)
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
    stamp_fp(receipts)
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
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [{"episode": "t37", "shot": 1, "shot_s": 2.0, "billing_s": 2,
                   "line": "After.", "audio": "e01-l01-draconia.mp3", "speaker": "draconia",
                   "dialogue_on_screen": True, "framing_class": "cu_dialogue"}]}
    cap4 = cap_for("t37", 1)
    v = pr.RUN_DIR / "t37-s01.mp4"; synth_clip(v, secs=2)
    receipts = {"shots": [], "charged_total": 0}
    STAGES.record_artifact(receipts, "t37", 1, "video", v, "video_verified", job="old-job")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "video", "--approved-cap", str(cap4), "--approval-ref", "[private-record-reference]", "--only", "t37:1"])
    pr.MANIFEST = orig
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
    stamp_fp(receipts)
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
         "beats":[{"id":1,"dur_s":4.73,"carries_line":True,"audio_intent":"dialogue","framing_class":"cu_dialogue","frame":{"refs":[],"prompt":"a"}},
                  {"id":2,"dur_s":0.27,"carries_line":False,"audio_intent":"sound_fx","framing_class":"insert","frame":{"refs":[],"prompt":"b"}}]}]}
    code = run_main(["--stage", "frames", "--approved-cap", "100", "--approval-ref", "[private-record-reference]"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    pr.MANIFEST = orig
    assert code == 2 and "frame grid" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == 0
    print("T43 PASS: beat durations off the 30fps frame grid hard-stop before any paid call")

with tempfile.TemporaryDirectory() as tmp:  # T44: multi-carrier beats - two readable-face beats get two lip windows
    shot = {"episode":"t9","shot":1,"shot_s":8,"billing_s":8,"line":"Two halves.","audio":"x.mp3",
            "speaker":"d","dialogue_on_screen":True,"framing_class":"two_shot_dialogue",
            "beats":[{"id":1,"dur_s":3.5,"carries_line":True,"audio_intent":"dialogue","framing_class":"two_shot_dialogue"},
                     {"id":2,"dur_s":1.0,"carries_line":False,"audio_intent":"sound_fx","framing_class":"insert"},
                     {"id":3,"dur_s":3.5,"carries_line":True,"audio_intent":"dialogue","framing_class":"cu_dialogue"}]}
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
         "beats":[{"id":1,"dur_s":0.6,"carries_line":True,"audio_intent":"dialogue","framing_class":"cu_dialogue","frame":{"refs":[],"prompt":"a"}},
                  {"id":2,"dur_s":2.4,"carries_line":False,"audio_intent":"sound_fx","framing_class":"insert","frame":{"refs":[],"prompt":"b"}}]}]}
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
         "beats":[{"id":1,"dur_s":3.5,"carries_line":True,"audio_intent":"dialogue","framing_class":"two_shot_dialogue","action":"a","frame":{"refs":[],"prompt":"a"}},
                  {"id":2,"dur_s":1.0,"carries_line":False,"audio_intent":"sound_fx","framing_class":"insert","action":"b","frame":{"refs":[],"prompt":"b"}},
                  {"id":3,"dur_s":4.5,"carries_line":True,"audio_intent":"dialogue","framing_class":"cu_dialogue","action":"c","frame":{"refs":[],"prompt":"c"}}]}]}
    # human-accepted frames are seeded (acceptance is a human gate by design); everything downstream runs as REAL stage invocations
    receipts = {"shots": [], "charged_total": 0}
    for b in (1, 2, 3):
        f = pr.RUN_DIR / ("t9-s01-b%d-start.png" % b); f.write_bytes(b"frame-%d" % b)
        STAGES.record_artifact(receipts, "t9", 1, "frames", f, "frame_accepted", beat=b, acceptance_ref="[private-record-reference]")
    fx_silence_seed(receipts, "t9", 1, 2)  # insert beat ships silent by explicit decision
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
    # s14 b1 re-staged 2026-10-26 under the redesign mandate: main's 15:12:10 pixel verdict rejected
    # the old frame (wrong-actor gesture, no post-spin motion); the still no longer carries the
    # shield/raised-wand causality - the redirect + chain hit live in b2's insert. One actor action.
    assert "jabs one finger upward" in p1 and "wand still raised" not in p1, p1
    assert "bends upward at a sharp angle" in b2["action"], b2["action"]  # redirect shown as MOTION in b2
    assert "bolt" not in b2["frame"]["prompt"], b2["frame"]["prompt"]  # start frame stays the intact chandelier
    fp1 = b1["frame"]["prompt"]
    assert "jabbing one finger upward" in fp1 and "standing still beside her" in fp1, fp1
    # shield is canon and must stay ESTABLISHED: present-state shimmer around her, never a 'fading'
    # remnant claim; his raised wand (causal-past demand, twice-failed) stays out of the still
    assert "shield-charm shimmer holding around her" in fp1 and "fading" not in fp1, fp1
    assert "wand still raised" not in fp1 and "redirected spell" not in fp1, fp1
    s03 = [s for s in pp.MANIFEST["shots"] if s["episode"] == "e01" and s["shot"] == 3][0]
    p3i = pp.prompt_for(unit(s03, s03["beats"][1]))  # s03 b2 is also an insert in a two_body shot
    assert "Both characters are present" not in p3i, p3i
    print("T49 PASS: insert two-body leak fixed; s14 b1 one-actor-action + present-state shield; redirect carried as b2 motion; canon causality ordered")

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
    assert m['total_cr_staged'] == staged == 34176 and m['total_cr'] == legacy == 28896
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
    fx_silence_seed(receipts, "e01", 16, 1); fx_silence_seed(receipts, "e01", 16, 3)  # T52 isolates the offset mux; FX gate itself is T60/T61
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
    import production_prompts as _pp; pr.AUDIO_DIR = _pp.AUDIO_DIR  # restore global rebind

with tempfile.TemporaryDirectory() as tmp:  # T53: audio_offset_s stress matrix - silent misalignment paths are hard errors
    import stages as ST
    m = json.load(open('shot-manifest-wan30.json'))
    s16 = [s for s in m['shots'] if s['episode'] == 'e01' and s['shot'] == 16][0]
    s04 = {"episode": "e01", "shot": 99, "shot_s": 5.0, "billing_s": 5, "line": "x",
           "audio": "e01-l01-draconia.mp3", "speaker": "draconia", "framing_class": "cu_dialogue",
           "dialogue_on_screen": True}  # synthetic UNDIVIDED shot: real e01 shots are all beat-subdivided now
    cases = [
        (dict(s04, audio_offset_s=2.0), 'undivided'),                       # offset with no wordless head beat
        (dict(s04, audio_offset_s=2.0, audio=None, line=None), 'no approved audio'),  # offset without audio
        (dict(s16, audio_offset_s=1.23), 'frame grid'),                     # off-grid offset
        (dict(s16, audio_offset_s=-1.0), 'non-negative'),                   # negative
        (dict(s16, audio_offset_s=0), 'leading wordless'),                  # wordless head, zero offset
        (dict(s16, audio_offset_s=3.0), 'leading wordless'),                # offset != head total
    ]
    for shot, frag in cases:
        err = ST.validate_beats(shot)
        assert err and frag in err, (frag, err)
    # line-carrying first beat with a positive offset: head is 0, offset must be 0
    s02 = [s for s in m['shots'] if s['episode'] == 'e01' and s['shot'] == 2][0]
    err = ST.validate_beats(dict(s02, audio_offset_s=1.0))
    assert err and 'leading wordless' in err, err
    # whole manifest stays valid
    assert all(ST.validate_beats(s) is None for s in m['shots'])
    print("T53 PASS: offset stress matrix - undivided/no-audio/off-grid/negative/mismatched offsets all hard-error")

with tempfile.TemporaryDirectory() as tmp:  # T54: assemble STOPS when offset+approved audio overruns the shot - no silent truncation
    import importlib, subprocess as _sp
    importlib.reload(_sp)
    pr.subprocess = _sp
    pr.RUN_DIR = Path(tmp) / "run"; pr.RUN_DIR.mkdir(parents=True)
    pr.AUDIO_DIR = Path(tmp) / "audio"; pr.AUDIO_DIR.mkdir(parents=True)
    def ff(args):
        r = _sp.run(["ffmpeg", "-y", "-v", "error"] + args, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    for bid, gen in ((1, 2), (2, 5), (3, 3)):
        ff(["-f", "lavfi", "-i", "testsrc=duration=%d:rate=30:size=320x240" % gen,
            "-pix_fmt", "yuv420p", str(pr.RUN_DIR / ("b%d-src.mp4" % bid))])
    apath = pr.AUDIO_DIR / "e01-l15-draconia.mp3"
    ff(["-f", "lavfi", "-i", "sine=frequency=440:duration=9.6", "-ac", "2", str(apath)])  # 2.0 offset + 9.6 > 9.0 shot
    import stages as ST
    pr._audio_lock = lambda: {"e01-l15-draconia.mp3": ST.sha256_file(apath)}
    receipts = {"started": "", "shots": [], "charged_total": 0, "stage_shots": {}}
    for bid in (1, 2, 3):
        receipts["stage_shots"]["e01:16#b%d" % bid] = {"video": {"state": "video_verified",
            "artifact": str(pr.RUN_DIR / ("b%d-src.mp4" % bid)), "job": None}}
    fx_silence_seed(receipts, "e01", 16, 1); fx_silence_seed(receipts, "e01", 16, 3)  # T54 isolates the overrun stop
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = None
    try: pr.stage_assemble(types.SimpleNamespace(only="e01:16"))
    except SystemExit as e: code = e.code
    assert code == 2
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert 'too long for this shot' in (rec.get('stopped') or ''), rec.get('stopped')
    assert 'assemble' not in rec['stage_shots'].get('e01:16', {}), "overrun must NOT be recorded as assembled"
    print("T54 PASS: offset + over-long approved audio STOPS assemble (no silent truncation, nothing recorded)")
    import production_prompts as _pp; pr.AUDIO_DIR = _pp.AUDIO_DIR  # restore global rebind

with tempfile.TemporaryDirectory() as tmp:  # T55: s16 wordless beat prompt renders clean; next_gen_s billing boundaries
    import production_prompts as pp
    import stages as ST
    m = json.load(open('shot-manifest-wan30.json'))
    s16 = [s for s in m['shots'] if s['episode'] == 'e01' and s['shot'] == 16][0]
    import production_runner as pr2
    for b in s16['beats']:
        u = pr2._beat_shot(s16, b)
        if not b.get('carries_line'):
            assert u.get('speaker') is None and u.get('line') is None and u.get('audio') is None  # approved line never rides a wordless beat
    # beat-declared refs own the prompt: no-leads beats must not pin faces (or the tie-inconsistent ref)
    p1 = pp.prompt_for(pr2._beat_shot(s16, s16['beats'][0]))
    assert '@draconia_front_close' not in p1 and '@harry_front_close' not in p1 and 'Keep  identical' not in p1, p1
    assert '@yule_ball_location' in p1, p1
    p2 = pp.prompt_for(pr2._beat_shot(s16, s16['beats'][1]))
    assert '@draconia_front_close' in p2 and '@draconia_speaking_profile' in p2 and '@harry_front_close' not in p2, p2
    p3 = pp.prompt_for(pr2._beat_shot(s16, s16['beats'][2]))
    assert '@draconia_front_close' not in p3 and '@harry_front_close' not in p3 and '@two_shot_action' in p3, p3
    m6 = [s for s in m['shots'] if s['episode'] == 'e01' and s['shot'] == 6][0]
    p62 = pp.prompt_for(pr2._beat_shot(m6, m6['beats'][1]))  # refs: yule_ball_location only
    assert 'front_close' not in p62 and 'fullbody' not in p62, p62
    m2 = [s for s in m['shots'] if s['episode'] == 'e01' and s['shot'] == 2][0]
    p22 = pp.prompt_for(pr2._beat_shot(m2, m2['beats'][1]))  # refs: harry_fullbody
    assert '@harry_fullbody' in p22 and '@harry_front_close' not in p22 and '@draconia_front_close' not in p22, p22
    # billing boundaries: provider accepts whole seconds {2..10,15,20,25,30} only
    assert ST.next_gen_s(0.033) == 2 and ST.next_gen_s(2.0) == 2 and ST.next_gen_s(2.0001) == 3
    assert ST.next_gen_s(10.0) == 10 and ST.next_gen_s(10.4) == 15 and ST.next_gen_s(30.0) == 30
    assert ST.next_gen_s(31.0) is None
    print("T55 PASS: wordless beat prompt clean, approved line stripped from non-carriers, next_gen_s boundaries exact")

with tempfile.TemporaryDirectory() as tmp:  # T56: unknown reference names are hard errors, never silently dropped
    import stages as ST
    m = json.load(open('shot-manifest-wan30.json'))
    s16 = [s for s in m['shots'] if s['episode'] == 'e01' and s['shot'] == 16][0]
    known = set(pr.REF_FILES)
    # whole manifest passes with the real bank
    assert all(ST.validate_beats(s, known_refs=known) is None for s in m['shots'])
    # typo in a beat frame ref -> hard error naming the typo
    bad = json.loads(json.dumps(s16)); bad['beats'][0]['frame']['refs'] = ['yule_ball_loccation']
    err = ST.validate_beats(bad, known_refs=known)
    assert err and 'yule_ball_loccation' in err, err
    # typo in a shot-level frame ref and in an end_frame ref -> same hard error
    bad2 = dict(s16, frame={"refs": ["draconia_front_clse"]})
    assert 'draconia_front_clse' in (ST.validate_beats(bad2, known_refs=known) or '')
    bad3 = json.loads(json.dumps(s16)); bad3['beats'][1]['end_frame'] = {"refs": ["yule_ball"]}
    assert 'yule_ball' in (ST.validate_beats(bad3, known_refs=known) or '')
    print("T56 PASS: unknown frame/end_frame reference names hard-error at validation (no silent prompt drop, no frames-stage crash)")

with tempfile.TemporaryDirectory() as tmp:  # T57a: legacy whole-shot route refuses beat-subdivided selections BEFORE any spend
    stub = StubNet(); make_env(tmp, "t57a", stub)
    code = run_main(["--legacy-t2v", "--approved-cap", "28896", "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and stub.posts == 0
    assert "beat-subdivided" in rec.get("stopped", "") and "assemble" in rec.get("stopped", ""), rec.get("stopped")
    # already-verified beat shots (historical pre-beat runs) do not block a resume selection that skips them
    rec2 = {"started": "", "charged_total": 768,
            "shots": [{"ep": "e01", "shot": 3, "charged": 768, "state": "verified"}]}
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(rec2))
    stub2posts = stub.posts
    code = run_main(["--legacy-t2v", "--approved-cap", "28896", "--approval-ref", "[private-record-reference]", "--only", "e01:3", "--resume"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 0 and stub.posts == stub2posts  # done beat shot skipped, no refusal, no spend
    print("T57a PASS: legacy refuses pending beat shots pre-spend; verified historical beat shots skip cleanly on resume")

with tempfile.TemporaryDirectory() as tmp:  # T57b: per-frame settle - settle-down reconciles the ledger, settle-up STOPS
    import importlib, subprocess as _sp
    class SettleNet(StubNet):
        def __init__(self, settled, **kw):
            super().__init__(**kw); self.settled = settled
        def get(self, url, headers=None, timeout=None):
            if "/v1/video-projects/" in url:
                return StubResp(200, {"id": "j", "status": "complete", "downloads": [{"url": "https://x/y.mp4"}],
                                      "credits_charged": self.settled})
            return super().get(url, headers=headers, timeout=timeout)
    def fake_verify(cmd, capture_output=False, text=False):
        vdir = Path(cmd[4]); vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "verify.json").write_text(json.dumps({"video": {"r_frame_rate": "30/1"},
            "envelope_correlation": 0.2, "motion": {"near_static": 0, "sampled": 240}, "audio_track": True, "asr_match": True}))
        return types.SimpleNamespace(returncode=0, stderr="")
    s05 = [s for s in pr.MANIFEST["shots"] if s["episode"] == "e01" and s["shot"] == 5][0]
    # settle-down: 700 < 768 charged -> ledger adjusted, no stop
    stub = SettleNet(700); make_env(tmp, "t57b-down", stub)
    pr.subprocess.run = fake_verify
    receipts = {"started": "", "charged_total": 768,
                "shots": [{"ep": "e01", "shot": 5, "charged": 768, "state": "submitted", "job": "j1"}]}
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    pr.complete_job("e01", 5, s05, "j1", receipts, receipts["shots"][0])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert rec["charged_total"] == 700 and rec["shots"][0]["settled_credits"] == 700, rec["charged_total"]
    # settle-up: 800 > 768 charged -> STOP, over approved estimate
    stub = SettleNet(800); make_env(tmp, "t57b-up", stub)
    pr.subprocess.run = fake_verify
    receipts = {"started": "", "charged_total": 768,
                "shots": [{"ep": "e01", "shot": 5, "charged": 768, "state": "submitted", "job": "j2"}]}
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = None
    try: pr.complete_job("e01", 5, s05, "j2", receipts, receipts["shots"][0])
    except SystemExit as e: code = e.code
    assert code == 2
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "settle UP" in (rec.get("stopped") or ""), rec.get("stopped")
    importlib.reload(_sp); pr.subprocess = _sp
    print("T57b PASS: settle-down reconciles ledger to 700; settle-up STOPS naming the over-estimate charge")

with tempfile.TemporaryDirectory() as tmp:  # T58: durable financial lock after settle-up
    class SettleUpNet(StubNet):
        def get(self, url, headers=None, timeout=None):
            if "/v1/video-projects/" in url:
                return StubResp(200, {"id": "j", "status": "complete", "downloads": [{"url": "https://x/y.mp4"}],
                                      "credits_charged": 800})
            return super().get(url, headers=headers, timeout=timeout)
    def fake_verify58(cmd, capture_output=False, text=False):
        vdir = Path(cmd[4]); vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "verify.json").write_text(json.dumps({"video": {"r_frame_rate": "30/1"},
            "envelope_correlation": 0.2, "motion": {"near_static": 0, "sampled": 240}, "audio_track": True, "asr_match": True}))
        return types.SimpleNamespace(returncode=0, stderr="")
    s05 = [s for s in pr.MANIFEST["shots"] if s["episode"] == "e01" and s["shot"] == 5][0]

    # a) settle-up writes the durable marker
    stub = SettleUpNet(); make_env(tmp, "t58a", stub); pr.subprocess.run = fake_verify58
    receipts = {"started": "", "charged_total": 768,
                "shots": [{"ep": "e01", "shot": 5, "charged": 768, "state": "submitted", "job": "j9"}]}
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    try: pr.complete_job("e01", 5, s05, "j9", receipts, receipts["shots"][0])
    except SystemExit: pass
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    lk = rec.get("settle_up_unreconciled")
    assert lk and lk["charged"] == 768 and lk["settled"] == 800 and lk["job"] == "j9", lk

    # b) fresh invocations: every spend path refuses pre-POST; resume polling still completes (read-only)
    stub2 = StubNet(); make_env(tmp, "t58b", stub2)  # fresh env, SAME receipts dir pattern but new run dir
    import production_prompts as _pp; pr.AUDIO_DIR = _pp.AUDIO_DIR
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(rec))
    code = run_main(GO)  # legacy whole-shot route
    rec_b = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and stub2.posts == 0 and "FINANCIAL LOCK" in rec_b.get("stopped", ""), rec_b.get("stopped")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(rec))
    code = run_main(["--stage", "video", "--approved-cap", "768", "--approval-ref", "[private-record-reference]", "--only", "e02:12"])  # exact quote so the lock (not the cap gate) is what refuses
    rec_b = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and stub2.posts == 0 and "FINANCIAL LOCK" in rec_b.get("stopped", ""), rec_b.get("stopped")
    # resume poll is read-only: a submitted job completes and verifies under the lock, then the lock blocks new POSTs
    rec_resume = dict(rec); rec_resume["shots"] = [{"ep": "e01", "shot": 5, "charged": 768, "state": "submitted", "job": "j-live"}]
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(rec_resume))
    code = run_main(GO + ["--resume", "--only", "e02:12"])
    rec_b = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    s5r = [s for s in rec_b["shots"] if s["shot"] == 5][0]
    assert s5r["state"] == "verified" and stub2.posts == 0, (s5r.get("state"), stub2.posts)

    # c) reconcile with explicit reason: clears lock, keeps settled truth + audit history
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(rec_b))
    code = run_main(["--reconcile-settle-up", "MH dashboard shows 800 charged on job j9; verified by operator"])
    rec_c = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 0 and "settle_up_unreconciled" not in rec_c
    assert rec_c["settle_up_history"][0]["prior"]["settled"] == 800 and "dashboard" in rec_c["settle_up_history"][0]["reason"]
    # spend works again after explicit reconcile
    code = run_main(GO + ["--only", "e02:12"])
    rec_d = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert stub2.posts == 1 and code == 0, (stub2.posts, code)

    # d) reconcile with nothing pending -> refuses, changes nothing
    code = run_main(["--reconcile-settle-up", "nothing pending"])
    assert code == 2

    # e) ordinary stopped reason does NOT lock (only the financial marker does)
    rec_plain = {"started": "", "charged_total": 0, "shots": [], "stopped": "gate failures e01 s03: [...]"}
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(rec_plain))
    code = run_main(GO + ["--only", "e02:12"])
    assert stub2.posts == 2, stub2.posts  # proceeded: no financial lock from a generic stop
    print("T58 PASS: settle-up durably locks all spend paths across restarts; resume polls read-only; explicit reasoned reconcile clears with audit trail; generic stops never lock")

with tempfile.TemporaryDirectory() as tmp:  # T59: explicit per-unit audio intent drives the request and the verify gate
    # A) resolver defaults and explicit override
    shot = {"episode": "t", "shot": 1, "shot_s": 4, "billing_s": 4, "line": "L.", "audio": "a.mp3",
            "speaker": "d", "audio_offset_s": 2.0,
            "beats": [{"id": 1, "dur_s": 2.0, "action": "x", "audio_intent": "sound_fx"},
                      {"id": 2, "dur_s": 2.0, "action": "y", "carries_line": True, "audio_intent": "dialogue"}]}
    assert STAGES.validate_beats(shot) is None, STAGES.validate_beats(shot)
    assert STAGES.audio_intent(shot, shot["beats"][0]) == "sound_fx"
    assert STAGES.audio_intent(shot, shot["beats"][1]) == "dialogue"
    sil = dict(shot["beats"][0], audio_intent="silent")
    assert STAGES.audio_intent(shot, sil) == "silent"
    # defaults when a synthetic manifest omits the field
    assert STAGES.audio_intent({}, {"carries_line": True}) == "dialogue"
    assert STAGES.audio_intent({}, {}) == "sound_fx"
    assert STAGES.audio_intent({"audio": "a.mp3"}) == "dialogue"
    assert STAGES.audio_intent({}) == "sound_fx"

    # B) validation: intent is explicit per beat and consistent with carries_line / approved audio
    def vb(**kw):
        s2 = dict(shot); s2.update(kw); return STAGES.validate_beats(s2)
    bad = dict(shot); bad["beats"] = [dict(b) for b in shot["beats"]]; del bad["beats"][1]["audio_intent"]
    assert "declares no audio_intent" in vb(beats=bad["beats"])
    bad = dict(shot); bad["beats"] = [dict(b) for b in shot["beats"]]; bad["beats"][1]["audio_intent"] = "sound_fx"
    assert "carriers must be 'dialogue'" in vb(beats=bad["beats"])
    bad = dict(shot); bad["beats"] = [dict(b) for b in shot["beats"]]; bad["beats"][0]["audio_intent"] = "dialogue"
    assert "wordless but audio_intent is 'dialogue'" in vb(beats=bad["beats"])
    bad = dict(shot); bad["beats"] = [dict(b) for b in shot["beats"]]; bad["beats"][0]["audio_intent"] = "muted"
    assert "not one of" in vb(beats=bad["beats"])
    assert "ambiguous" in vb(audio_intent="dialogue")
    assert STAGES.validate_beats({"episode": "t", "shot": 2, "shot_s": 4, "billing_s": 4,
                                  "audio": "a.mp3", "audio_intent": "sound_fx"}) is not None
    assert STAGES.validate_beats({"episode": "t", "shot": 2, "shot_s": 4, "billing_s": 4,
                                  "audio_intent": "dialogue"}) is not None
    assert STAGES.validate_beats({"episode": "t", "shot": 2, "shot_s": 4, "billing_s": 4,
                                  "audio_intent": "muted"}) is not None
    assert STAGES.validate_beats({"episode": "t", "shot": 2, "shot_s": 4, "billing_s": 4,
                                  "audio_intent": "sound_fx"}) is None
    # real manifest: every unit explicit and valid
    for s in pr.MANIFEST["shots"]:
        assert STAGES.validate_beats(s, known_refs=pr.REF_FILES) is None, (s["episode"], s["shot"], STAGES.validate_beats(s))

    # C) request body mapping + verify gate, on the real 3-beat s03
    class I2VCap(I2VStub):
        def __init__(self):
            super().__init__(); self.bodies = []
        def post(self, url, headers=None, json=None, timeout=None):
            if url.endswith("/v1/image-to-video"):
                self.bodies.append(dict(json))
            return super().post(url, headers=headers, json=json, timeout=timeout)
    def fake_verify(track):
        def fv(cmd, capture_output=False, text=False):
            trk = track(cmd[2]) if callable(track) else track
            vdir = Path(cmd[4]); vdir.mkdir(parents=True, exist_ok=True)
            (vdir / "verify.json").write_text(json.dumps({"video": {"r_frame_rate": "30/1"},
                "envelope_correlation": 0.2, "motion": {"near_static": 0, "sampled": 240},
                "audio_track": trk, "asr_match": True}))
            return types.SimpleNamespace(returncode=0, stderr="")
        return fv
    GO3 = ["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"]
    saved_gate = pr.GATE_AFTER; pr.GATE_AFTER = {}  # s03's inspection stop is not what this test exercises
    orig = pr.MANIFEST
    s03 = [s for s in orig["shots"] if s["episode"] == "e01" and s["shot"] == 3][0]

    # c1: all current units non-silent -> every body requests audio:true
    stub = I2VCap(); make_env(tmp, "t59a", stub); pr.subprocess.run = fake_verify(True)
    receipts = {"shots": [], "charged_total": 0}
    record_s03_frames(receipts, "frame_accepted", pr.RUN_DIR)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(GO3)
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and rec.get("stopped") == "video stage batch done", (code, rec.get("stopped"))
    assert [bd["audio"] for bd in stub.bodies] == [True, True, True], [bd["audio"] for bd in stub.bodies]

    # c2: a wordless beat declared silent -> that beat's body requests audio:false, carrier unchanged,
    #     and a provider clip WITH a track hard-fails the gate (audio:false must be honored)
    import copy
    mod = copy.deepcopy(orig)
    ms03 = [s for s in mod["shots"] if s["episode"] == "e01" and s["shot"] == 3][0]
    ms03["beats"][1]["audio_intent"] = "silent"
    pr.MANIFEST = mod
    stub = I2VCap(); make_env(tmp, "t59b", stub); pr.subprocess.run = fake_verify(True)
    receipts = {"shots": [], "charged_total": 0}
    record_s03_frames(receipts, "frame_accepted", pr.RUN_DIR)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(GO3)
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "intent silent" in rec.get("stopped", ""), (code, rec.get("stopped"))
    assert [bd["audio"] for bd in stub.bodies] == [True, False], [bd["audio"] for bd in stub.bodies]

    # c3: same silent beat, provider honors audio:false (no track) -> all three beats complete
    stub = I2VCap(); make_env(tmp, "t59c", stub); pr.subprocess.run = fake_verify(lambda clip: "-b2" not in clip)  # provider honors audio:false on the silent beat only
    receipts = {"shots": [], "charged_total": 0}
    record_s03_frames(receipts, "frame_accepted", pr.RUN_DIR)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(GO3)
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and rec.get("stopped") == "video stage batch done", (code, rec.get("stopped"))
    assert [bd["audio"] for bd in stub.bodies] == [True, False, True], [bd["audio"] for bd in stub.bodies]

    # c4: ordinary dialogue/sound_fx units still REQUIRE a track - a trackless clip fails as before
    pr.MANIFEST = orig
    stub = I2VCap(); make_env(tmp, "t59d", stub); pr.subprocess.run = fake_verify(False)
    receipts = {"shots": [], "charged_total": 0}
    record_s03_frames(receipts, "frame_accepted", pr.RUN_DIR)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(GO3)
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "no audio track" in rec.get("stopped", ""), (code, rec.get("stopped"))
    assert [bd["audio"] for bd in stub.bodies] == [True], stub.bodies
    pr.GATE_AFTER = saved_gate
    print("T59 PASS: explicit per-beat audio_intent; silent->audio:false in the request; verify gate validates the actual track both ways; dialogue and sound_fx unchanged")

with tempfile.TemporaryDirectory() as tmp:  # T60: FX gate - strict stop, labeled preview, accepted-FX mix, tamper/regen stops
    # Structural fixture: wordless sound_fx head beat + offset carrier (s16's SHAPE; absolute
    # durations differ - s16's own 9.0s offset path is covered by T52 on the real manifest).
    import re as _re
    def rms_db(path, ss, t):
        r = REAL_RUN(["ffmpeg", "-ss", str(ss), "-t", str(t), "-i", str(path),
                      "-af", "astats=measure_overall=RMS_level:measure_perchannel=none", "-f", "null", "-"],
                     capture_output=True, text=True)
        m = _re.search(r"RMS level dB:\s*(-inf|-?[\d.]+)", r.stderr)
        return float("-inf") if (m is None or m.group(1) == "-inf") else float(m.group(1))
    make_stage_env(tmp, "t60")
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode": "t10", "shot": 1, "shot_s": 11.0, "billing_s": 11.0, "line": "After.", "audio": "e01-l01-draconia.mp3",
         "speaker": "draconia", "dialogue_on_screen": True, "framing_class": "cu_dialogue", "audio_offset_s": 2.0,
         "beats": [{"id": 1, "dur_s": 2.0, "carries_line": False, "audio_intent": "sound_fx", "framing_class": "wide_action", "action": "crash"},
                   {"id": 2, "dur_s": 9.0, "carries_line": True, "audio_intent": "dialogue", "framing_class": "cu_dialogue", "action": "line"}]},
        {"episode": "t10", "shot": 2, "shot_s": 2, "billing_s": 2, "line": None, "audio": None,
         "dialogue_on_screen": False, "framing_class": "wide_action", "audio_intent": "sound_fx"}]}
    receipts = {"shots": [], "charged_total": 0}
    for b, secs in ((1, 2), (2, 9)):
        v = pr.RUN_DIR / ("t10-s01-b%d.mp4" % b)
        synth_clip(v, secs=secs, audio=True)  # 440Hz tone = the would-be crash sound
        STAGES.record_artifact(receipts, "t10", 1, "video", v, "video_verified", beat=b)
    v2 = pr.RUN_DIR / "t10-s02.mp4"; synth_clip(v2, secs=2, audio=True)
    STAGES.record_artifact(receipts, "t10", 2, "video", v2, "video_verified")
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    def rec():
        return json.loads((pr.RUN_DIR / "run-receipts.json").read_text())

    # a) fx stage: sound_fx units only, candidate state, bound to the verified video sha
    code = run_main(["--stage", "fx"])
    fx1 = STAGES.get_artifact(rec(), "t10", 1, "fx", beat=1)
    assert code == 2 and fx1 and fx1["state"] == "fx_extracted", (code, rec().get("stopped"))
    assert fx1["upstream_sha256"] == STAGES.get_artifact(rec(), "t10", 1, "video", beat=1)["sha256"]
    assert STAGES.get_artifact(rec(), "t10", 1, "fx", beat=2) is None  # carrier is never an FX source
    fx2 = STAGES.get_artifact(rec(), "t10", 2, "fx")
    assert fx2 and fx2["state"] == "fx_extracted"

    # b) listen gate refuses unattributed acceptance, then records main's decision as main's
    code = run_main(["--accept-fx", "t10:1#b1"])
    assert code == 2 and "REFUSED" in rec().get("stopped", "")
    code = run_main(["--accept-fx", "t10:2", "--approval-ref", "main:msg-fx-01"])
    fx2 = STAGES.get_artifact(rec(), "t10", 2, "fx")
    assert code == 0 and fx2["state"] == "fx_accepted" and fx2["acceptance_actor"] == "main"

    # c) STRICT: undecided sound_fx FX blocks final assemble - canon sound is never silently dropped
    code = run_main(["--stage", "assemble", "--only", "t10:1"])
    assert code == 2 and "no FX decision" in rec().get("stopped", "") and "t10-s01-b1" in rec()["stopped"], rec().get("stopped")
    assert STAGES.get_artifact(rec(), "t10", 1, "assemble") is None
    # c2) PREVIEW: labeled review render - silent crash window, state downstream refuses
    code = run_main(["--stage", "assemble", "--only", "t10:1", "--preview"])
    art = STAGES.get_artifact(rec(), "t10", 1, "assemble")
    assert code == 2 and art and art["state"] == "assembled_preview" and art["mode"] == "preview-mux" and not art["fx"], (code, art)
    assert "t10-s01-b1" in art["fx_missing"] and "-preview.mp4" in art["artifact"]
    assert rms_db(art["artifact"], 0.1, 1.8) < -60, rms_db(art["artifact"], 0.1, 1.8)
    rc_voice = rms_db(art["artifact"], 4.0, 5.0)
    assert rc_voice > -45, rc_voice
    errs = []
    STAGES.require_artifact(rec(), "t10", 1, "lipsync", lambda m: errs.append(m))
    assert errs and "assembled_preview" in errs[0], errs  # downstream hard-refuses preview

    # d) accept b1 FX -> strict assemble mixes it; crash window audible; voice position/level preserved
    run_main(["--accept-fx", "t10:1#b1", "--approval-ref", "[private-record-reference]"])
    code = run_main(["--stage", "assemble", "--only", "t10:1"])
    art = STAGES.get_artifact(rec(), "t10", 1, "assemble")
    assert code == 2 and art["state"] == "assembled" and art["mode"] == "mux+fx" and not art["fx_missing"], (code, art)
    assert art["fx"][0]["offset_s"] == 0.0 and art["fx"][0]["sha256"] == STAGES.sha256_file(fx1_path := (pr.RUN_DIR / "t10-s01-b1-fx.wav"))
    assert rms_db(art["artifact"], 0.1, 1.8) > -45, rms_db(art["artifact"], 0.1, 1.8)  # crash audible
    rm_voice = rms_db(art["artifact"], 4.0, 5.0)
    assert abs(rm_voice - rc_voice) < 1.5, (rc_voice, rm_voice)  # approved take passes at its own format, not ducked/covered
    assert abs(probe_dur(art["artifact"]) - 11.0) < 0.4, probe_dur(art["artifact"])  # timeline intact

    # e) wordless shot: accepted FX replaces the silent passthrough in the strict path
    code = run_main(["--stage", "assemble", "--only", "t10:2"])
    art2 = STAGES.get_artifact(rec(), "t10", 2, "assemble")
    assert code == 2 and art2["mode"] == "fx" and art2["state"] == "assembled" and rms_db(art2["artifact"], 0.1, 1.8) > -45, (code, art2.get("mode"))

    # f) tampered accepted FX hard-stops assemble (sha drift)
    p = Path(fx2["artifact"]); p.write_bytes(p.read_bytes() + b"tamper")
    code = run_main(["--stage", "assemble", "--only", "t10:2"])
    assert code == 2 and "drifted since acceptance" in rec().get("stopped", ""), rec().get("stopped")

    # g) regenerated upstream video invalidates the accepted FX (re-listen required)
    v1 = pr.RUN_DIR / "t10-s01-b1.mp4"  # regenerated unit: different content, same length
    r = REAL_RUN(["ffmpeg","-y","-v","error","-f","lavfi","-i","testsrc=duration=2:size=320x240:rate=30",
                  "-f","lavfi","-i","sine=frequency=550:duration=2","-c:a","aac","-shortest",str(v1)],
                 capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-200:]
    STAGES.record_artifact(receipts2 := rec(), "t10", 1, "video", v1, "video_verified", beat=1)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts2))
    code = run_main(["--stage", "assemble", "--only", "t10:1"])
    assert code == 2 and "regenerated" in rec().get("stopped", ""), rec().get("stopped")
    pr.MANIFEST = orig
    print("T60 PASS: undecided sound_fx blocks final assemble; preview renders labeled+downstream-refused; accepted FX audible; voice preserved; tamper/regeneration hard-stop")

with tempfile.TemporaryDirectory() as tmp:  # T61: peak guard, full-window voice preservation, fx-silence decision path
    def peak_db(path):
        r = REAL_RUN(["ffmpeg", "-i", str(path), "-af", "astats=measure_overall=Peak_level:measure_perchannel=none",
                      "-f", "null", "-"], capture_output=True, text=True)
        m = _re.search(r"Peak level dB:\s*(-inf|-?[\d.]+)", r.stderr)
        return float(m.group(1))
    make_stage_env(tmp, "t61")
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode": "t11", "shot": 1, "shot_s": 11.0, "billing_s": 11.0, "line": "After.", "audio": "e01-l01-draconia.mp3",
         "speaker": "draconia", "dialogue_on_screen": True, "framing_class": "cu_dialogue", "audio_offset_s": 2.0,
         "beats": [{"id": 1, "dur_s": 2.0, "carries_line": False, "audio_intent": "sound_fx", "framing_class": "wide_action", "action": "crash"},
                   {"id": 2, "dur_s": 9.0, "carries_line": True, "audio_intent": "dialogue", "framing_class": "cu_dialogue", "action": "line"}]}]}
    receipts = {"shots": [], "charged_total": 0}
    v1 = pr.RUN_DIR / "t11-s01-b1.mp4"  # FULL-SCALE tone: a blind mux would clip
    r = REAL_RUN(["ffmpeg","-y","-v","error","-f","lavfi","-i","testsrc=duration=2:size=320x240:rate=30",
                  "-f","lavfi","-i","sine=frequency=440:duration=2,volume=8","-c:a","aac","-shortest",str(v1)],
                 capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-200:]
    STAGES.record_artifact(receipts, "t11", 1, "video", v1, "video_verified", beat=1)
    v2 = pr.RUN_DIR / "t11-s01-b2.mp4"; synth_clip(v2, secs=9, audio=True)
    STAGES.record_artifact(receipts, "t11", 1, "video", v2, "video_verified", beat=2)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    def rec61():
        return json.loads((pr.RUN_DIR / "run-receipts.json").read_text())

    # fx-silence: attribution enforced; dialogue units refused (the take IS their sound)
    code = run_main(["--fx-silence", "t11:1#b1"])
    assert code == 2 and "REFUSED" in rec61().get("stopped", "")
    code = run_main(["--fx-silence", "t11:1#b2", "--approval-ref", "main:t61-x"])
    assert code == 2 and "not a sound_fx unit" in rec61().get("stopped", "")

    # control: explicit silence decision satisfies the gate; crash window silent, voice intact
    code = run_main(["--fx-silence", "t11:1#b1", "--approval-ref", "main:t61-silence"])
    assert code == 0
    code = run_main(["--stage", "assemble", "--only", "t11:1"])
    ctrl = STAGES.get_artifact(rec61(), "t11", 1, "assemble")
    assert code == 2 and ctrl and ctrl["mode"] == "mux" and not ctrl["fx"] and not ctrl["fx_missing"], (code, ctrl)
    assert rms_db(ctrl["artifact"], 0.1, 1.8) < -60

    # a silence decision stands against later --stage fx sweeps (no side-effect reversal)
    run_main(["--stage", "fx"])
    code = run_main(["--accept-fx", "t11:1#b1", "--approval-ref", "main:t61-listen"])
    assert code == 2 and "no fx_extracted candidate" in rec61().get("stopped", "")
    # explicit attributed reversal, then re-extract, listen, accept
    code = run_main(["--fx-undecide", "t11:1#b1"])
    assert code == 2 and "REFUSED" in rec61().get("stopped", "")
    assert run_main(["--fx-undecide", "t11:1#b1", "--approval-ref", "main:t61-reconsider"]) == 0
    run_main(["--stage", "fx"])
    code = run_main(["--accept-fx", "t11:1#b1", "--approval-ref", "main:t61-listen"])
    assert code == 0
    code = run_main(["--stage", "assemble", "--only", "t11:1"])
    mix = STAGES.get_artifact(rec61(), "t11", 1, "assemble")
    assert code == 2 and mix["mode"] == "mux+fx", (code, mix)

    # peak guard: full-scale FX cannot clip the mix
    pk = peak_db(mix["artifact"])
    assert -2.0 <= pk <= -0.4, pk  # limited near 0.94FS (-0.54dB), not muted, not clipped

    # full-window voice preservation: every 1s window of the take span within 1.5dB of control
    for w in range(2, 11):
        a, b_ = rms_db(ctrl["artifact"], w, 1), rms_db(mix["artifact"], w, 1)
        assert abs(a - b_) < 1.5, (w, a, b_)
    assert abs(probe_dur(mix["artifact"]) - 11.0) < 0.4
    pr.MANIFEST = orig
    print("T61 PASS: peak guard holds full-scale FX at limit without muting; voice preserved across every 1s window; fx-silence attributed, dialogue-refused, gate-satisfying, reversal only via attributed --fx-undecide")

with tempfile.TemporaryDirectory() as tmp:  # T62: REAL s16 geometry + REAL approved l15 take - overlap ducking proof + clip stop
    make_stage_env(tmp, "t62")  # real accepted-audio lock, real take, REAL_RUN
    real_s16 = [s for s in json.load(open("shot-manifest-wan30.json"))["shots"]
                if s["episode"] == "e01" and s["shot"] == 16][0]
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [real_s16]}
    receipts = {"shots": [], "charged_total": 0}
    def mkbeat(bid, secs, freq, vol=None):
        v = pr.RUN_DIR / ("e01-s16-b%d.mp4" % bid)
        srcq = "sine=frequency=%d:duration=%d%s" % (freq, secs, (",volume=%s" % vol) if vol else "")
        r = REAL_RUN(["ffmpeg","-y","-v","error","-f","lavfi","-i","testsrc=duration=%d:size=320x240:rate=30" % secs,
                      "-f","lavfi","-i",srcq,"-c:a","aac","-shortest",str(v)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-200:]
        STAGES.record_artifact(receipts, "e01", 16, "video", v, "video_verified", beat=bid)
    mkbeat(1, 2, 440)   # crash window 0-2s, no voice overlap
    mkbeat(2, 5, 220)   # carrier, trimmed to 4.4s
    mkbeat(3, 3, 6000, vol="0.2")  # hands insert 6.4-9.0s at a sane FX level - OVERLAPS the take (2.0-8.43s)
    fx_silence_seed(receipts, "e01", 16, 1); fx_silence_seed(receipts, "e01", 16, 3)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    def rec62():
        return json.loads((pr.RUN_DIR / "run-receipts.json").read_text())

    # control: voice-only strict assemble over the REAL 9.0s shot and REAL take
    code = run_main(["--stage", "assemble", "--only", "e01:16"])
    ctrl = STAGES.get_artifact(rec62(), "e01", 16, "assemble")
    assert code == 2 and ctrl and ctrl["mode"] == "mux", (code, rec62().get("stopped"))
    assert abs(probe_dur(ctrl["artifact"]) - 9.0) < 0.4, probe_dur(ctrl["artifact"])

    # mixed: reverse the silence decisions (attributed), re-extract, listen-accept both
    assert run_main(["--fx-undecide", "e01:16#b1", "--approval-ref", "main:t62-r1"]) == 0
    assert run_main(["--fx-undecide", "e01:16#b3", "--approval-ref", "main:t62-r3"]) == 0
    run_main(["--stage", "fx", "--only", "e01:16"])
    assert run_main(["--accept-fx", "e01:16#b1", "--approval-ref", "main:t62-l1"]) == 0
    assert run_main(["--accept-fx", "e01:16#b3", "--approval-ref", "main:t62-l3"]) == 0
    code = run_main(["--stage", "assemble", "--only", "e01:16"])
    mix = STAGES.get_artifact(rec62(), "e01", 16, "assemble")
    assert code == 2 and mix["mode"] == "mux+fx" and [f["offset_s"] for f in mix["fx"]] == [0.0, 6.4], (code, mix)

    # voice-band proof: lowpass 3kHz isolates the voice from the 6kHz FX tone; every 0.5s
    # window of the take span - including the 6.5-8.4 OVERLAP - must match the control
    def voice_rms(path, ss, t):
        r = REAL_RUN(["ffmpeg","-ss",str(ss),"-t",str(t),"-i",str(path),
                      "-af","lowpass=f=3000,astats=measure_overall=RMS_level:measure_perchannel=none","-f","null","-"],
                     capture_output=True, text=True)
        m = _re.search(r"RMS level dB:\s*(-inf|-?[\d.]+)", r.stderr)
        return float("-inf") if (m is None or m.group(1) == "-inf") else float(m.group(1))
    w = 2.0
    while w < 8.9:
        a, b_ = voice_rms(ctrl["artifact"], w, 0.5), voice_rms(mix["artifact"], w, 0.5)
        assert abs(a - b_) < 1.5, ("voice ducked at window", w, a, b_)
        w += 0.5
    assert rms_db(mix["artifact"], 0.1, 1.8) > -45  # crash window audible, full band
    assert abs(probe_dur(mix["artifact"]) - 9.0) < 0.4

    # clip stop: full-scale FX overlapping the hot take (-2.7dBFS peaks) must STOP, not ship
    make_stage_env(tmp, "t62b")
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [real_s16]}
    receipts = {"shots": [], "charged_total": 0}
    mkbeat(1, 2, 440); mkbeat(2, 5, 220); mkbeat(3, 3, 6000, vol="10")  # full-scale overlap
    fx_silence_seed(receipts, "e01", 16, 1)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    run_main(["--stage", "fx", "--only", "e01:16"])
    assert run_main(["--accept-fx", "e01:16#b3", "--approval-ref", "main:t62-hot"]) == 0
    code = run_main(["--stage", "assemble", "--only", "e01:16"])
    assert code == 2 and "clips" in rec62().get("stopped", ""), rec62().get("stopped")
    assert STAGES.get_artifact(rec62(), "e01", 16, "assemble") is None, "clipped render must NOT be recorded"
    pr.MANIFEST = orig
    print("T62 PASS: real s16 9.0s + real l15 take (6.426s, offset 2.0 -> 8.426s end); voice-band windows identical through FX overlap; full-scale overlap clips -> hard stop, nothing recorded")

with tempfile.TemporaryDirectory() as tmp:  # T63: stale-assemble safety - changed inputs invalidate prior output on every downstream path
    make_stage_env(tmp, "t63")
    orig = pr.MANIFEST
    shot = {"episode": "t63", "shot": 1, "shot_s": 11.0, "billing_s": 11.0, "line": "After.", "audio": "e01-l01-draconia.mp3",
            "speaker": "draconia", "dialogue_on_screen": True, "framing_class": "cu_dialogue", "audio_offset_s": 2.0,
            "beats": [{"id": 1, "dur_s": 2.0, "carries_line": False, "audio_intent": "sound_fx", "framing_class": "wide_action", "action": "crash"},
                      {"id": 2, "dur_s": 9.0, "carries_line": True, "audio_intent": "dialogue", "framing_class": "cu_dialogue", "action": "line"}]}
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [shot]}
    receipts = {"shots": [], "charged_total": 0}
    for b, secs in ((1, 2), (2, 9)):
        v = pr.RUN_DIR / ("t63-s01-b%d.mp4" % b)
        synth_clip(v, secs=secs, audio=True)
        STAGES.record_artifact(receipts, "t63", 1, "video", v, "video_verified", beat=b)
    fx_silence_seed(receipts, "t63", 1, 1)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    def rec63():
        return json.loads((pr.RUN_DIR / "run-receipts.json").read_text())

    # good pipeline: assemble -> lipsync (soundtrack via not_readable) -> edit, all current
    code = run_main(["--stage", "assemble", "--only", "t63:1"])
    a1 = STAGES.get_artifact(rec63(), "t63", 1, "assemble")
    assert code == 2 and a1 and a1["state"] == "assembled" and a1.get("inputs_sha256"), (code, rec63().get("stopped"))
    canonical = Path(a1["artifact"])
    receipts = rec63()
    receipts["stage_shots"]["t63:1"]["face_verdict"] = "not_readable"
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "lipsync", "--only", "t63:1"])
    l1 = STAGES.get_artifact(rec63(), "t63", 1, "lipsync")
    assert code == 2 and l1 and l1["mode"] == "soundtrack", (code, rec63().get("stopped"))
    code = run_main(["--stage", "edit", "--only", "t63:1"])
    assert code == 2 and STAGES.get_artifact(rec63(), "t63", 0, "edit"), rec63().get("stopped")

    # inputs change: silence decision reversed -> re-assemble STOPS at the strict gate, and the
    # prior good assemble is invalidated BEFORE the stop (file preserved as a named backup)
    assert run_main(["--fx-undecide", "t63:1#b1", "--approval-ref", "main:t63-reconsider"]) == 0
    code = run_main(["--stage", "assemble", "--only", "t63:1"])
    assert code == 2 and "no FX decision" in rec63().get("stopped", ""), rec63().get("stopped")
    a2 = STAGES.get_artifact(rec63(), "t63", 1, "assemble")
    assert a2["state"] == "assembled_stale" and "stale_reason" in a2, a2
    assert ".stale-" in Path(a2["artifact"]).name and Path(a2["artifact"]).exists()  # backup preserved
    assert not canonical.exists()  # canonical path no longer serves stale bytes
    e_stale = STAGES.get_artifact(rec63(), "t63", 0, "edit")
    assert e_stale["state"] == "edited_stale" and ".stale-" in e_stale["artifact"] and Path(e_stale["artifact"]).exists(), e_stale  # cascaded at assemble-invalidation time

    # downstream refuses the stale record on every path - no stale success
    code = run_main(["--stage", "lipsync", "--only", "t63:1"])
    assert code == 2 and "assembled_stale" in rec63().get("stopped", ""), rec63().get("stopped")
    code = run_main(["--stage", "edit", "--only", "t63:1"])
    assert code == 2 and rec63().get("stopped", ""), "edit must not consume a stale chain"

    # resume: re-decide silence -> fresh assemble at the canonical path -> downstream flows again
    assert run_main(["--fx-silence", "t63:1#b1", "--approval-ref", "main:t63-resilence"]) == 0
    code = run_main(["--stage", "assemble", "--only", "t63:1"])
    a3 = STAGES.get_artifact(rec63(), "t63", 1, "assemble")
    assert code == 2 and a3["state"] == "assembled" and a3["artifact"] == str(canonical) and canonical.exists(), (code, rec63().get("stopped"))
    code = run_main(["--stage", "lipsync", "--only", "t63:1"])
    l2 = STAGES.get_artifact(rec63(), "t63", 1, "lipsync")
    assert code == 2 and l2["state"] == "lipsync_done" and l2["sha256"] == a3["sha256"], (code, l2)
    code = run_main(["--stage", "edit", "--only", "t63:1"])
    assert code == 2, rec63().get("stopped")

    # manifest change WITHOUT re-assemble: fingerprint freshness stops lipsync and edit anyway
    shot2 = dict(shot); shot2["shot_s"] = 12.0
    shot2["beats"] = [dict(shot["beats"][0]), dict(shot["beats"][1], dur_s=10.0)]
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [shot2]}
    code = run_main(["--stage", "lipsync", "--only", "t63:1"])
    assert code == 2 and "STALE" in rec63().get("stopped", ""), rec63().get("stopped")
    code = run_main(["--stage", "edit", "--only", "t63:1"])
    assert code == 2 and "not current" in rec63().get("stopped", ""), rec63().get("stopped")
    e_stale2 = STAGES.get_artifact(rec63(), "t63", 0, "edit")
    assert e_stale2["state"] == "edited_stale", e_stale2  # edit run itself invalidated the episode record before stopping
    pr.MANIFEST = orig
    print("T63 PASS: changed inputs invalidate a prior good assemble (file preserved as named backup); lipsync/edit/resume never consume stale output; fresh re-assemble unblocks; manifest drift without re-assemble stops downstream")

with tempfile.TemporaryDirectory() as tmp:  # T64: unfingerprinted legacy records are NEVER blessed; edited episode invalidates on upstream change/failure
    make_stage_env(tmp, "t64")
    orig = pr.MANIFEST
    shot = {"episode": "t64", "shot": 1, "shot_s": 11.0, "billing_s": 11.0, "line": "After.", "audio": "e01-l01-draconia.mp3",
            "speaker": "draconia", "dialogue_on_screen": True, "framing_class": "cu_dialogue", "audio_offset_s": 2.0,
            "beats": [{"id": 1, "dur_s": 2.0, "carries_line": False, "audio_intent": "sound_fx", "framing_class": "wide_action", "action": "crash"},
                      {"id": 2, "dur_s": 9.0, "carries_line": True, "audio_intent": "dialogue", "framing_class": "cu_dialogue", "action": "line"}]}
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [shot]}
    receipts = {"shots": [], "charged_total": 0}
    for b, secs in ((1, 2), (2, 9)):
        v = pr.RUN_DIR / ("t64-s01-b%d.mp4" % b)
        synth_clip(v, secs=secs, audio=True)
        STAGES.record_artifact(receipts, "t64", 1, "video", v, "video_verified", beat=b)
    fx_silence_seed(receipts, "t64", 1, 1)
    # legacy fixtures as a pre-fingerprint run left them: intact files, NO fingerprints
    legacy = pr.RUN_DIR / "t64-s01-assembled.mp4"; synth_clip(legacy, secs=11, audio=True)
    STAGES.record_artifact(receipts, "t64", 1, "assemble", legacy, "assembled")
    legacy_ep = pr.RUN_DIR / "t64-edited.mp4"; synth_clip(legacy_ep, secs=11, audio=True)
    STAGES.record_artifact(receipts, "t64", 0, "edit", legacy_ep, "edited")
    receipts["stage_shots"]["t64:1"]["face_verdict"] = "not_readable"
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    def rec64():
        return json.loads((pr.RUN_DIR / "run-receipts.json").read_text())

    # (a) unfingerprinted assemble record: lineage unprovable -> invalidated, old file preserved
    # VERBATIM as a named backup, fresh rebuild from verified inputs records a real fingerprint
    legacy_bytes = legacy.read_bytes()
    code = run_main(["--stage", "assemble", "--only", "t64:1"])
    a = STAGES.get_artifact(rec64(), "t64", 1, "assemble")
    assert code == 2 and a["state"] == "assembled" and a.get("inputs_sha256"), (code, rec64().get("stopped"))
    assert Path(a["artifact"]).name == "t64-s01-assembled.mp4" and Path(a["artifact"]).exists()
    backups = list(pr.RUN_DIR.glob("t64-s01-assembled.stale-*.mp4"))
    assert len(backups) == 1 and backups[0].read_bytes() == legacy_bytes, backups
    # the unfingerprinted EDIT record was cascade-invalidated at the same moment
    e = STAGES.get_artifact(rec64(), "t64", 0, "edit")
    assert e["state"] == "edited_stale" and ".stale-" in e["artifact"] and Path(e["artifact"]).exists(), e
    assert not legacy_ep.exists()

    # rebuild the chain fresh: lipsync + edit; then an unchanged edit run SKIPS
    assert run_main(["--stage", "lipsync", "--only", "t64:1"]) == 2
    code = run_main(["--stage", "edit", "--only", "t64:1"])
    e2 = STAGES.get_artifact(rec64(), "t64", 0, "edit")
    assert code == 2 and e2["state"] == "edited" and e2.get("inputs_sha256"), (code, rec64().get("stopped"))
    canonical_ep = Path(e2["artifact"])
    assert run_main(["--stage", "edit", "--only", "t64:1"]) == 2  # unchanged -> skip path, no rebuild

    # (b) video regenerated WITHOUT re-assemble: the edit run itself invalidates its own
    # episode record (backup preserved, canonical cleared) BEFORE stopping on the stale chain
    v1 = pr.RUN_DIR / "t64-s01-b1.mp4"
    r = REAL_RUN(["ffmpeg","-y","-v","error","-f","lavfi","-i","testsrc=duration=2:size=320x240:rate=30",
                  "-f","lavfi","-i","sine=frequency=550:duration=2","-c:a","aac","-shortest",str(v1)],
                 capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-200:]
    receipts = rec64()
    STAGES.record_artifact(receipts, "t64", 1, "video", v1, "video_verified", beat=1)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--stage", "edit", "--only", "t64:1"])
    assert code == 2 and "not current" in rec64().get("stopped", ""), rec64().get("stopped")
    e3 = STAGES.get_artifact(rec64(), "t64", 0, "edit")
    assert e3["state"] == "edited_stale" and ".stale-" in e3["artifact"] and Path(e3["artifact"]).exists(), e3
    assert not canonical_ep.exists()  # stale episode file no longer at the canonical path

    # (c) legacy record + CHANGED inputs + a rebuild that FAILS: still invalidated first, backup kept
    receipts = rec64()
    receipts["stage_shots"]["t64:1"]["assemble"]["inputs_sha256"] = None  # simulate pre-fingerprint lineage again
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    shot3 = dict(shot); shot3["shot_s"] = 12.0
    shot3["beats"] = [dict(shot["beats"][0]), dict(shot["beats"][1], dur_s=10.0)]
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [shot3]}
    code = run_main(["--stage", "assemble", "--only", "t64:1"])
    assert code == 2 and "approved shot length" in rec64().get("stopped", ""), rec64().get("stopped")
    a5 = STAGES.get_artifact(rec64(), "t64", 1, "assemble")
    assert a5["state"] == "assembled_stale" and not a5.get("inputs_sha256"), a5
    assert ".stale-" in a5["artifact"] and Path(a5["artifact"]).exists()  # backup preserved through the FAILED rebuild
    pr.MANIFEST = orig
    print("T64 PASS: unfingerprinted records never blessed (backup preserved verbatim, fresh rebuild fingerprints); edited episode invalidates on upstream change/failure and on its own stale-chain stop; unchanged episode skips")

with tempfile.TemporaryDirectory() as tmp:  # T65: export gate - final-media freshness, source-zip labeling + hygiene
    import export_release as EX
    def run_export(argv):
        with mock.patch.object(sys, "argv", ["export_release.py"] + argv):
            try: EX.main()
            except SystemExit as e: return e.code
        return 0
    make_stage_env(tmp, "t65")
    orig = pr.MANIFEST
    shot = {"episode": "t65", "shot": 1, "shot_s": 11.0, "billing_s": 11.0, "line": "After.", "audio": "e01-l01-draconia.mp3",
            "speaker": "draconia", "dialogue_on_screen": True, "framing_class": "cu_dialogue", "audio_offset_s": 2.0,
            "beats": [{"id": 1, "dur_s": 2.0, "carries_line": False, "audio_intent": "sound_fx", "framing_class": "wide_action", "action": "crash"},
                      {"id": 2, "dur_s": 9.0, "carries_line": True, "audio_intent": "dialogue", "framing_class": "cu_dialogue", "action": "line"}]}
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [shot]}
    mpath = pr.RUN_DIR / "t65-manifest.json"
    mpath.write_text(json.dumps(pr.MANIFEST))
    receipts = {"shots": [], "charged_total": 0}
    for b, secs in ((1, 2), (2, 9)):
        v = pr.RUN_DIR / ("t65-s01-b%d.mp4" % b)
        synth_clip(v, secs=secs, audio=True)
        STAGES.record_artifact(receipts, "t65", 1, "video", v, "video_verified", beat=b)
    fx_silence_seed(receipts, "t65", 1, 1)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    def rec65():
        return json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    fargs = lambda od: ["--final-media", str(od), "--run-dir", str(pr.RUN_DIR), "--manifest-json", str(mpath)]

    # fresh chain exports; broken chain refuses and never touches a prior export
    assert run_main(["--stage", "assemble", "--only", "t65:1"]) == 2
    receipts = rec65()
    receipts["stage_shots"]["t65:1"]["face_verdict"] = "not_readable"
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    assert run_main(["--stage", "lipsync", "--only", "t65:1"]) == 2
    assert run_main(["--stage", "edit", "--only", "t65:1"]) == 2
    outdir = pr.RUN_DIR / "deliverable"
    assert run_export(fargs(outdir)) == 0
    ep_file = outdir / "t65-edited.mp4"
    man = json.loads((outdir / "MANIFEST.json").read_text())
    assert ep_file.exists() and man["episodes"][0]["sha256"] == STAGES.sha256_file(ep_file)
    assert man["freshness_verified_at_export"] is True and man["class"] == "final-media"
    assert sorted(p.name for p in outdir.iterdir()) == ["MANIFEST.json", "t65-edited.mp4"]  # no preview/stale passengers
    prior = ep_file.read_bytes()
    assert run_main(["--fx-undecide", "t65:1#b1", "--approval-ref", "main:t65-x"]) == 0
    assert run_main(["--stage", "assemble", "--only", "t65:1"]) == 2  # strict gate stops; chain now stale
    assert run_export(fargs(outdir)) == 2
    assert ep_file.read_bytes() == prior  # refused exports never modify the prior deliverable dir

    # restore the chain -> export OK again; manifest drift WITHOUT rebuild -> refused
    assert run_main(["--fx-silence", "t65:1#b1", "--approval-ref", "main:t65-y"]) == 0
    assert run_main(["--stage", "assemble", "--only", "t65:1"]) == 2
    assert run_main(["--stage", "lipsync", "--only", "t65:1"]) == 2
    assert run_main(["--stage", "edit", "--only", "t65:1"]) == 2
    assert run_export(fargs(outdir)) == 0
    shot2 = dict(shot); shot2["shot_s"] = 12.0
    shot2["beats"] = [dict(shot["beats"][0]), dict(shot["beats"][1], dur_s=10.0)]
    mpath2 = pr.RUN_DIR / "t65-manifest-12.json"
    mpath2.write_text(json.dumps({"fps_actual_verified": 30, "shots": [shot2]}))
    assert run_export(["--final-media", str(outdir), "--run-dir", str(pr.RUN_DIR), "--manifest-json", str(mpath2)]) == 2
    pr.MANIFEST = orig

    # source zip: builds with zero edited records required, labeled NOT PRODUCTION OUTPUT, no media/receipts/probe
    import zipfile as _zf
    zpath = Path(tmp) / "review.zip"
    assert run_export(["--source-zip", str(zpath), "--include-root", str(Path(__file__).resolve().parents[2])]) == 0
    zf = _zf.ZipFile(zpath)
    names = zf.namelist()
    assert "EXPORT-READER-NOTICE.txt" in names and "NOT PRODUCTION OUTPUT" in zf.read("EXPORT-READER-NOTICE.txt").decode()
    assert not [n for n in names if n.lower().endswith((".mp4", ".wav", ".mp3", ".zip"))
                or "receipt" in n.lower() or "probe-2" in n or "production-2" in n], "source zip leaked media/receipts/run dirs"
    # hygiene: planted personal email + private key refuse the archive
    bad = Path(tmp) / "tree"; bad.mkdir()
    (bad / "ok.py").write_text("x = 1\n")
    (bad / "leak.md").write_text("reach me at some.person" + "@realdomain" + ".com " + "-----BEGIN " + "PRIVATE KEY----- abc")  # literals split so the repo's own hygiene scan stays clean
    assert run_export(["--source-zip", str(Path(tmp) / "bad.zip"), "--include-root", str(bad)]) == 2
    assert not (Path(tmp) / "bad.zip").exists()
    print("T65 PASS: final-media export gated on a fresh verified chain (refusals never touch prior exports); source zip labeled NOT-PRODUCTION with no media/receipts/probe and hygiene-blocked on planted secrets")

with tempfile.TemporaryDirectory() as tmp:  # T66: crash-safe ledger writes + corrupt-ledger hard refusal
    make_stage_env(tmp, "t66")
    f = pr.RUN_DIR / "run-receipts.json"

    # corrupt ledger: refusal names the file, writes NOTHING, exits non-zero, bytes preserved verbatim
    f.write_text('{"shots": [truncated mid-write')
    before = f.read_bytes()
    try:
        pr._stage_receipts()
        raise AssertionError("corrupt ledger must refuse")
    except SystemExit as e:
        assert e.code == 2, e.code
    assert f.read_bytes() == before, "refusal must not overwrite the corrupt ledger"
    assert not list(pr.RUN_DIR.glob("*.tmp-*")), "no temp residue"

    # atomic write: a stop() leaves a parseable file and no temp fragments
    f.unlink()
    try:
        pr.stop("deliberate test stop", {"shots": [], "charged_total": 0})
        raise AssertionError("stop must exit")
    except SystemExit as e:
        assert e.code == 2
    assert json.loads(f.read_text())["stopped"] == "deliberate test stop"
    assert not list(pr.RUN_DIR.glob("*.tmp-*")), "stop() must not strand temp fragments"

    # serialization failure mid-write: pre-existing good file survives intact
    good = {"shots": [1], "charged_total": 5}
    pr._atomic_write_json(f, good)
    try:
        pr._atomic_write_json(f, {"bad": object()})
        raise AssertionError("unserializable must raise")
    except TypeError:
        pass
    assert json.loads(f.read_text()) == good, "failed write must not clobber the prior ledger"
    assert not list(pr.RUN_DIR.glob("*.tmp-*"))
    print("T66 PASS: corrupt ledger hard-refuses without writing (bytes preserved); stop() atomic + residue-free; failed serialization leaves prior ledger intact")

with tempfile.TemporaryDirectory() as tmp:  # T67: gate-fail honesty, no auto-reroll, explicit attributed retry
    stub = I2VStub(); make_env(tmp, "t67", stub); pr.RUN_DIR = Path(tmp) / "t67"
    receipts = {"shots": [], "charged_total": 0}
    record_s03_frames(receipts, "frame_accepted", pr.RUN_DIR)
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    ok_run = pr.subprocess.run
    def fail_run(cmd, capture_output=False, text=False):
        vdir = Path(cmd[4]); vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "verify.json").write_text(json.dumps({"video": {"r_frame_rate": "30/1"},
            "envelope_correlation": 0.21, "motion": {"near_static": 0, "sampled": 240},
            "audio_track": True, "asr_match": False, "asr_clip": "partial words", "asr_ref": "the full line"}))
        return types.SimpleNamespace(returncode=0, stderr="")
    pr.subprocess.run = fail_run
    # (a) gate fail: recorded gate_failed with the fails, never "verified"
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "gate_failed" in rec.get("stopped", ""), rec.get("stopped")
    fe = [x for x in rec["shots"] if x.get("stage") == "video" and x.get("state") == "gate_failed"]
    assert fe and fe[-1].get("gate_fails"), rec["shots"]
    assert not [x for x in rec["shots"] if x.get("state") == "verified" and x.get("gate_fails")], "conflicting verified+fails"
    # (b) rerun without --retry-shot: hard stop pre-POST
    p0 = stub.posts
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--only", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "NO automatic reroll" in rec.get("stopped", "") and "--retry-shot" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == p0, "no POST without explicit retry"
    # (c) --retry-shot under a main: ref refused - retry spends, spend authority is user-only
    code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "main:handoff-x", "--retry-shot", "e01:3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "REFUSED" in rec.get("stopped", ""), rec.get("stopped")
    assert stub.posts == p0
    # (d) --retry-shot + user wamid: fresh attempt submits, clean pass records verified
    pr.subprocess.run = ok_run
    # s03 sits under GATE_AFTER("e01",3): each clean beat stops for main inspection, one POST per run
    for beat_posts in (1, 2, 3):  # GATE_AFTER fires on every clean e01:3 verify, one beat POST per run
        code = run_main(["--stage", "video", "--approved-cap", str(CAP_E01S03), "--approval-ref", "[private-record-reference]", "--retry-shot", "e01:3"])
        rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
        assert code == 2 and "STOP GATE" in rec.get("stopped", ""), rec.get("stopped")
        assert stub.posts == p0 + beat_posts, (stub.posts, p0, beat_posts)
    verified = [x for x in rec["shots"] if x.get("stage") == "video" and x.get("state") == "verified"]
    assert verified and all(not x.get("gate_fails") for x in verified), "clean pass has no fails"
    # (e) --retry-shot with no recorded failure: refused (flag cannot widen scope)
    code = run_main(["--stage", "video", "--approved-cap", "960", "--approval-ref", "[private-record-reference]", "--retry-shot", "e01:5"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "no prior gate_failed" in rec.get("stopped", ""), rec.get("stopped")
    # (f) whole-shot resume: a gate_failed shot in the selection stops instead of silently resubmitting
    make_env(tmp, "t67b", StubNet()); pr.RUN_DIR = Path(tmp) / "t67b"
    receipts = {"shots": [{"ep": "e01", "shot": 5, "stage": "video", "state": "gate_failed",
                           "intended": 480, "charged": 480, "gate_fails": ["ASR delta"]}], "charged_total": 480}
    (pr.RUN_DIR / "run-receipts.json").write_text(json.dumps(receipts))
    code = run_main(["--legacy-t2v", "--approved-cap", "28896", "--approval-ref", "[private-record-reference]", "--resume", "--only", "e01:5"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "NO automatic reroll" in rec.get("stopped", ""), rec.get("stopped")
    print("T67 PASS: gate fails record gate_failed (never verified); no auto-reroll staged or whole-shot; retry needs --retry-shot + user wamid; scope-widening retry refused")

import subprocess as _bsp, importlib as _il
_il.reload(_bsp)  # earlier tests monkeypatched pr.subprocess (the shared stdlib module); restore the real run
def _run_builder():
    r = _bsp.run(["python3", "build_shot_manifest.py"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
    return r.stdout

with tempfile.TemporaryDirectory() as tmp:  # T68: builder preserves authored staging; take swaps drop + warn, never silently
    mp = Path("shot-manifest-wan30.json")
    good = mp.read_text()
    try:
        out = _run_builder()
        m = json.loads(mp.read_text())
        assert sum(1 for s in m["shots"] if s.get("beats")) == 50, "rebuild lost authored beats"
        assert "kept authored staging" in out and "e01 s16" in out, out  # authored 9.0s over formula preserved with an INFO note
        assert m["total_cr_staged"] == 34176 and m["total_cr"] == 28896, (m["total_cr_staged"], m["total_cr"])
        # take swap under authored beats -> WARNING + beats dropped for that shot only
        tam = json.loads(good)
        s3 = next(s for s in tam["shots"] if s["episode"] == "e02" and s["shot"] == 3)
        s3["audio"] = "e02-l02-draconia-RETAKE.mp3"
        mp.write_text(json.dumps(tam, indent=1))
        out = _run_builder()
        m = json.loads(mp.read_text())
        assert "WARNING: carried-over beats DROPPED" in out and "e02 s03" in out, out
        e02 = {s["shot"]: bool(s.get("beats")) for s in m["shots"] if s["episode"] == "e02"}
        assert e02[3] is False and all(v for k, v in e02.items() if k != 3), e02
        s3n = next(s for s in m["shots"] if s["episode"] == "e02" and s["shot"] == 3)
        assert s3n["audio"] == "e02-l02-draconia.mp3", s3n["audio"]  # canonical take from qa/scripts, not the tampered prior
    finally:
        mp.write_text(good)  # always restore the committed manifest
    print("T68 PASS: builder carries authored beats/offsets/shot lengths forward; take or line-dur moves drop + warn, never silently shrink")

with tempfile.TemporaryDirectory() as tmp:  # T69: fold-in lead-in validation - declared vs undeclared late line
    import stages as ST
    base = {"episode": "e02", "shot": 98, "shot_s": 5.0, "billing_s": 5, "line": "x",
            "audio": "e02-l10-harry.mp3", "speaker": "harry", "audio_offset_s": 0.8,
            "beats": [{"id": 1, "dur_s": 5.0, "framing_class": "cu_dialogue", "camera": "static",
                       "carries_line": True, "audio_intent": "dialogue", "lead_in_s": 0.8,
                       "action": "0-0.8s lead-in: the ice-grid flares underfoot. Then the line: he answers.",
                       "frame": {"refs": ["harry_front_close"], "prompt": "p"}}]}
    assert ST.validate_beats(base) is None  # declared lead-in: legal
    no_decl = json.loads(json.dumps(base)); del no_decl["beats"][0]["lead_in_s"]
    err = ST.validate_beats(no_decl); assert err and "lead_in_s" in err, err
    bad_mark = json.loads(json.dumps(base)); bad_mark["beats"][0]["action"] = "he answers."
    err = ST.validate_beats(bad_mark); assert err and "lead-in" in err, err
    mismatch = json.loads(json.dumps(base)); mismatch["beats"][0]["lead_in_s"] = 0.5
    err = ST.validate_beats(mismatch); assert err and "lead_in_s" in err, err
    # the old head-beat rule still holds: offset must equal the leading wordless total
    with_head = json.loads(json.dumps(base))
    with_head["beats"] = [{"id": 1, "dur_s": 0.5, "framing_class": "insert", "camera": "static",
                           "carries_line": False, "audio_intent": "sound_fx", "action": "w",
                           "frame": {"refs": [], "prompt": "p"}}] + with_head["beats"]
    with_head["beats"][1]["id"] = 2; del with_head["beats"][1]["lead_in_s"]; with_head["beats"][1]["dur_s"] = 4.5
    err = ST.validate_beats(with_head); assert err and "leading wordless" in err, err
    # variant artifact totals match the generator's claim
    import os
    if os.path.exists("shot-manifest-wan30.foldin.json"):
        v = json.load(open("shot-manifest-wan30.foldin.json"))
        assert v["total_cr_staged"] == 30144, v["total_cr_staged"]
        assert all(ST.validate_beats(s) is None for s in v["shots"])
    print("T69 PASS: fold-in lead-in requires explicit declaration (lead_in_s == offset + '0-<off>s lead-in:' action); head-beat rule unchanged; variant totals 30,144cr and validates")

with tempfile.TemporaryDirectory() as tmp:  # T70: frames stage --only ep:shot#bN generates exactly that beat's frame, never widens
    stub = StubNet(); make_env(tmp, "t70", stub); pr.RUN_DIR = Path(tmp) / "t70"
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t9","shot":1,"shot_s":4,"billing_s":4,"line":"Hi.","audio":"x.mp3","dialogue_on_screen":True,
         "framing_class":"cu_dialogue",
         "beats":[{"id":1,"dur_s":2,"carries_line":True,"audio_intent":"dialogue","framing_class":"cu_dialogue","frame":{"refs":[],"prompt":"a"}},
                  {"id":2,"dur_s":2,"carries_line":False,"audio_intent":"sound_fx","framing_class":"insert","frame":{"refs":[],"prompt":"b"}}]}]}
    code = run_main(["--stage","frames","--approved-cap","50","--approval-ref","[private-record-reference]","--only","t9:1"])
    assert code == 2 and stub.img_posts == 0  # whole-shot selection is 2 units = 100cr; cap 50 refused
    code = run_main(["--stage","frames","--approved-cap","50","--approval-ref","[private-record-reference]","--only","t9:1#b1"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert "batch done" in rec.get("stopped","") and stub.img_posts == 1, (rec.get("stopped"), stub.img_posts)
    assert [(e["beat"], e["intended"]) for e in rec["shots"]] == [(1, 50)], rec["shots"]
    assert STAGES.get_artifact(rec, "t9", 1, "frames", beat=1)["state"] == "frame_generated"
    assert STAGES.get_artifact(rec, "t9", 1, "frames", beat=2) is None
    code = run_main(["--stage","frames","--approved-cap","50","--approval-ref","[private-record-reference]","--only","t9:1#b3"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "no frame unit" in rec.get("stopped","") and stub.img_posts == 1  # unknown beat: refuse, no widening
    pr.MANIFEST = orig
    print("T70 PASS: frames stage beat selection - #b1 = exactly one 50cr image job, shot-level cap mismatch refused, unknown beat refused without widening")

with tempfile.TemporaryDirectory() as tmp:  # T71: --reject-frame records attributed rejection with reasons; rejected frame can't be accepted or consumed
    stub = StubNet(); make_env(tmp, "t71", stub); pr.RUN_DIR = Path(tmp) / "t71"
    orig = pr.MANIFEST
    pr.MANIFEST = {"fps_actual_verified": 30, "shots": [
        {"episode":"t9","shot":1,"shot_s":4,"billing_s":4,"line":"Hi.","audio":"x.mp3","dialogue_on_screen":True,
         "framing_class":"cu_dialogue",
         "beats":[{"id":1,"dur_s":2,"carries_line":True,"audio_intent":"dialogue","framing_class":"cu_dialogue","frame":{"refs":[],"prompt":"a"}},
                  {"id":2,"dur_s":2,"carries_line":False,"audio_intent":"sound_fx","framing_class":"insert","frame":{"refs":[],"prompt":"b"}}]}]}
    run_main(["--stage","frames","--approved-cap","50","--approval-ref","[private-record-reference]","--only","t9:1#b1"])
    code = run_main(["--reject-frame","t9:1#b1","--approval-ref","main:T71"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "--reason" in rec.get("stopped","")  # no reason, refused
    code = run_main(["--reject-frame","t9:1#b1","--approval-ref","main:T71","--reason","wrong-actor gesture; no post-spin motion"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    fr = STAGES.get_artifact(rec, "t9", 1, "frames", beat=1)
    assert fr["state"] == "frame_rejected" and fr["acceptance_actor"] == "main" and "wrong-actor" in fr["rejection_reason"], fr
    code = run_main(["--accept-frame","t9:1#b1","--approval-ref","main:T71"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and "no frame_generated" in rec.get("stopped","")  # rejected can't flip to accepted
    code = run_main(["--stage","video","--approved-cap","192","--approval-ref","[private-record-reference]","--only","t9:1"])
    rec = json.loads((pr.RUN_DIR / "run-receipts.json").read_text())
    assert code == 2 and stub.posts == 0  # video stage refuses without an ACCEPTED frame
    pr.MANIFEST = orig
    print("T71 PASS: reject-frame needs main ref + concrete reason; rejected frame preserved, can't be accepted, video stage blocked")

# T72: beat-complexity linter - detects the empirically observed frame-failure class and
# guards the manifest: no beat may carry the overloaded-binding risk profile that failed twice on s14 b1.
import beat_complexity as bc
OLD_S14_B1 = ("Candlelit Yule Ball Great Hall from the location reference. Close two-shot: the "
 "platinum-blonde woman in the green embroidered gown turned toward the black-haired boy in black "
 "red-lined dress robes over a white shirt and dark necktie, incredulous, a faint shield-charm shimmer "
 "fading around her, his wand still raised from the redirected spell, jabbing a finger upward, mouth "
 "clearly visible mid-speech; both faces readable. Identical faces, hair, wardrobe to the references. "
 "Photorealistic, cinematic candlelight.")
a = bc.analyze_prompt(OLD_S14_B1)
ids = {f[0] for f in a["flags"]}
assert a["risk"] == "high" and {"R1", "R3", "R4", "R5"} <= ids, a  # the twice-failed wording must read high
NEW_S14_B1 = next(s for s in pr.MANIFEST["shots"] if s["episode"] == "e01" and s["shot"] == 14)["beats"][0]["frame"]["prompt"]
a2 = bc.analyze_prompt(NEW_S14_B1)
assert a2["risk"] == "clean" and a2["actor_verbs"].get("draconia") == ["jab"] and not a2["actor_verbs"].get("harry"), a2
ins = next(s for s in pr.MANIFEST["shots"] if s["episode"] == "e01" and s["shot"] == 14)["beats"][1]["frame"]["prompt"]
assert bc.analyze_prompt(ins)["risk"] in ("clean", "watch"), ins  # single-event no-people insert is fine
amb = bc.analyze_prompt("The black-haired boy in black red-lined dress robes beside the platinum-blonde woman in the green embroidered gown, his wand raised, jabbing a finger upward.")
assert any(f[0] == "R3" for f in amb["flags"]), amb  # dangling action near a male mention = migration risk
one = bc.analyze_prompt("Close on the platinum-blonde woman in the green embroidered gown, rising from a duck with a laughing grin, mouth clearly visible mid-speech.")
assert not any(f[0] == "R3" for f in one["flags"]), one  # one actor on screen: dangling verbs can only bind to her
for mp in ("shot-manifest-wan30.json", "shot-manifest-wan30.foldin.json"):
    high = [r["shot"] for r in bc.census(str(ROOT / mp)) if r["risk"] == "high"]
    assert not high, (mp, high)  # manifest guard: zero overloaded-binding beats
print("T72 PASS: linter isolates the twice-failed s14 b1 class; new staging clean; manifests carry zero high-risk beats")
