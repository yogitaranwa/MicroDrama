"""Angle-matched still gate tests. Stdlib + PIL."""
import pytest
from forge.gates import GateLocked, lock_stills
from forge.gates.angle_stills import (angle_class, required_still_labels,
                                      angle_coverage, require_angle_stills,
                                      cross_angle_flags)


def _img(path, colour):
    from PIL import Image
    Image.new("RGB", (64, 64), colour).save(path)
    return str(path)


PLAN = [
    {"plan_n": 1, "kind": "speaker", "speaker": "Harry", "camera": "over_shoulder:Harry_over_Draconia", "location": "kitchens"},
    {"plan_n": 2, "kind": "speaker", "speaker": "Draconia", "camera": "reverse:Draconia_over_Harry", "location": "kitchens"},
    {"plan_n": 3, "kind": "reaction", "speaker": "Harry", "camera": "reaction_closeup:Harry", "location": "kitchens"},
]


def test_angle_class_normalises():
    assert angle_class("reverse:Draconia_over_Harry") == "reverse"
    assert angle_class("over_shoulder:Harry_over_Draconia") == "front"
    assert angle_class("reaction_closeup:Harry") == "closeup"
    assert angle_class("wide establishing shot") == "wide"
    assert angle_class("") == "other"


def test_required_labels_from_plan():
    labels = required_still_labels(PLAN)
    assert "character:Harry:angle:front" in labels
    assert "character:Draconia:angle:reverse" in labels
    assert "character:Harry:angle:closeup" in labels
    assert "location:kitchens" in labels


def test_gate_blocks_when_angles_missing(tmp_path):
    lock_stills(tmp_path, {"character:Harry:angle:front": _img(tmp_path / "h.png", (120, 60, 40))})
    cov = angle_coverage(tmp_path, PLAN)
    assert not cov["ok"] and "location:kitchens" in cov["missing"]
    with pytest.raises(GateLocked, match="missing required stills"):
        require_angle_stills(tmp_path, PLAN)


def test_gate_passes_with_full_coverage(tmp_path):
    stills = {
        "character:Harry:angle:front": _img(tmp_path / "hf.png", (120, 60, 40)),
        "character:Harry:angle:closeup": _img(tmp_path / "hc.png", (118, 62, 41)),
        "character:Draconia:angle:reverse": _img(tmp_path / "dr.png", (30, 30, 90)),
        "location:kitchens": _img(tmp_path / "kit.png", (70, 70, 70)),
    }
    lock_stills(tmp_path, stills)
    cov = require_angle_stills(tmp_path, PLAN)
    assert cov["ok"] and cov["missing"] == []


def test_gate_blocks_without_any_lock(tmp_path):
    with pytest.raises(GateLocked, match="stills"):
        require_angle_stills(tmp_path, PLAN)


def test_cross_angle_flags_drift(tmp_path):
    stills = {
        "character:Harry:angle:front": _img(tmp_path / "hf.png", (120, 60, 40)),
        "character:Harry:angle:reverse": _img(tmp_path / "hr.png", (200, 10, 200)),  # wardrobe changed?!
    }
    lock_stills(tmp_path, stills)
    flags = cross_angle_flags(tmp_path, "Harry")
    assert len(flags) == 1 and flags[0]["score"] > 0.45


def test_cross_angle_consistent_pair_clean(tmp_path):
    stills = {
        "character:Harry:angle:front": _img(tmp_path / "hf.png", (120, 60, 40)),
        "character:Harry:angle:reverse": _img(tmp_path / "hr.png", (121, 61, 41)),
    }
    lock_stills(tmp_path, stills)
    assert cross_angle_flags(tmp_path, "Harry") == []
