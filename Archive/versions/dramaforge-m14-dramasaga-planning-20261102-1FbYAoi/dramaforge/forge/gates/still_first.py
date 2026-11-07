"""Gate 1: stills first.

Every character and location reference still must exist and be locked
(sha256-pinned) BEFORE any moving shot is rendered. Re-rendering a still
after the lock invalidates the lock on purpose: consistency is decided on
stills, never repaired on video.
"""
from forge.gates.common import GateLocked, sha256_file, state_dir, read_json, write_json, now_iso, bypassed

LOCK_NAME = "still_lock.json"


def lock_stills(project_dir, stills: dict) -> dict:
    """stills: {label: image_path}. Locks the current bytes of each still.

    Labels should name what the still pins down, e.g.
    'character:harry:wardrobe', 'character:draconia:portrait',
    'location:great_hall'. Returns the written lock record.
    """
    if not stills:
        raise GateLocked("lock_stills: no stills given; generate reference stills first")
    record = {"locked": True, "locked_at": now_iso(), "stills": {}}
    for label, path in sorted(stills.items()):
        digest = sha256_file(path)  # FileNotFoundError surfaces as-is: the still must exist
        record["stills"][label] = {"path": str(path), "sha256": digest}
    write_json(state_dir(project_dir) / LOCK_NAME, record)
    return record


def require_still_lock(project_dir, needed=None) -> dict:
    """Raise GateLocked unless a valid lock covers `needed` labels and every
    locked still still matches its pinned bytes."""
    if bypassed():
        return {}
    record = read_json(state_dir(project_dir) / LOCK_NAME)
    if not record or not record.get("locked"):
        raise GateLocked(
            "no locked reference stills: generate and lock character/location "
            "stills first (forge.gates.lock_stills), then render moving shots")
    locked = record.get("stills", {})
    missing = [l for l in (needed or []) if l not in locked]
    if missing:
        raise GateLocked(f"still lock is missing required stills: {missing}")
    drifted = [l for l, e in locked.items()
               if not _matches(e)]
    if drifted:
        raise GateLocked(
            f"locked stills changed after locking: {drifted}; re-lock deliberately "
            "with lock_stills instead of editing stills mid-production")
    return record


def _matches(entry) -> bool:
    try:
        return sha256_file(entry["path"]) == entry["sha256"]
    except OSError:
        return False
