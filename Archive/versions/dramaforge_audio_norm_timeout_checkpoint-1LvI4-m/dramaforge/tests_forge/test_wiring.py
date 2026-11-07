"""m11 wiring tests: new modules called from existing pipeline files,
old behaviour preserved when the new artifacts are absent."""
import json
import pytest
from pathlib import Path

from forge.gates import GateLocked, lock_stills, record_proof, signoff_proof
from forge.gates.enforce import enforce_render_allowed, DEFAULT_PLAN
from forge.gates.proof_checklist import ITEMS, start_checklist, check_item
from forge.script_run import write_plan_and_lint


def _img(path, colour):
    from PIL import Image
    Image.new("RGB", (64, 64), colour).save(path)
    return str(path)


SCRIPT_SHOTS = [
    {"n": 1, "location": "kitchens", "camera": "wide", "action": "she enters", "seconds": 10,
     "lines": [{"speaker": "Harry", "text": "word " * 20},
               {"speaker": "Draconia", "text": "word " * 20}]},
    {"n": 2, "location": "kitchens", "camera": "close", "action": "he sits", "seconds": 8,
     "lines": [{"speaker": "Harry", "text": "word " * 18}]},
]

FULL_STILLS = None  # built per-test with tmp paths


def _full_lock(tmp_path):
    stills = {
        "character:Harry:angle:front": _img(tmp_path / "hf.png", (120, 60, 40)),
        "character:Harry:angle:closeup": _img(tmp_path / "hc.png", (120, 60, 40)),
        "character:Draconia:angle:reverse": _img(tmp_path / "dr.png", (30, 30, 90)),
        "location:kitchens": _img(tmp_path / "kit.png", (70, 70, 70)),
    }
    lock_stills(tmp_path, stills)
    return stills


# --- old behaviour preserved ------------------------------------------------

def test_old_flow_unchanged_without_plan(tmp_path):
    """No plan file, no checklist: gates behave exactly as m10b."""
    lock_stills(tmp_path, {"character:harry": _img(tmp_path / "h.png", (1, 2, 3))})
    enforce_render_allowed(tmp_path, "proof")  # still lock only, as before
    with pytest.raises(GateLocked, match="proof scene"):
        enforce_render_allowed(tmp_path, "episode")


def test_bad_mode_still_rejected(tmp_path):
    lock_stills(tmp_path, {"character:harry": _img(tmp_path / "h.png", (1, 2, 3))})
    with pytest.raises(GateLocked, match="unknown render mode"):
        enforce_render_allowed(tmp_path, "surprise")


# --- script stage writes the plan and lint ----------------------------------

def test_write_plan_and_lint_outputs(tmp_path):
    res = write_plan_and_lint(SCRIPT_SHOTS, outdir=tmp_path / "out")
    plan = json.loads((tmp_path / "out" / "e01_plan.json").read_text())
    lint = json.loads((tmp_path / "out" / "e01_action_lint.json").read_text())
    assert len(plan) == len(res["plan"]) >= 3  # shot 1 split per speaker
    assert all(p.get("line") is None or p["line"]["speaker"] == p["speaker"] for p in plan)
    assert "plan_summary" in lint and lint["n_shots"] == 2


# --- plan file activates the angle-still gate --------------------------------

def test_plan_file_blocks_render_until_angles_locked(tmp_path):
    lock_stills(tmp_path, {"character:harry": _img(tmp_path / "h.png", (1, 2, 3))})
    write_plan_and_lint(SCRIPT_SHOTS, outdir=tmp_path / "out")  # plan at DEFAULT_PLAN location
    assert (tmp_path / DEFAULT_PLAN).exists()
    with pytest.raises(GateLocked, match="missing required stills"):
        enforce_render_allowed(tmp_path, "proof")


def test_plan_file_passes_with_full_coverage(tmp_path):
    _full_lock(tmp_path)
    write_plan_and_lint(SCRIPT_SHOTS, outdir=tmp_path / "out")
    enforce_render_allowed(tmp_path, "proof")  # no raise: plan found and covered


def test_explicit_planned_shots_arg(tmp_path):
    lock_stills(tmp_path, {"character:harry": _img(tmp_path / "h.png", (1, 2, 3))})
    plan = [{"speaker": "harry", "camera": "single:harry", "location": "kitchens"}]
    with pytest.raises(GateLocked, match="missing required stills"):
        enforce_render_allowed(tmp_path, "proof", planned_shots=plan)


# --- checklist opt-in for episode renders -------------------------------------

