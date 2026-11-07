"""Plan-driven rendering tests: the plan is the render list. Free paths only."""
import json
import pytest

from forge.gates import GateLocked, lock_stills
from forge.gates.common import state_dir, read_json
from forge.render_plan import build_render_jobs, dry_run, default_prompt
from forge.script_run import write_plan_and_lint

SCRIPT_SHOTS = [
    {"n": 1, "location": "kitchens", "camera": "wide", "action": "she enters", "seconds": 10,
     "lines": [{"speaker": "Harry", "text": "Your office closed at six, and I waited?"},
               {"speaker": "Draconia", "text": "Harry, please, let me explain this properly now."}]},
]


def _img(path, colour):
    from PIL import Image
    Image.new("RGB", (64, 64), colour).save(path)
    return str(path)


def _planned(tmp_path):
    write_plan_and_lint(SCRIPT_SHOTS, outdir=tmp_path / "out")
    return tmp_path


def test_no_plan_is_a_gate_error(tmp_path):
    with pytest.raises(GateLocked, match="no shot plan"):
        build_render_jobs(tmp_path)


def test_one_job_per_planned_clip(tmp_path):
    _planned(tmp_path)
    jobs = build_render_jobs(tmp_path)
    plan = json.loads((tmp_path / "out" / "e01_plan.json").read_text())
    assert [j["plan_n"] for j in jobs] == [p["plan_n"] for p in plan]
    # the question line earns a reaction clip; every speaker job names its still
    kinds = [j["kind"] for j in jobs]
    assert "reaction" in kinds
    for j in jobs:
        if j["speaker"]:
            assert j["reference_still"].startswith(f"character:{j['speaker']}:angle:")
    reaction = next(j for j in jobs if j["kind"] == "reaction")
    assert reaction["silent"] and "reacting without speaking" in reaction["prompt"]


def test_dry_run_manifest_estimates_and_blocks(tmp_path):
    _planned(tmp_path)
    lock_stills(tmp_path, {  # cover Harry's front angle only
        "character:Harry:angle:front": _img(tmp_path / "hf.png", (120, 60, 40))})
    m = dry_run(tmp_path, credits_per_second=10)
    assert (state_dir(tmp_path) / "render_manifest.json").exists()
    assert m["credits_est_total"] == sum(j["credits_est"] for j in m["jobs"])
    assert not m["ready"] and m["blocked_jobs"]  # missing Draconia reverse + closeup + location
    harry_front = next(j for j in m["jobs"]
                       if j["reference_still"] == "character:Harry:angle:front")
    assert harry_front["still_present"]


def test_dry_run_ready_when_all_stills_locked(tmp_path):
    _planned(tmp_path)
    lock_stills(tmp_path, {
        "character:Harry:angle:front": _img(tmp_path / "hf.png", (120, 60, 40)),
        "character:Harry:angle:closeup": _img(tmp_path / "hc.png", (120, 60, 40)),
        "character:Draconia:angle:reverse": _img(tmp_path / "dr.png", (30, 30, 90)),
        "character:Draconia:angle:closeup": _img(tmp_path / "dc.png", (30, 30, 90)),
        "location:kitchens": _img(tmp_path / "kit.png", (70, 70, 70))})
    m = dry_run(tmp_path)
    assert m["ready"] and m["blocked_jobs"] == []


def test_execute_refuses_without_stills(tmp_path):
    import asyncio
    _planned(tmp_path)  # no stills locked at all
    with pytest.raises(GateLocked, match="lack locked stills"):
        asyncio.run(_execute(tmp_path))


async def _execute(tmp_path):
    from forge.render_plan import execute_plan
    return await execute_plan(tmp_path, generator=None)


def test_default_prompt_is_restrained():
    p = default_prompt({"kind": "speaker", "speaker": "Harry", "camera": "over_shoulder:Harry",
                        "location": "kitchens", "action": "he sits",
                        "line": {"text": "One line only."}})
    assert "Action (only this): he sits" in p and '"One line only."' in p
