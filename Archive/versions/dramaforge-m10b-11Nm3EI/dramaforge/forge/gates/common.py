"""Shared gate primitives."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path


from forge.guard.ledger import SpendLocked


class GateLocked(SpendLocked):
    """A process gate refused the action, before any credit is reserved.
    Subclasses SpendLocked so existing spend-guard handling catches it."""


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def state_dir(project_dir) -> Path:
    p = Path(project_dir) / ".forge"
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1))


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def enabled() -> bool:
    return os.environ.get("FORGE_GATES", "1") != "0"


def bypassed() -> bool:
    if enabled():
        return False
    print("WARNING: FORGE_GATES=0, process gates bypassed", file=sys.stderr)
    return True
