"""A persisted user hold is independent of caps and cannot be bypassed by FORGE_GATES.

No resume helper: an operator must verify a newer user instruction before
changing the record. Preparation and read-only inspection remain available.
"""
import json
import os
from pathlib import Path
from .ledger import SpendLocked


def require_generation_open(project_dir=None, ledger_path=None):
    paths = []
    if project_dir:
        paths.append(Path(project_dir) / '.forge' / 'generation_hold.json')
    if ledger_path:
        paths.append(Path(ledger_path).parent / 'generation_hold.json')
    configured = os.environ.get('FORGE_GENERATION_HOLD')
    if configured:
        paths.append(Path(configured))
    for path in set(paths):
        if not path.exists():
            continue
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise SpendLocked('unreadable generation hold: ' + str(path)) from exc
        if not isinstance(record, dict) or type(record.get('held')) is not bool:
            raise SpendLocked('malformed generation hold: ' + str(path))
        if record['held']:
            raise SpendLocked('generation held by user: ' + str(record.get('reason', 'review required')))
