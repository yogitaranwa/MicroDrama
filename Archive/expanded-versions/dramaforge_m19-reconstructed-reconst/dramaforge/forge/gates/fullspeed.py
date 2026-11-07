"""Gate 3b: the full-speed review step.

Why this exists: every defect that shipped had passed through SAMPLED checks
(frame strips, spot listens). The only review that catches acting, sync and
pacing defects is one person watching and listening to the whole episode at
full speed. signoff() already attests "watched and listened"; this record
makes that attestation structured: what the reviewer saw and heard, with
timestamped observations, bound to the exact bytes reviewed.

Delivery requires this record (see gates/deliver.py). A record that says the
episode was not watched or not listened to is not a review and is refused.
"""
from forge.gates.common import (GateLocked, sha256_file, state_dir, read_json,
                                write_json, now_iso, bypassed)
from forge.gates.review import REPORT_NAME

REVIEW_NAME = "fullspeed_review.json"
VERDICTS = ("approved", "issues")
_OBS_KINDS = ("visual", "audio", "sync", "pace", "caption", "other")


def _validate_observations(observations):
    clean = []
    for i, obs in enumerate(observations or []):
        if not isinstance(obs, dict):
            raise GateLocked(f"observation {i + 1} must be an object")
        t = obs.get("t")
        if isinstance(t, bool) or not isinstance(t, (int, float)) or t < 0:
            raise GateLocked(f"observation {i + 1}: t must be a non-negative number of seconds")
        kind = str(obs.get("kind") or "other").strip().lower()
        if kind not in _OBS_KINDS:
            raise GateLocked(f"observation {i + 1}: kind must be one of {_OBS_KINDS}")
        note = str(obs.get("note") or "").strip()
        if not note:
            raise GateLocked(f"observation {i + 1}: a note is required")
        clean.append({"t": float(t), "kind": kind, "note": note})
    return sorted(clean, key=lambda o: o["t"])


def record_fullspeed_review(project_dir, reviewer: str, episode_path=None,
                            watched_full_speed: bool = False,
                            listened: bool = False,
                            observations=None, verdict: str = "",
                            note: str = "") -> dict:
    """Record one human's full-speed watch + listen. Refused unless the
    reviewer actually watched at full speed AND listened; anything else is
    not this gate. The machine review (review_episode) must already cover the
    same bytes, so the human record never stands in for the machine half."""
    if not reviewer or not reviewer.strip():
        raise GateLocked("full-speed review needs a reviewer name")
    if watched_full_speed is not True:
        raise GateLocked("not watched at full speed; a sampled look is not this review")
    if listened is not True:
        raise GateLocked("not listened to; muted playback is not this review")
    if verdict not in VERDICTS:
        raise GateLocked(f"verdict must be one of {VERDICTS}")
    report = read_json(state_dir(project_dir) / REPORT_NAME)
    if not report:
        raise GateLocked("no machine review report; run review_episode first")
    ep = episode_path or report["episode"]
    digest = sha256_file(ep)
    if digest != report["sha256"]:
        raise GateLocked("episode changed since the machine review; re-run review_episode first")
    rec = {"episode": report["episode"], "sha256": digest,
           "reviewer": reviewer.strip(),
           "watched_full_speed": True, "listened": True,
           "observations": _validate_observations(observations),
           "verdict": verdict, "note": note,
           "reviewed_at": now_iso()}
    write_json(state_dir(project_dir) / REVIEW_NAME, rec)
    return rec


def require_fullspeed_review(project_dir, episode_path=None) -> dict:
    """Raise GateLocked unless an approved full-speed review covers the
    CURRENT episode bytes."""
    if bypassed():
        return {}
    rec = read_json(state_dir(project_dir) / REVIEW_NAME)
    if not rec:
        raise GateLocked(
            "no full-speed review: one person must watch and listen to the "
            "whole episode at full speed, then record_fullspeed_review")
    ep = episode_path or rec["episode"]
    try:
        digest = sha256_file(ep)
    except OSError:
        raise GateLocked(f"episode file missing: {ep}")
    if digest != rec["sha256"]:
        raise GateLocked("episode changed after the full-speed review; review the new cut")
    if rec.get("verdict") != "approved":
        raise GateLocked(
            f"full-speed review verdict is {rec.get('verdict')!r}; "
            "resolve the recorded observations and review again")
    return rec
