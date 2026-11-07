"""Gate 3: continuous playback + listening review before anything is delivered.

review_episode() builds an honest machine half of the review: full-timeline
coverage, silent stretches, and any continuity flags attached by the caller.
signoff() records that a named human then actually watched and listened to
the whole file. require_signoff() gates delivery on both.
"""
from forge.gates.common import GateLocked, sha256_file, state_dir, read_json, write_json, now_iso, bypassed

REPORT_NAME = "review_report.json"
SIGNOFF_NAME = "review_signoff.json"
DEFAULT_MAX_SILENT_S = 3.0


def silent_stretches(loudness_samples, floor_db: float = -45.0, max_silent_s: float = DEFAULT_MAX_SILENT_S):
    """loudness_samples: [(t_seconds, db)]. Returns [(start, end)] of stretches
    under floor_db longer than max_silent_s. Gaps between samples count."""
    stretches, start, end = [], None, None
    for t, db in sorted(loudness_samples):
        if db < floor_db:
            if start is None:
                start = t
            end = t
        else:
            if start is not None and end - start > max_silent_s:
                stretches.append((round(start, 2), round(end, 2)))
            start = end = None
    if start is not None and end is not None and end - start > max_silent_s:
        stretches.append((round(start, 2), round(end, 2)))
    return stretches


def review_episode(project_dir, episode_path, shots, loudness_samples=None,
                   continuity_flags=None, max_silent_s: float = DEFAULT_MAX_SILENT_S,
                   lip_sync_done: bool = False) -> dict:
    """shots: [(name, seconds)] as placed on the final timeline.
    Writes .forge/review_report.json and returns it. status is 'issues' if
    any machine check trips, else 'ready_for_human_review' - never
    'approved'; approval is a human act recorded by signoff()."""
    import math
    import os
    bad = [(n, s) for n, s in shots
           if isinstance(s, bool) or not isinstance(s, (int, float)) or not math.isfinite(s) or s < 0]
    duration = sum(s for _, s in shots if isinstance(s, (int, float)) and not isinstance(s, bool)
                   and math.isfinite(s) and s >= 0)
    issues = []
    if not os.path.exists(episode_path):
        raise GateLocked(f"episode file missing: {episode_path}")
    if bad:
        issues.append(f"invalid shot durations (negative/non-finite/non-numeric): {bad}")
    if duration <= 0:
        issues.append("empty timeline")
    stretches = silent_stretches(loudness_samples or [], max_silent_s=max_silent_s)
    for a, b in stretches:
        issues.append(f"silent stretch {a}s-{b}s (> {max_silent_s}s)")
    for flag in (continuity_flags or []):
        issues.append(f"continuity: {flag}")
    if not lip_sync_done:
        issues.append("lip-sync not run on this cut")
    report = {
        "episode": str(episode_path), "sha256": sha256_file(episode_path),
        "seconds": duration, "n_shots": len(shots),
        "silent_stretches": stretches, "continuity_flags": continuity_flags or [],
        "lip_sync_done": lip_sync_done, "issues": issues,
        "status": "issues" if issues else "ready_for_human_review",
        "reviewed_at": now_iso(),
    }
    write_json(state_dir(project_dir) / REPORT_NAME, report)
    return report


def signoff(project_dir, reviewer: str, episode_path=None, note: str = "") -> dict:
    """Record that `reviewer` watched AND listened to the whole episode."""
    if not reviewer or not reviewer.strip():
        raise GateLocked("signoff needs a reviewer name")
    report = read_json(state_dir(project_dir) / REPORT_NAME)
    if not report:
        raise GateLocked("no review report; run review_episode first")
    ep = episode_path or report["episode"]
    digest = sha256_file(ep)
    if digest != report["sha256"]:
        raise GateLocked("episode changed since review; re-run review_episode before signoff")
    rec = {"episode": report["episode"], "sha256": digest, "reviewer": reviewer.strip(),
           "note": note, "signed_off_at": now_iso()}
    write_json(state_dir(project_dir) / SIGNOFF_NAME, rec)
    return rec


def require_signoff(project_dir, episode_path=None) -> dict:
    """Raise GateLocked unless a human signoff covers the CURRENT episode bytes."""
    if bypassed():
        return {}
    report = read_json(state_dir(project_dir) / REPORT_NAME)
    rec = read_json(state_dir(project_dir) / SIGNOFF_NAME)
    if not report or not rec:
        raise GateLocked("no review/signoff: run review_episode, watch and listen, then signoff")
    ep = episode_path or rec["episode"]
    try:
        digest = sha256_file(ep)
    except OSError:
        raise GateLocked(f"episode file missing: {ep}")
    if digest != rec["sha256"] or digest != report["sha256"]:
        raise GateLocked("episode changed after signoff; review and sign off the new cut")
    return rec
