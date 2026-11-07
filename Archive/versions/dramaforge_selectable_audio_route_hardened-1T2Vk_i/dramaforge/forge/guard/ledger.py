"""Spend guard: paid calls are refused unless an approved cap covers them.

Hardened (m15):
- reserve() rejects non-positive, non-numeric and non-finite amounts
  (a negative amount previously *reduced* recorded spend).
- The ledger file is validated on every read; a corrupt or tampered money
  record fails closed with SpendLocked instead of a raw parse error or a
  silently misread balance.
- Writes are atomic (temp file + fsync + os.replace) so a crash mid-write
  cannot destroy the approved/spent counters.
- A best-effort cross-process advisory lock (fcntl, where available) guards
  the read-modify-write against two processes spending the same approval.
"""
import contextlib
import json
import math
import os
import tempfile
import threading
from pathlib import Path


class SpendLocked(RuntimeError):
    pass


def _atomic_write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(json.dumps(data))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_amount(amount):
    if not _is_number(amount):
        raise SpendLocked(f"reserve amount must be a finite number, got {amount!r}")
    if amount <= 0:
        raise SpendLocked(f"reserve amount must be positive, got {amount!r}")
    return amount


class Ledger:
    """JSON file {"approved": int, "spent": int}. Approval is edited by a human only."""

    def __init__(self, path=None, unit="credits"):
        self.path = Path(path or os.environ.get("FORGE_LEDGER", ".forge/ledger.json"))
        self.unit = unit
        self._lock = threading.Lock()

    def _read(self):
        if not self.path.exists():
            return {"approved": 0, "spent": 0}
        try:
            d = json.loads(self.path.read_text())
        except (OSError, ValueError) as e:
            raise SpendLocked(
                f"ledger at {self.path} is unreadable ({e}); refusing to spend "
                "until a human restores the approved/spent record")
        if (not isinstance(d, dict)
                or not _is_number(d.get("approved")) or not _is_number(d.get("spent"))
                or d["approved"] < 0 or d["spent"] < 0):
            raise SpendLocked(
                f"ledger at {self.path} is malformed ({d!r}); refusing to spend "
                "until a human restores the approved/spent record")
        return d

    def _process_lock(self):
        """Best-effort cross-process advisory lock; no-op without fcntl."""
        try:
            import fcntl
        except ImportError:
            return contextlib.nullcontext()
        lock_path = self.path.parent / (self.path.name + ".lock")

        @contextlib.contextmanager
        def locked():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(lock_path, "a") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)
        return locked()

    def remaining(self):
        d = self._read()
        return d["approved"] - d["spent"]

    def reserve(self, amount, label=""):
        if os.environ.get("FORGE_LIVE") != "1":
            raise SpendLocked(f"live paid calls disabled (set FORGE_LIVE=1 after approval): {label}")
        from forge.guard.generation_hold import require_generation_open
        require_generation_open(ledger_path=self.path)
        _validate_amount(amount)
        with self._lock, self._process_lock():
            d = self._read()
            if amount > d["approved"] - d["spent"]:
                raise SpendLocked(f"{label}: needs {amount} {self.unit}, approved cap has {d['approved'] - d['spent']} left")
            d["spent"] += amount
            _atomic_write_json(self.path, d)
        return amount
