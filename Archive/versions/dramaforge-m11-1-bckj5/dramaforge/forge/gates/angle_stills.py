"""Angle-matched stills: approve every camera angle as a still BEFORE animation.

Why this exists: locking one portrait per character proved not to be enough -
identity and wardrobe held in the reference material because the SAME person,
costume and room were recognizable from every angle used (front, reverse,
close-up). One approved portrait does not prove the reverse angle matches.

This module is additive: it reads the existing still_lock.json written by
forge.gates.still_first and derives which angle-specific stills a planned
shot list needs, then fails closed while any are missing. It never edits or
re-locks stills itself; locking stays deliberate via lock_stills().
"""
from typing import Dict, Iterable, List

from forge.gates.common import GateLocked, bypassed, read_json, state_dir
from forge.gates.still_first import LOCK_NAME, require_still_lock
from forge.gates.continuity import frame_features, drift_score

# Camera-label prefix -> angle class. Planned shots from
# forge.dialogue_shots use these prefixes; free text normalizes by keyword.
def angle_class(camera_label: str) -> str:
    c = (camera_label or "").lower()
    if c.startswith("reverse") or "reverse" in c:
        return "reverse"
    if c.startswith("reaction_closeup") or "close" in c or c.startswith("cu"):
        return "closeup"
    if c.startswith("over_shoulder") or "ots" in c:
        return "front"
    if "wide" in c or "establish" in c:
        return "wide"
    if "track" in c or "follow" in c:
        return "tracking"
    if c.startswith("single") or "medium" in c:
        return "front"
    return "other"


def required_still_labels(planned_shots: Iterable[Dict]) -> List[str]:
    """Labels a planned shot list needs in the still lock:
    'character:<speaker>:angle:<class>' for every speaking/reaction shot,
    'location:<location>' for every distinct location."""
    labels = set()
    for p in planned_shots:
        sp = p.get("speaker")
        if sp:
            labels.add(f"character:{sp}:angle:{angle_class(p.get('camera', ''))}")
        loc = (p.get("location") or "").strip()
        if loc:
            labels.add(f"location:{loc}")
    return sorted(labels)


def angle_coverage(project_dir, planned_shots: Iterable[Dict]) -> Dict:
    """Report which required angle/location stills are present or missing in
    the current lock. Never raises; use require_angle_stills to gate."""
    record = read_json(state_dir(project_dir) / LOCK_NAME) or {}
    locked = set((record.get("stills") or {}).keys())
    needed = required_still_labels(planned_shots)
    missing = [l for l in needed if l not in locked]
    return {"needed": needed, "present": sorted(locked & set(needed)),
            "missing": missing, "ok": not missing and bool(record.get("locked"))}


def require_angle_stills(project_dir, planned_shots: Iterable[Dict]) -> Dict:
    """Fail closed unless the lock is valid AND covers every angle the plan
    uses. Reuses require_still_lock for lock validity and byte drift."""
    if bypassed():
        return {}
    cov = angle_coverage(project_dir, planned_shots)
    require_still_lock(project_dir, needed=cov["needed"])  # raises with detail
    return cov


def cross_angle_flags(project_dir, character: str, threshold: float = 0.45,
                      box=(0.2, 0.35, 0.8, 0.95)) -> List[Dict]:
    """PIL-only consistency flags between a character's locked angle stills:
    the torso/wardrobe region should read as the same costume from every
    angle. Flags feed human review; they are not verdicts."""
    record = read_json(state_dir(project_dir) / LOCK_NAME) or {}
    prefix = f"character:{character}:angle:"
    feats = {}
    for label, entry in (record.get("stills") or {}).items():
        if label.startswith(prefix):
            try:
                feats[label] = frame_features(entry["path"], box=box)
            except OSError:
                pass
    flags = []
    labels = sorted(feats)
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            s = drift_score(feats[a], feats[b])
            if s > threshold:
                flags.append({"stills": [a, b], "score": round(s, 3),
                              "note": "wardrobe region differs between angles; eyeball both before animating"})
    return flags
