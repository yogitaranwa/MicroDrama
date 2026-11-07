"""Proof-scene review checklist: make 'we watched it' itemised, not vibes.

The proof-scene gate proves a scene was assembled and a named human approved
it. This checklist names WHAT that human confirmed while watching, so a
proof cannot pass on a glance: identity, wardrobe, set, voices, lip-sync and
dead air each need an explicit check by a named reviewer.

Additive: it reads the existing scene_proof.json (hash check only) and keeps
its own state file. Nothing here replaces signoff_proof; it sharpens it.
"""
from typing import Dict

from forge.gates.common import (GateLocked, bypassed, now_iso, read_json,
                                sha256_file, state_dir, write_json)

CHECKLIST_NAME = "proof_checklist.json"
PROOF_NAME = "scene_proof.json"

ITEMS: Dict[str, str] = {
    "identity_match": "faces are recognisably the locked characters in every shot",
    "wardrobe_match": "costumes match the locked wardrobe stills in every shot",
    "set_match": "the room/set details match the locked location stills across angles",
    "voices_cast": "each line is spoken by the approved voice for that character",
    "lip_sync": "mouths follow the dialogue with no visible drift",
    "no_dead_air": "no silent stretch long enough to feel dead",
    "dialogue_intelligible": "every line is understandable on first listen",
}


def start_checklist(project_dir) -> Dict:
    """Create (or reset) the checklist with every item unchecked."""
    rec = {"items": {k: {"description": d, "checked": False}
                     for k, d in ITEMS.items()},
           "started_at": now_iso()}
    write_json(state_dir(project_dir) / CHECKLIST_NAME, rec)
    return rec


def check_item(project_dir, item: str, reviewer: str, note: str = "") -> Dict:
    """Mark one item confirmed by a named human who actually checked it."""
    if not reviewer or not reviewer.strip():
        raise GateLocked("checklist needs a reviewer name; the pipeline cannot check itself")
    rec = read_json(state_dir(project_dir) / CHECKLIST_NAME)
    if not rec:
        raise GateLocked("no checklist; run start_checklist when the proof cut is ready")
    if item not in rec["items"]:
        raise GateLocked(f"unknown checklist item {item!r}; expected one of {sorted(ITEMS)}")
    rec["items"][item].update({"checked": True, "reviewer": reviewer.strip(),
                               "note": note, "checked_at": now_iso()})
    write_json(state_dir(project_dir) / CHECKLIST_NAME, rec)
    return rec


def checklist_status(project_dir) -> Dict:
    rec = read_json(state_dir(project_dir) / CHECKLIST_NAME) or {"items": {}}
    unchecked = [k for k, v in rec["items"].items() if not v.get("checked")]
    return {"items": rec["items"], "unchecked": unchecked, "complete": not unchecked and bool(rec["items"])}


def require_proof_checklist(project_dir) -> Dict:
    """Fail closed unless every item is checked AND the proof video still
    matches the recorded/approved proof scene (when one exists)."""
    if bypassed():
        return {}
    st = checklist_status(project_dir)
    if not st["items"]:
        raise GateLocked("no proof checklist; start_checklist, then check each item while watching")
    if st["unchecked"]:
        raise GateLocked(f"proof checklist incomplete; still unchecked: {st['unchecked']}")
    proof = read_json(state_dir(project_dir) / PROOF_NAME)
    if proof and proof.get("video"):
        try:
            if sha256_file(proof["video"]) != proof["sha256"]:
                raise GateLocked("proof video changed after checklist; re-watch and re-check")
        except OSError:
            raise GateLocked("proof video missing; re-record the proof scene")
    return st
