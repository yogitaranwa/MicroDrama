"""Per-character reference-angle planner (m19).

Adapted from the externally supplied "Soul ID Character Angles" prompt
matrix: front close-up, front full body, 45-degree L/R, profiles, back.
Two deliberate changes versus that matrix: (1) every prompt must carry the
character's distinguishing identifiers (glasses, scars, crest, earrings,
outfit) because the matrix's "blemish-free, no moles" wording erases
identity features we need to KEEP; (2) coverage is checked against our
existing verified reference bank before any new still is requested.
Free/local only - produces prompts and a coverage report, no generation."""
from __future__ import annotations

from .registry import IntegrationError

ANGLES = (
    "front_close", "front_full", "left_45", "right_45",
    "left_profile", "right_profile", "back_full",
)

# Words from the source matrix that erase identity; never emitted by us.
ERASURE_TERMS = ("blemish-free", "no moles", "no spots", "flawless skin")

_ANGLE_DESC = {
    "front_close": "close-up of the face, front view",
    "front_full": "full body, front view, head to shoes",
    "left_45": "three-quarter view turned 45 degrees to the character's left",
    "right_45": "three-quarter view turned 45 degrees to the character's right",
    "left_profile": "strict side profile facing left",
    "right_profile": "strict side profile facing right",
    "back_full": "full body from directly behind",
}


def build_angle_plan(character: str, identifiers, outfit: str,
                     existing=()) -> dict:
    """Return {character, missing, covered, prompts}. `identifiers` are the
    features that MUST survive (e.g. ["round glasses", "black tousled hair"]);
    `existing` lists angle keys already covered by the verified bank."""
    if not character or not character.strip():
        raise IntegrationError("character name must be non-empty")
    if not identifiers:
        raise IntegrationError(f"{character}: identifiers are required - "
                               "reference prompts without them erase identity")
    ids = [i.strip() for i in identifiers if i and i.strip()]
    if not ids:
        raise IntegrationError(f"{character}: identifiers are required - "
                               "reference prompts without them erase identity")
    bad = [t for t in ERASURE_TERMS
           if any(t in i.lower() for i in ids) or t in (outfit or "").lower()]
    if bad:
        raise IntegrationError(f"erasure wording rejected: {', '.join(bad)}")
    covered = [a for a in ANGLES if a in set(existing)]
    missing = [a for a in ANGLES if a not in set(existing)]
    keep = ", ".join(ids)
    prompts = {}
    for a in missing:
        prompts[a] = (
            f"Photorealistic {_ANGLE_DESC[a]} of {character}, "
            f"wearing {outfit}. Keep every distinguishing feature exactly: {keep}. "
            "Clean even lighting, vertical 9:16, character reference still.")
    return {"character": character, "covered": covered, "missing": missing,
            "prompts": prompts,
            "rule": "identifiers preserved; erasure wording rejected"}


def coverage_report(plans) -> dict:
    """Aggregate per-character plans for gate review."""
    return {p["character"]: {"covered": len(p["covered"]),
                             "missing": p["missing"]} for p in plans}
