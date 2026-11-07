"""m17/m18 stress and bulletproof coverage: adversarial inputs, boundary
shapes, and one integrated end-to-end local flow across the stage log,
design bible, story arc, motion anchor and platform-safe captions."""
import json
import os

import cv2
import numpy as np
import pytest

from forge.gates.common import GateLocked


def _clip(path, frames=8, color=(30, 50, 80)):
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 64))
    for _ in range(frames):
        w.write(np.full((64, 64, 3), color, np.uint8))
    w.release()
    return str(path)


def test_stage_log_corrupt_sidecar_and_repeat_records(tmp_path):
    from forge.assemble import stage_log
    v = _clip(tmp_path / "a.mp4")
    # corrupt sidecar => treated as unknown, never a crash or a false clean
    with open(v + ".stages.json", "w") as fh:
        fh.write("{not json")
    assert stage_log.stages_of(v) == []
    from forge.assemble.lipsync import lipsync_job
    front = lambda frame: [{"landmarks": _lm_stub(), "box": (0, 0, 30, 30)}]
    job = lipsync_job(v, "a.wav", "o.mp4", detect_fn=front)
    assert job["provenance"] == "corrupt"  # never a false "recorded"
    # repeated records stay deduped; SYNCED clears PLANNED exactly once
    stage_log.record(v, stage_log.PLANNED)
    stage_log.record(v, stage_log.PLANNED)
    stage_log.record(v, stage_log.SYNCED)
    stage_log.record(v, stage_log.SYNCED)
    assert stage_log.stages_of(v) == [stage_log.SYNCED]


def _lm_stub():
    import numpy as _np
    lm = _np.zeros((478, 2))
    lm[1] = (50, 50); lm[33] = (40, 50); lm[263] = (60, 50)
    return lm


def test_copy_with_overwrite_replaces_stale_sidecar(tmp_path):
    from forge.assemble import stage_log
    src_v = _clip(tmp_path / "s.mp4")
    stage_log.record(src_v, stage_log.SYNCED)
    dst = _clip(tmp_path / "d.mp4")
    stage_log.record(dst, stage_log.CAPTIONS)  # stale conflicting provenance
    assert stage_log.copy_with(src_v, dst) == "recorded"
    assert stage_log.stages_of(dst) == [stage_log.SYNCED]  # replaced, not merged


def test_lipsync_cli_refuses_captioned_input_rc3(tmp_path):
    from forge.assemble import stage_log
    from forge.assemble.lipsync import main
    v = _clip(tmp_path / "c.mp4")
    stage_log.record(v, stage_log.CAPTIONS, strict=True)
    assert main([v, "a.wav", "--out", "o.mp4", "--detector", "none"]) == 3


def test_coverage_gate_boundaries(tmp_path):
    from forge.planning.design_prep import (asset_sheet, build_design_bible,
                                            location_sheet,
                                            validate_design_coverage)
    bible = build_design_bible(
        assets=[asset_sheet(f"char{i}", "character", f"look {i}") for i in range(40)],
        locations=[location_sheet("Balcony", "roof")])
    # empty plan passes vacuously; large bible fine
    assert validate_design_coverage([], bible)["checked"] == 0
    big = [{"plan_n": i, "location": "Balcony", "speaker": f"char{i % 40}",
            "line": {"speaker": f"char{i % 40}", "text": "x"}} for i in range(120)]
    assert validate_design_coverage(big, bible)["checked"] == 120
    # case mismatch is a miss - strict matching is deliberate (drift guard)
    with pytest.raises(GateLocked, match="balcony"):
        validate_design_coverage(
            [{"plan_n": 1, "location": "balcony", "speaker": "char0",
              "line": {"speaker": "char0", "text": "x"}}], bible)


def test_plate_no_cuts_and_unreadable(tmp_path):
    from forge.planning.design_prep import (DesignError, plate_cut_times,
                                            shots_from_plate)
    flat = _clip(tmp_path / "flat.mp4", frames=30)  # single colour, no cuts
    assert plate_cut_times(flat) == []
    shots = shots_from_plate(flat, location="Studio")
    assert len(shots) == 1 and shots[0]["seconds"] > 0  # whole-plate fallback
    with pytest.raises(DesignError):
        shots_from_plate(str(tmp_path / "missing.mp4"))


