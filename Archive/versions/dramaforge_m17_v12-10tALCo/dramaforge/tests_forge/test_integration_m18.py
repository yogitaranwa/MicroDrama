"""m18: pre-production design discipline (asset design sheets, per-scene
location sheets, real-footage motion anchors) - applied from the reviewed
shoot-then-transform creator breakdown. Free/local only; fail-closed gates,
nothing invented."""
import os

import cv2
import numpy as np
import pytest

from forge.gates.common import GateLocked
from forge.planning.design_prep import (DesignError, asset_sheet,
                                        attach_motion_anchor,
                                        build_design_bible, location_sheet,
                                        plate_cut_times, shots_from_plate,
                                        validate_design_coverage)


def _plate(path, segments=((0, 0, 0), (255, 255, 255)), frames_each=15):
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 64))
    for color in segments:
        for _ in range(frames_each):
            w.write(np.full((64, 64, 3), color, np.uint8))
    w.release()
    return str(path)


def test_asset_and_location_sheets_are_validated():
    sheet = asset_sheet("Aiden", "character",
                        "young wizard, sharp jaw, black slicked hair, grey uniform")
    assert sheet["kind"] == "character"
    loc = location_sheet("Balcony", "rooftop balcony above the city",
                         key_features=["railing", "string lights"],
                         time_of_day="night")
    assert loc["key_features"] == ["railing", "string lights"]
    with pytest.raises(DesignError):
        asset_sheet("Aiden", "wizard", "desc")  # unknown kind
    with pytest.raises(DesignError):
        asset_sheet("Aiden", "character", "   ")  # empty design
    with pytest.raises(DesignError):
        location_sheet("", "desc")


def test_design_bible_rejects_duplicates():
    a = asset_sheet("Aiden", "character", "look one")
    a2 = asset_sheet("Aiden", "character", "look two")
    with pytest.raises(DesignError, match="duplicate"):
        build_design_bible(assets=[a, a2])


def test_coverage_gate_blocks_undesigned_plan():
    bible = build_design_bible(
        assets=[asset_sheet("Aiden", "character", "black hair, grey uniform")],
        locations=[location_sheet("Balcony", "rooftop at night")])
    plan = [
        {"plan_n": 1, "location": "Balcony", "speaker": "Aiden",
         "line": {"speaker": "Aiden", "text": "hi"}, "assets": ["Rose"]},
        {"plan_n": 2, "location": "Fridge", "speaker": "Mal"},
    ]
    with pytest.raises(GateLocked) as exc:
        validate_design_coverage(plan, bible)
    msg = str(exc.value)
    assert "no design sheet for asset 'Rose'" in msg
    assert "no location sheet for 'Fridge'" in msg
    assert "no character design sheet for 'Mal'" in msg
    ok = validate_design_coverage(
        [{"plan_n": 1, "location": "Balcony", "speaker": "Aiden",
          "line": {"speaker": "Aiden", "text": "hi"}}], bible)
    assert ok == {"checked": 1, "missing": []}


def test_motion_anchor_validation(tmp_path):
    plate = _plate(tmp_path / "plate.mp4")
    shot = attach_motion_anchor({"kind": "visual", "location": "Street"}, plate)
    assert shot["motion_source"]["role"].startswith("camera movement")
    assert os.path.isabs(shot["motion_source"]["path"])
    with pytest.raises(DesignError, match="not a video"):
        attach_motion_anchor({}, str(tmp_path / "x.txt"))
    with pytest.raises(DesignError, match="missing or empty"):
        attach_motion_anchor({}, str(tmp_path / "nope.mp4"))


def test_plate_cuts_drive_shot_skeletons(tmp_path):
    plate = _plate(tmp_path / "plate.mp4", segments=((0, 0, 0), (255, 255, 255)),
                   frames_each=15)
    cuts = plate_cut_times(plate)
    assert len(cuts) >= 1 and 0.5 < cuts[0] < 2.5  # the hard cut at ~1.5s
    shots = shots_from_plate(plate, location="Street")
    assert len(shots) >= 2
    assert all(s["motion_source"]["path"] == os.path.abspath(plate) for s in shots)
    assert all(s["seconds"] > 0 for s in shots)
    assert sum(s["seconds"] for s in shots) > 2.0