def _approved_proof(tmp_path):
    v = tmp_path / "proof.mp4"
    v.write_bytes(b"proof-bytes")
    record_proof(tmp_path, str(v), n_shots=3, seconds=20, locations=["kitchens"])
    signoff_proof(tmp_path, "reviewer")


def test_episode_blocked_by_incomplete_checklist(tmp_path):
    _full_lock(tmp_path)
    _approved_proof(tmp_path)
    start_checklist(tmp_path)  # opted in, nothing checked
    with pytest.raises(GateLocked, match="incomplete"):
        enforce_render_allowed(tmp_path, "episode")


def test_episode_passes_with_complete_checklist(tmp_path):
    _full_lock(tmp_path)
    _approved_proof(tmp_path)
    start_checklist(tmp_path)
    for item in ITEMS:
        check_item(tmp_path, item, "reviewer")
    enforce_render_allowed(tmp_path, "episode")  # no raise


def test_episode_without_checklist_keeps_old_flow(tmp_path):
    lock_stills(tmp_path, {"character:harry": _img(tmp_path / "h.png", (1, 2, 3))})
    _approved_proof(tmp_path)
    enforce_render_allowed(tmp_path, "episode")  # no checklist file: m10b behaviour


# --- compose hierarchy helper -------------------------------------------------

def test_burn_caption_hierarchy_writes_ass_and_burns(tmp_path, monkeypatch):
    import forge.assemble.compose as compose
    calls = {}
    def fake_run(cmd, check):
        calls["cmd"] = cmd
        return None
    monkeypatch.setattr(compose.subprocess, "run", fake_run)
    out = compose.burn_caption_hierarchy(
        "in.mp4", [{"word": "hi", "start": 0.0, "end": 0.4}],
        [{"text": "hook", "start": 0.0, "end": 3.0, "kind": "hook"}],
        str(tmp_path / "out.mp4"), ass_path=str(tmp_path / "cap.ass"))
    text = (tmp_path / "cap.ass").read_text()
    assert "Hook" in text and "Dialogue" in text
    assert any("ass=" in str(c) for c in calls["cmd"])
    assert out.endswith("out.mp4")


# --- action-lint blocks episode renders once a lint report exists -----------

def test_episode_blocked_by_flagged_lint(tmp_path):
    lock_stills(tmp_path, {  # satisfy the angle gate so the lint gate is what fires
        # (a one-line shot is planned as 'single:<speaker>' -> angle class 'front')
        "character:Harry:angle:front": _img(tmp_path / "hw.png", (1, 2, 3)),
        "location:corridor": _img(tmp_path / "cor.png", (4, 5, 6))})
    _approved_proof(tmp_path)
    overloaded = [{"n": 9, "location": "corridor", "camera": "wide", "seconds": 10,
                   "action": "He storms in, crosses the room, grabs the letter and slams the door.",
                   "lines": [{"speaker": "Harry", "text": "word " * 10}]}]
    write_plan_and_lint(overloaded, outdir=tmp_path / "out")
    with pytest.raises(GateLocked, match="action-budget lint flags shots"):
        enforce_render_allowed(tmp_path, "episode")


def test_proof_render_exempt_from_lint_block(tmp_path):
    lock_stills(tmp_path, {"character:harry": _img(tmp_path / "h.png", (1, 2, 3))})
    overloaded = [{"n": 9, "location": "corridor", "camera": "wide", "seconds": 10,
                   "action": "He storms in, crosses the room, grabs the letter and slams the door.",
                   "lines": [{"speaker": "Harry", "text": "word " * 10}]}]
    write_plan_and_lint(overloaded, outdir=tmp_path / "out")
    # proof mode: angle-still gate applies (plan exists) but lint must not block
    with pytest.raises(GateLocked, match="missing required stills"):
        enforce_render_allowed(tmp_path, "proof")


def test_clean_lint_does_not_block(tmp_path):
    lock_stills(tmp_path, {
        "character:harry:angle:front": _img(tmp_path / "hw.png", (1, 2, 3)),
        "location:kitchens": _img(tmp_path / "kit.png", (70, 70, 70))})
    _approved_proof(tmp_path)
    calm = [{"n": 1, "location": "kitchens", "camera": "wide", "action": "she sits", "seconds": 8,
             "lines": [{"speaker": "harry", "text": "word " * 20}]}]
    write_plan_and_lint(calm, outdir=tmp_path / "out")
    enforce_render_allowed(tmp_path, "episode")