def test_story_arc_edge_shapes():
    from forge.planning.story_arc import lint_arc
    one = lint_arc([{"n": 1}])
    assert one["beats"] == ["setup"] and "payoff" in one["missing"]
    two = lint_arc([{"n": 1}, {"n": 2}])
    assert two["beats"] == ["setup", "payoff"] and "reveal" in two["missing"]
    many = lint_arc([{"n": i} for i in range(100)])
    assert many["ok"] and many["beats"][0] == "setup" and many["beats"][-1] == "payoff"


def test_design_prep_cli_missing_plan_is_clean_refusal(tmp_path):
    from forge.planning.design_prep import main, save_bible
    save_bible(str(tmp_path), {"locations": [{"name": "A", "description": "place"}]})
    assert main(["validate", str(tmp_path)]) == 3  # no traceback, exit 3


def test_integrated_local_flow(tmp_path):
    """End-to-end local: bible -> gated plan write -> arc/continuity lint ->
    render jobs with motion anchor -> dry_run manifest -> assemble vertical
    with platform-safe captions -> provenance chain -> re-sync refused."""
    from forge.assemble import stage_log
    from forge.assemble.compose import compose, burn_speaker_captions
    from forge.assemble.lipsync import lipsync_job
    from forge.planning.design_prep import (attach_motion_anchor, save_bible)
    from forge.render_plan import build_render_jobs, dry_run
    from forge.script_run import write_plan_and_lint

    proj = tmp_path / "proj"
    proj.mkdir()
    save_bible(str(proj), {
        "assets": [{"name": "Aiden", "kind": "character",
                    "description": "black hair, grey uniform"}],
        "locations": [{"name": "Balcony", "description": "rooftop at night"}]})
    shots = [{"n": 1, "location": "Balcony", "camera": "wide", "action": "waits",
              "seconds": 6, "beat": "setup",
              "lines": [{"speaker": "Aiden", "text": "She actually came."}]},
             {"n": 2, "location": "Balcony", "camera": "close", "action": "smiles",
              "seconds": 6, "beat": "payoff",
              "lines": [{"speaker": "Aiden", "text": "Pink. You remembered."}]}]
    res = write_plan_and_lint(shots, outdir=proj / "out")
    assert res["lint"]["story_arc"]["missing"] == ["reveal"]  # honest report
    assert res["lint"]["character_continuity"]["characters"]["Aiden"]["shots"] >= 1

    # motion anchor flows into jobs + manifest
    plate = _clip(proj / "plate.mp4", frames=20)
    plan_path = proj / "out" / "e01_plan.json"
    plan = json.loads(plan_path.read_text())
    plan[0] = attach_motion_anchor(plan[0], plate)
    plan_path.write_text(json.dumps(plan))
    jobs = build_render_jobs(str(proj))
    assert jobs[0]["motion_source"]["path"] == os.path.abspath(plate)
    manifest = dry_run(str(proj))
    assert manifest["n_jobs"] == len(jobs) and manifest["credits_est_total"] >= 0

    # assemble: provenance inherits, captions land above platform zone
    clip = _clip(proj / "shot1.mp4", frames=15)
    stage_log.record(clip, stage_log.SYNCED)  # a completed sync from the GPU host
    out = str(proj / "ep.mp4")
    compose([clip], None, None, out,
            speaker_segments=[{"speaker": "Aiden", "text": "hi", "start": 0, "end": 1}],
            caption_platform="instagram_reels")
    assert os.path.exists(out)
    stages = stage_log.stages_of(out)
    assert stage_log.CAPTIONS in stages and stage_log.SYNCED in stages
    ass = open(out + ".speaker.ass").read()
    assert ",10,10,400,1" in ass
    # the captioned episode can never be lip-synced afterwards
    with pytest.raises(GateLocked, match="pre-caption"):
        lipsync_job(out, "a.wav", "o2.mp4", detect_fn=lambda f: [])
