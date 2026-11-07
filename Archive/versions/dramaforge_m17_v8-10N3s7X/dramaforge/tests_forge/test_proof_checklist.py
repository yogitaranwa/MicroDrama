"""Proof-scene checklist gate tests. Stdlib only."""
import pytest
from forge.gates import GateLocked, record_proof
from forge.gates.proof_checklist import (ITEMS, start_checklist, check_item,
                                         checklist_status, require_proof_checklist)


def _proof_video(tmp_path):
    p = tmp_path / "proof.mp4"
    p.write_bytes(b"fake-proof")
    return str(p)


def test_blocked_before_start(tmp_path):
    with pytest.raises(GateLocked, match="no proof checklist"):
        require_proof_checklist(tmp_path)


def test_blocked_until_every_item_checked(tmp_path):
    start_checklist(tmp_path)
    for item in sorted(ITEMS)[:-1]:
        check_item(tmp_path, item, "reviewer")
    st = checklist_status(tmp_path)
    assert st["unchecked"] == [sorted(ITEMS)[-1]]
    with pytest.raises(GateLocked, match="incomplete"):
        require_proof_checklist(tmp_path)


def test_full_checklist_passes(tmp_path):
    start_checklist(tmp_path)
    for item in ITEMS:
        check_item(tmp_path, item, "reviewer", note="watched")
    st = require_proof_checklist(tmp_path)
    assert st["complete"]


def test_reviewer_name_required(tmp_path):
    start_checklist(tmp_path)
    with pytest.raises(GateLocked, match="reviewer"):
        check_item(tmp_path, "lip_sync", "  ")


def test_unknown_item_rejected(tmp_path):
    start_checklist(tmp_path)
    with pytest.raises(GateLocked, match="unknown checklist item"):
        check_item(tmp_path, "looks_fine_to_me", "reviewer")


def test_checklist_invalidated_if_proof_video_changes(tmp_path):
    v = _proof_video(tmp_path)
    record_proof(tmp_path, v, n_shots=3, seconds=20, locations=["kitchens"])
    start_checklist(tmp_path)
    for item in ITEMS:
        check_item(tmp_path, item, "reviewer")
    assert require_proof_checklist(tmp_path)["complete"]
    (tmp_path / "proof.mp4").write_bytes(b"re-rendered-differently")
    with pytest.raises(GateLocked, match="changed after checklist"):
        require_proof_checklist(tmp_path)
