from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(files: list[str | Path], metadata: dict[str, Any]) -> dict[str, Any]:
    entries = []
    for file in files:
        p = Path(file)
        entries.append({
            "path": str(p),
            "name": p.name,
            "bytes": p.stat().st_size,
            "sha256": sha256_file(p),
        })
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata,
        "files": entries,
    }


def write_manifest(path: str | Path, manifest: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(manifest, indent=2, sort_keys=True))