def test_director_prompt_carries_motion_anchor(tmp_path):
    from forge.planning.director import director_prompt
    plate = _plate(tmp_path / "plate.mp4")
    shot = attach_motion_anchor(
        {"kind": "visual", "location": "Street", "camera": "wide",
         "action": "crowd crosses"}, plate)
    prompt = director_prompt(shot)
    assert "MOTION ANCHOR" in prompt and plate in prompt
    plain = director_prompt({"kind": "visual", "location": "Street",
                             "camera": "wide", "action": "crowd crosses"})
    # empty optional sections keep the module's existing header style
    assert "plate.mp4" not in plain and "reference plate" not in plain


def test_render_jobs_carry_motion_source(tmp_path):
    import json
    from forge.render_plan import build_render_jobs
    plate = _plate(tmp_path / "plate.mp4")
    proj = tmp_path / "proj"
    (proj / "out").mkdir(parents=True)
    shot = attach_motion_anchor(
        {"plan_n": 1, "kind": "visual", "location": "Street",
         "camera": "wide", "action": "crowd crosses", "seconds": 2.0}, plate)
    (proj / "out" / "e01_plan.json").write_text(json.dumps([shot]))
    jobs = build_render_jobs(str(proj))
    assert jobs[0]["motion_source"]["path"] == os.path.abspath(plate)


def _bible_doc():
    return {"style": "cinematic",
            "assets": [{"name": "Aiden", "kind": "character",
                        "description": "black slicked hair, grey uniform"}],
            "locations": [{"name": "Balcony",
                           "description": "rooftop balcony above the city",
                           "key_features": ["railing"], "time_of_day": "night"}]}


def test_bible_roundtrip_and_plan_gate_at_script_stage(tmp_path):
    """The real script-stage path: with a bible installed, write_plan_and_lint
    refuses an undesigned plan and accepts a fully designed one."""
    from forge.planning.design_prep import save_bible
    from forge.script_run import write_plan_and_lint

    save_bible(str(tmp_path), _bible_doc())
    bad = [{"n": 1, "location": "Fridge", "camera": "wide", "action": "glares",
            "seconds": 6, "lines": [{"speaker": "Mal", "text": "why"}]}]
    with pytest.raises(GateLocked, match="location sheet"):
        write_plan_and_lint(bad, outdir=tmp_path / "out")
    assert not (tmp_path / "out" / "e01_plan.json").exists()
    good = [{"n": 1, "location": "Balcony", "camera": "wide", "action": "smiles",
             "seconds": 6, "lines": [{"speaker": "Aiden", "text": "hi there"}]}]
    res = write_plan_and_lint(good, outdir=tmp_path / "out")
    assert (tmp_path / "out" / "e01_plan.json").exists()
    assert res["plan"]


def test_render_jobs_blocked_by_installed_bible(tmp_path):
    """The render funnel enforces the same bible before any spend."""
    import json
    from forge.planning.design_prep import save_bible
    from forge.render_plan import build_render_jobs
    save_bible(str(tmp_path), _bible_doc())
    (tmp_path / "out").mkdir(exist_ok=True)
    plan = [{"plan_n": 1, "kind": "speaker", "location": "Fridge",
             "speaker": "Aiden", "camera": "wide", "action": "talks",
             "line": {"speaker": "Aiden", "text": "hi"}, "seconds": 5}]
    (tmp_path / "out" / "e01_plan.json").write_text(json.dumps(plan))
    with pytest.raises(GateLocked, match="location sheet"):
        build_render_jobs(str(tmp_path))
    plan[0]["location"] = "Balcony"
    (tmp_path / "out" / "e01_plan.json").write_text(json.dumps(plan))
    jobs = build_render_jobs(str(tmp_path))
    assert len(jobs) == 1 and jobs[0]["plan_n"] == 1


def test_malformed_bible_fails_closed(tmp_path):
    from forge.planning.design_prep import load_bible, save_bible
    with pytest.raises(GateLocked, match="malformed"):
        save_bible(str(tmp_path), {"assets": [{"name": "X"}]})
    (tmp_path / ".forge").mkdir(exist_ok=True)
    (tmp_path / ".forge" / "design_bible.json").write_text('{"assets": 42}')
    with pytest.raises(GateLocked, match="malformed"):
        load_bible(str(tmp_path))


