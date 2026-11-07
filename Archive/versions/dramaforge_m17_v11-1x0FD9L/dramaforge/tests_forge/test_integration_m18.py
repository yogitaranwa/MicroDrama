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
