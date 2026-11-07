"""Canonical reference bank with explicit view coverage.

Adapted from cited open-source reference-selection mechanisms, rebuilt
native to this package. A banked reference is the canonical appearance of
a character, location or prop at named views. Shot planning must bind
actual banked views; a missing view is an explicit gap and a planner must
never substitute a different view and label it as the requested one.
Coverage is a planning fact, not proof the generator honors the reference.
"""
from __future__ import annotations

VIEWS = ("front", "three_quarter", "profile", "back", "full_body", "close", "wide", "detail")
KINDS = ("character", "location", "prop")


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
        if ref.get("kind") not in KINDS:
            errors.append(f"{rid}: kind must be one of {KINDS}")
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
        if "version" in ref and (not isinstance(ref["version"], int) or isinstance(ref["version"], bool) or ref["version"] < 1):
            errors.append(f"{rid}: version must be a positive integer")
    return errors


def coverage_report(story: dict, bank: dict) -> dict:
    """Check reference coverage for every shot in a story.

    Shot fields used: id, visible_characters (required), framing (a view
    label; missing framing is an error, since an unframed shot cannot
    bind a view). Episodes walk in story order.
    """
    errors: list[str] = []
    bank_errors = validate_reference_bank(bank)
    if bank_errors:
        return {"status": "fail", "errors": bank_errors,
                "note": "planning coverage only; generated media still requires review"}
    refs = {r["id"]: r for r in bank["references"]}
    for episode in story.get("episodes", []):
        for shot in episode.get("shots", []):
            sid = shot.get("id", "?")
            framing = shot.get("framing")
            if framing not in VIEWS:
                errors.append(f"{sid}: framing must be one of {VIEWS}")
                continue
            visible = shot.get("visible_characters")
            if not isinstance(visible, list):
                errors.append(f"{sid}: visible_characters list required")
                continue
            for cid in visible:
                ref = refs.get(cid)
                if ref is None:
                    errors.append(f"{sid}: no reference banked for {cid}; explicit gap, no substitution")
                elif framing not in ref.get("views", []):
                    errors.append(
                        f"{sid}: no {framing} view reference for {cid}; banked views "
                        f"{sorted(ref.get('views', []))} do not cover it - explicit gap, no substitution")
    return {"status": "pass" if not errors else "fail", "errors": errors,
            "note": "planning coverage only; generated media still requires review"}
