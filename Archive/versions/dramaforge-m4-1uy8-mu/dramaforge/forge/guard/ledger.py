"""Spend guard: paid calls are refused unless an approved cap covers them."""
import json, os, threading
from pathlib import Path

class SpendLocked(RuntimeError):
    pass

class Ledger:
    """JSON file {"approved": int, "spent": int}. Approval is edited by a human only."""
    def __init__(self, path=None, unit="credits"):
        self.path = Path(path or os.environ.get("FORGE_LEDGER", ".forge/ledger.json"))
        self.unit = unit
        self._lock = threading.Lock()

    def _read(self):
        if not self.path.exists():
            return {"approved": 0, "spent": 0}
        return json.loads(self.path.read_text())

    def remaining(self):
        d = self._read()
        return d["approved"] - d["spent"]

    def reserve(self, amount, label=""):
        if os.environ.get("FORGE_LIVE") != "1":
            raise SpendLocked(f"live paid calls disabled (set FORGE_LIVE=1 after approval): {label}")
        with self._lock:
            d = self._read()
            if amount > d["approved"] - d["spent"]:
                raise SpendLocked(f"{label}: needs {amount} {self.unit}, approved cap has {d['approved'] - d['spent']} left")
            d["spent"] += amount
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(d))
        return amount
