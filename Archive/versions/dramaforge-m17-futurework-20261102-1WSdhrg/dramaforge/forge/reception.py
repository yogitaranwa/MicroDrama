"""Viewer reception records: how pace and music level land with real people
(future-work item 7).

This module is the instrumentation for that study, not the study itself:
it records structured viewing sessions (pace rating, music-level rating,
timestamped moments) and aggregates them. No record is ever fabricated by
the pipeline; every row names the viewer who supplied it. Running the study
- recruiting viewers and collecting these records - remains a human activity.
"""
import json
import os
import tempfile
from pathlib import Path

from forge.gates.common import GateLocked, now_iso

STORE_NAME = "reception.jsonl"
MIN_RATING, MAX_RATING = 1, 5
_MOMENT_KINDS = ("pace", "music", "other")


def _rating(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise GateLocked(f"{field} must be a whole-number rating {MIN_RATING}-{MAX_RATING}")
    if not MIN_RATING <= value <= MAX_RATING:
        raise GateLocked(f"{field} must be {MIN_RATING}-{MAX_RATING}, got {value}")
    return value


def _moments(moments):
    clean = []
    for i, m in enumerate(moments or []):
        if not isinstance(m, dict):
            raise GateLocked(f"moment {i + 1} must be an object")
        t = m.get("t")
        if isinstance(t, bool) or not isinstance(t, (int, float)) or t < 0:
            raise GateLocked(f"moment {i + 1}: t must be a non-negative number of seconds")
        kind = str(m.get("kind") or "other").strip().lower()
        if kind not in _MOMENT_KINDS:
            raise GateLocked(f"moment {i + 1}: kind must be one of {_MOMENT_KINDS}")
        note = str(m.get("note") or "").strip()
        if not note:
            raise GateLocked(f"moment {i + 1}: a note is required")
        clean.append({"t": float(t), "kind": kind, "note": note})
    return clean


def record_viewing(store_path, episode: str, viewer: str, pace: int,
                   music_level: int, moments=None, note: str = "") -> dict:
    """Append one viewer's session to the JSONL store. Viewer and episode
    must be named; ratings are whole numbers 1-5. The append is a single
    atomic line write so a crash cannot leave half a record."""
    if not episode or not str(episode).strip():
        raise GateLocked("episode is required")
    if not viewer or not str(viewer).strip():
        raise GateLocked("viewer is required")
    rec = {"episode": str(episode).strip(), "viewer": str(viewer).strip(),
           "pace": _rating(pace, "pace"), "music_level": _rating(music_level, "music_level"),
           "moments": _moments(moments), "note": str(note or "").strip(),
           "recorded_at": now_iso()}
    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w") as fh:
            if path.exists():
                fh.write(path.read_text())
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return rec


def read_store(store_path) -> dict:
    """Read the JSONL store. Research data, not gate state: a corrupt line is
    skipped and counted, never silently treated as a real viewing."""
    path = Path(store_path)
    records, skipped = [], 0
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                skipped += 1
    return {"records": records, "skipped_lines": skipped}


def aggregate(store_path) -> dict:
    """Per-episode means and distributions over every recorded viewing."""
    store = read_store(store_path)
    by_ep = {}
    for rec in store["records"]:
        ep = by_ep.setdefault(rec["episode"], {"viewings": 0, "pace": [], "music_level": [],
                                               "viewers": set(), "moments": 0})
        ep["viewings"] += 1
        ep["viewers"].add(rec["viewer"])
        ep["pace"].append(rec["pace"])
        ep["music_level"].append(rec["music_level"])
        ep["moments"] += len(rec.get("moments", []))
    out = {}
    for name, ep in sorted(by_ep.items()):
        out[name] = {
            "viewings": ep["viewings"], "viewers": len(ep["viewers"]),
            "pace_mean": round(sum(ep["pace"]) / len(ep["pace"]), 2),
            "music_level_mean": round(sum(ep["music_level"]) / len(ep["music_level"]), 2),
            "pace_counts": {r: ep["pace"].count(r) for r in range(MIN_RATING, MAX_RATING + 1)},
            "music_level_counts": {r: ep["music_level"].count(r) for r in range(MIN_RATING, MAX_RATING + 1)},
            "moments": ep["moments"],
        }
    return {"episodes": out, "skipped_lines": store["skipped_lines"]}
