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
    """Read gate state. A file that exists but is not valid JSON fails closed:
    gate state guards money and review decisions, so a corrupt record must
    stop the flow loudly instead of looking like an absent one."""
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise GateLocked(f"gate state at {path} is unreadable ({e}); restore or re-create it deliberately")


def write_json(path, data) -> None:
    """Atomic write: temp file + fsync + os.replace, so a crash mid-write can
    never leave a half-written gate state (still lock, signoff, checklist)."""
    import tempfile
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(json.dumps(data, indent=1))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def enabled() -> bool:
    return os.environ.get("FORGE_GATES", "1") != "0"


def bypassed() -> bool:
    if enabled():
        return False
    print("WARNING: FORGE_GATES=0, process gates bypassed", file=sys.stderr)
    return True
