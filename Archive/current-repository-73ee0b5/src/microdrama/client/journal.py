"""Idempotency journal for Magic Hour API jobs to prevent double-billing and data loss."""

import json
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
from ..config import JOURNAL_FILE


class JobJournal:
    """Manages persistent job records in jobs.json."""

    def __init__(self, journal_path: Optional[Path] = None):
        self.path = journal_path or JOURNAL_FILE
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load journal from disk."""
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, data: Dict[str, Any]) -> None:
        """Atomic write to journal file."""
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def compute_tag(payload: Dict[str, Any]) -> str:
        """Calculate deterministic SHA-256 hash of a request payload."""
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get_job(self, tag: str) -> Optional[Dict[str, Any]]:
        """Get job record by hash tag."""
        return self.load().get(tag)

    def set_job(self, tag: str, record: Dict[str, Any]) -> None:
        """Update or create job record."""
        journal = self.load()
        journal[tag] = record
        self.save(journal)
