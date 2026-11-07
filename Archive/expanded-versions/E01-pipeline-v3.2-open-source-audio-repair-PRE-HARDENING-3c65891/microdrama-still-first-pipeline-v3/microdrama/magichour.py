from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any

API_BASE = "https://api.magichour.ai"


class PaidGenerationBlocked(RuntimeError):
    pass


def require_paid_enabled(max_credits: int | None) -> None:
    if os.environ.get("ALLOW_PAID_GENERATION") != "1":
        raise PaidGenerationBlocked("Paid generation blocked. Set ALLOW_PAID_GENERATION=1 and pass an explicit credit budget.")
    if max_credits is None or max_credits <= 0:
        raise PaidGenerationBlocked("Paid generation requires --max-credits greater than zero.")


def api_key() -> str:
    key = os.environ.get("MAGIC_HOUR_API_KEY")
    if not key:
        raise RuntimeError("MAGIC_HOUR_API_KEY is not set")
    return key


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        API_BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def write_json(path: str | Path, value: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True))
