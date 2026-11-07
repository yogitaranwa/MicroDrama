"""Gate 2: prove one short connected scene before any full episode.

The proof scene is deliberately small: ONE location, a handful of shots,
tens of seconds. It must be assembled, auto-checked and signed off by a
human who actually watched and listened to it end to end. Only then may
episode-scale renders reserve credits.
"""
from forge.gates.common import GateLocked, sha256_file, state_dir, read_json, write_json, now_iso, bypassed

PROOF_NAME = "scene_proof.json"
MAX_PROOF_SHOTS = 4
MAX_PROOF_SECONDS = 30
MAX_PROOF_LOCATIONS = 1


def record_proof(project_dir, video_path, n_shots: int, seconds: float, locations, qa: dict | None = None) -> dict:
    """Register an assembled proof scene as pending human review.

    Rejects scenes that are already episode-shaped: the proof must stay
    small, or it proves nothing about restraint.
    """
    locations = list(locations)
    problems = []
    if n_shots > MAX_PROOF_SHOTS:
        problems.append(f"{n_shots} shots > {MAX_PROOF_SHOTS}: shrink the proof scene")
    if seconds > MAX_PROOF_SECONDS:
        problems.append(f"{seconds}s > {MAX_PROOF_SECONDS}s: shrink the proof scene")
    if len(set(locations)) > MAX_PROOF_LOCATIONS:
        problems.append(f"{len(set(locations))} locations > {MAX_PROOF_LOCATIONS}: one room, one connected scene")
    if problems:
        raise GateLocked("proof scene is too big: " + "; ".join(problems))
    record = {
        "video": str(video_path), "sha256": sha256_file(video_path),
        "n_shots": n_shots, "seconds": seconds, "locations": locations,
        "qa": qa or {}, "status": "pending_review", "recorded_at": now_iso(),
    }
    write_json(state_dir(project_dir) / PROOF_NAME, record)
    return record


def signoff_proof(project_dir, reviewer: str, video_path=None) -> dict:
    """Mark the proof scene watched+listened and approved by `reviewer`.
    If video_path is given it must hash-match the recorded proof."""
    record = read_json(state_dir(project_dir) / PROOF_NAME)
    if not record:
        raise GateLocked("no proof scene recorded; assemble one first with record_proof")
    if video_path is not None and sha256_file(video_path) != record["sha256"]:
        raise GateLocked("signoff refused: file differs from the recorded proof scene")
    if not reviewer or not reviewer.strip():
        raise GateLocked("signoff needs a reviewer name; self-approval by the pipeline is not review")
    record.update({"status": "approved", "reviewer": reviewer.strip(), "approved_at": now_iso()})
    write_json(state_dir(project_dir) / PROOF_NAME, record)
    return record


def require_proof(project_dir) -> dict:
    """Raise GateLocked unless a proof scene is recorded AND human-approved."""
    if bypassed():
        return {}
    record = read_json(state_dir(project_dir) / PROOF_NAME)
    if not record:
        raise GateLocked(
            "no approved proof scene: prove one short connected scene "
            "(record_proof + signoff_proof) before episode-scale renders")
    if record.get("status") != "approved":
        raise GateLocked("proof scene is recorded but not human-approved yet")
    try:
        if sha256_file(record["video"]) != record["sha256"]:
            raise GateLocked("approved proof video changed after approval; re-review it")
    except OSError:
        raise GateLocked("approved proof video is missing; re-record and re-review")
    return record