def test_design_prep_cli(tmp_path):
    """The user-facing entry path: save-bible, validate (blocked + ok),
    cuts, skeleton."""
    import json
    from forge.planning.design_prep import main
    doc = tmp_path / "bible.json"
    doc.write_text(json.dumps(_bible_doc()))
    assert main(["save-bible", str(tmp_path), str(doc)]) == 0
    assert (tmp_path / ".forge" / "design_bible.json").exists()

    (tmp_path / "out").mkdir(exist_ok=True)
    bad_plan = [{"plan_n": 1, "location": "Fridge", "speaker": "Mal"}]
    (tmp_path / "out" / "e01_plan.json").write_text(json.dumps(bad_plan))
    assert main(["validate", str(tmp_path)]) == 3  # blocked, fail closed

    good_plan = [{"plan_n": 1, "location": "Balcony", "speaker": "Aiden",
                  "line": {"speaker": "Aiden", "text": "hi"}}]
    (tmp_path / "out" / "e01_plan.json").write_text(json.dumps(good_plan))
    assert main(["validate", str(tmp_path)]) == 0

    plate = _plate(tmp_path / "plate.mp4")
    assert main(["cuts", plate]) == 0
    assert main(["skeleton", plate, "--location", "Street"]) == 0

    empty_proj = tmp_path / "nobible"
    assert main(["validate", str(empty_proj)]) == 0  # opt-in: not installed


def test_story_arc_lint_and_strict_gate():
    from forge.planning.story_arc import lint_arc, validate_arc
    full = lint_arc([{"n": 1, "beat": "setup"}, {"n": 2, "beat": "reveal"},
                     {"n": 3, "beat": "payoff"}])
    assert full["ok"] and not full["inferred"] and full["missing"] == []
    inferred = lint_arc([{"n": 1}, {"n": 2}, {"n": 3}])
    assert inferred["ok"] and inferred["inferred"]  # positional, flagged
    missing = lint_arc([{"n": 1, "beat": "setup"}, {"n": 2, "beat": "setup"}])
    assert not missing["ok"] and "payoff" in missing["missing"]
    validate_arc([{"n": 1, "beat": "setup"}], strict=False)  # report-only
    with pytest.raises(GateLocked, match="payoff"):
        validate_arc([{"n": 1, "beat": "setup"}], strict=True)
    with pytest.raises(GateLocked, match="unknown beat"):
        lint_arc([{"n": 1, "beat": "climax"}])


def test_character_continuity_report():
    from forge.planning.story_arc import character_continuity_report
    plan = [
        {"location": "Kitchen", "line": {"speaker": "Draconia", "text": "a"}},
        {"location": "Balcony", "line": {"speaker": "Draconia", "text": "b"}},
        {"location": "Balcony", "line": {"speaker": "Harry", "text": "c"}},
    ]
    rep = character_continuity_report(plan)
    assert rep["characters"]["Draconia"]["shots"] == 2
    assert any("Draconia" in a for a in rep["attention"])  # multi-location
    assert not any("Harry" in a for a in rep["attention"])  # one location
    assert not rep["ok"]
    assert character_continuity_report([]) == {
        "characters": {}, "attention": [], "ok": True}


def test_script_lint_carries_arc_and_continuity(tmp_path):
    """Real entry path: the script-stage lint report now carries both."""
    import json
    from forge.script_run import write_plan_and_lint
    shots = [{"n": 1, "location": "kitchens", "camera": "wide",
              "action": "she enters", "seconds": 10,
              "lines": [{"speaker": "Harry", "text": "I waited."},
                        {"speaker": "Draconia", "text": "Let me explain."}]}]
    write_plan_and_lint(shots, outdir=tmp_path / "out")
    lint = json.loads((tmp_path / "out" / "e01_action_lint.json").read_text())
    assert lint["story_arc"]["beats"] and "inferred" in lint["story_arc"]
    assert "characters" in lint["character_continuity"]


def test_platform_safe_caption_margins(tmp_path):
    from forge.assemble.caption_safe import (PLATFORM_MARGIN_V,
                                             PlatformError,
                                             platform_safe_ass_kw)
    assert platform_safe_ass_kw("instagram_reels")["margin_v"] == 380
    assert platform_safe_ass_kw("Instagram_Reels")["margin_v"] == 380
    assert platform_safe_ass_kw("generic")["margin_v"] == 260
    assert platform_safe_ass_kw("tiktok", margin_v=500)["margin_v"] == 500
    with pytest.raises(PlatformError, match="unknown caption platform"):
        platform_safe_ass_kw("myspace")
    # real burn path: the platform margin lands in the written ASS
    from forge.assemble.speaker_captions import write_speaker_ass
    ass = str(tmp_path / "s.ass")
    write_speaker_ass([{"speaker": "A", "text": "hi", "start": 0, "end": 1}],
                      ass, **platform_safe_ass_kw("instagram_reels"))
    style = [l for l in open(ass) if l.startswith("Style: spk_A")][0]
    assert style.rstrip().endswith(",10,10,380,1")  # MarginV field lifted
