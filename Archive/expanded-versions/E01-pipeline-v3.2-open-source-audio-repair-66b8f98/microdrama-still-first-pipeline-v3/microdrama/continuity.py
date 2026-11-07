"""Continuity contracts: reference bank, per-shot state, cut transitions,
action phases.

Mechanisms adapted from cited open-source approaches (reference/view
selection, structured action beats, staging continuity checklists), rebuilt
native to this pipeline. A validated contract is a complete plan, not proof
that generated media honors it: acceptance still needs real review of the
actual bytes. Missing views are explicit gaps; a planner must never
substitute a different view and label it as the requested one.
"""
from __future__ import annotations

VIEWS = ("front", "three_quarter", "profile", "back", "full_body", "close", "wide", "detail")
REFERENCE_KINDS = ("character", "location", "prop")
PHASES = ("before", "contact", "after")
# Fields that may reset across a scene cut without an in-story explanation.
PHYSICAL_RESET_FIELDS = ("position", "facing", "emotion", "eyeline")
CHARACTER_FIELDS = ("position", "facing", "eyeline", "wardrobe", "emotion")


def validate_reference_bank(bank: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(bank, dict) or not isinstance(bank.get("references"), list):
        return ["reference bank requires a references list"]
    seen: set[str] = set()
    for ref in bank["references"]:
        rid = ref.get("id") if isinstance(ref, dict) else None
        if not isinstance(rid, str) or not rid.strip():
            errors.append("every reference needs a nonempty id")
            continue
        if rid in seen:
            errors.append(f"duplicate reference id {rid}")
        seen.add(rid)
        if ref.get("kind") not in REFERENCE_KINDS:
            errors.append(f"{rid}: kind must be one of {REFERENCE_KINDS}")
        views = ref.get("views")
        if not isinstance(views, list) or not views:
            errors.append(f"{rid}: needs a nonempty views list")
        else:
            bad = sorted(set(views) - set(VIEWS))
            if bad:
                errors.append(f"{rid}: unknown views {bad}")
            if len(views) != len(set(views)):
                errors.append(f"{rid}: duplicate views")
        if "sha256" in ref and (not isinstance(ref["sha256"], str) or len(ref["sha256"]) != 64):
            errors.append(f"{rid}: sha256 must be a 64-char hex digest")
    return errors


def _validate_state(state: dict, cast: set[str], label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return [f"{label}: state must be an object"]
    chars = state.get("characters")
    if not isinstance(chars, dict) or set(chars) != cast:
        errors.append(f"{label}: characters must enumerate the full cast, including offscreen")
        return errors
    for cid, values in chars.items():
        if not isinstance(values, dict):
            errors.append(f"{label}: {cid} state must be an object")
            continue
        missing = [f for f in CHARACTER_FIELDS if not isinstance(values.get(f), str) or not values[f].strip()]
        if missing:
            errors.append(f"{label}: {cid} needs nonempty text for {missing}")
        props = values.get("props", {})
        if not isinstance(props, dict):
            errors.append(f"{label}: {cid} props must be a map")
            continue
        for pid, pstate in props.items():
            if not isinstance(pstate, dict):
                errors.append(f"{label}: prop {pid} state must be an object")
                continue
            if pstate.get("hand") not in ("left", "right", "both", "none"):
                errors.append(f"{label}: prop {pid} hand must be left/right/both/none")
            count = pstate.get("count", 1)
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                errors.append(f"{label}: prop {pid} count must be a non-negative integer")
    if not isinstance(state.get("lighting"), str) or not state["lighting"].strip():
        errors.append(f"{label}: lighting description required")
    return errors


def check_cut_transition(prev_end: dict, next_start: dict, same_scene: bool) -> list[str]:
    """Unexplained state changes across a cut. Within a scene nothing may
    change silently; across scenes only physical reset fields may differ."""
    errors: list[str] = []
    for cid, after in next_start.get("characters", {}).items():
        before = prev_end.get("characters", {}).get(cid, {})
        for fieldname in CHARACTER_FIELDS:
            old, new = before.get(fieldname), after.get(fieldname)
            if old is None or new is None or old == new:
                continue
            if same_scene or fieldname not in PHYSICAL_RESET_FIELDS:
                errors.append(f"{cid}: unexplained cut change in {fieldname}: {old!r} -> {new!r}")
        before_props = before.get("props", {})
        for pid, pstate in after.get("props", {}).items():
            old = before_props.get(pid)
            if old is not None and (old.get("hand"), old.get("count", 1)) != (pstate.get("hand"), pstate.get("count", 1)):
                errors.append(f"{cid}: unexplained prop change for {pid} across cut")
    if same_scene and prev_end.get("lighting") != next_start.get("lighting"):
        errors.append("unexplained lighting change within a scene")
    return errors


def check_reference_coverage(shot: dict, bank: dict) -> list[str]:
    """Every visible character needs a banked reference at the shot's view.
    A missing view is an explicit gap; substitution is not allowed."""
    errors: list[str] = []
    framing = shot.get("framing")
    if framing not in VIEWS:
        errors.append(f"{shot.get('id', '?')}: framing must be one of {VIEWS}")
        return errors
    visible = shot.get("visible_characters")
    if not isinstance(visible, list) or not visible:
        errors.append(f"{shot.get('id', '?')}: visible_characters required")
        return errors
    refs = {r.get("id"): r for r in bank.get("references", []) if isinstance(r, dict)}
    for cid in visible:
        ref = refs.get(cid)
        if ref is None:
            errors.append(f"{shot.get('id', '?')}: no reference banked for {cid}; explicit gap, no substitution")
        elif framing not in ref.get("views", []):
            errors.append(
                f"{shot.get('id', '?')}: no {framing} view reference for {cid}; "
                f"banked views {sorted(ref.get('views', []))} do not cover it - explicit gap, no substitution")
    return errors


def validate_action_phases(shot: dict) -> list[str]:
    """A scripted action must be structured as before/contact/after phases
    with review items. Schema completeness only; only media review can
    establish the phases actually occurred."""
    errors: list[str] = []
    action = shot.get("action")
    if action is None:
        return errors
    if not isinstance(action, dict) or not isinstance(action.get("summary"), str) or not action["summary"].strip():
        return [f"{shot.get('id', '?')}: action needs a summary"]
    phases = action.get("phases")
    if not isinstance(phases, dict) or set(phases) != set(PHASES):
        return [f"{shot.get('id', '?')}: action requires phases {list(PHASES)}"]
    for phase, detail in phases.items():
        if not isinstance(detail, dict) or not isinstance(detail.get("description"), str) or not detail["description"].strip():
            errors.append(f"{shot.get('id', '?')}: phase {phase} needs a description")
        items = detail.get("review_items") if isinstance(detail, dict) else None
        if not isinstance(items, list) or not items or any(not isinstance(i, str) or not i.strip() for i in items):
            errors.append(f"{shot.get('id', '?')}: phase {phase} needs nonempty review_items")
    return errors


def validate_continuity_document(doc: dict) -> dict:
    errors: list[str] = []
    bank = doc.get("reference_bank")
    errors.extend(validate_reference_bank(bank) if bank is not None else ["reference_bank required"])
    cast = doc.get("cast")
    if not isinstance(cast, list) or not cast or any(not isinstance(c, str) for c in cast):
        errors.append("cast must be a nonempty list of character ids")
        cast = []
    cast_set = set(cast)
    shots = doc.get("shots")
    if not isinstance(shots, list) or not shots:
        errors.append("shots must be a nonempty list")
        shots = []
    prev_end, prev_scene = None, None
    for shot in shots:
        sid = shot.get("id", "?") if isinstance(shot, dict) else "?"
        errors.extend(_validate_state(shot.get("start_state"), cast_set, f"{sid} start_state"))
        errors.extend(_validate_state(shot.get("end_state"), cast_set, f"{sid} end_state"))
        errors.extend(check_reference_coverage(shot, bank or {}))
        errors.extend(validate_action_phases(shot))
        scene = shot.get("scene_id")
        if not isinstance(scene, str) or not scene.strip():
            errors.append(f"{sid}: scene_id required")
        if prev_end is not None:
            errors.extend(check_cut_transition(prev_end, shot.get("start_state", {}), same_scene=(scene == prev_scene)))
        prev_end, prev_scene = shot.get("end_state", {}), scene
    return {"status": "pass" if not errors else "fail", "errors": errors,
            "note": "contract completeness only; generated media still requires real review"}
