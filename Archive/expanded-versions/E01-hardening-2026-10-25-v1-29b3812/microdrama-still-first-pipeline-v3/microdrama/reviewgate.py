"""Fail-closed delivery gate: mechanical detectors plus hash-bound human review.

Engineering checks based on the 2026-10-25 failure audit:
1. A shot missing its scripted action is REJECTED - never patched into the
   assembly with a still, crop, retime or slow-motion substitute.
2. When automatic checks cannot establish action quality or emotional audio,
   the pipeline PAUSES for named human review instead of assembling.
3. Review receipts are bound to the exact reviewed bytes (sha256). Changed
   bytes invalidate the receipt.

A receipt is a record that a named person states they checked something.
It is not independent proof that they did. Mechanical defects (freeze,
silence, levels) are measured here; actions, expressions, emotion and lip
sync are only ever established by review, never by this code.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path

from .detectors import mechanical_report
from .manifest import sha256_file

# Semantic checks that only a competent reviewer can make on a shot.
SHOT_REVIEW_CHECKS = ("action_present", "expression_ok", "lip_sync_ok", "continuity_ok")
# Episode-level checks after assembly.
EPISODE_REVIEW_CHECKS = ("full_playback", "emotional_listen")

APPROVED = "APPROVED"
REJECTED = "REJECTED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"


def requirement_sha256(requirement: dict) -> str:
    return hashlib.sha256(json.dumps(requirement, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_requirements(requirements: dict) -> None:
    beats = requirements.get("beats")
    if not isinstance(beats, list) or not beats:
        raise ValueError("Nonempty ordered beat requirements required")
    seen = set(); previous = 0.0
    for req in beats:
        beat = str(req.get("beat", ""))
        if not beat or beat in seen:
            raise ValueError("Missing or duplicate beat identity")
        seen.add(beat)
        start, end = req.get("start"), req.get("end")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (start, end)) or start < 0 or end <= start or abs(start - previous) > .001:
            raise ValueError("Beat intervals must be finite, positive and contiguous from zero")
        if not isinstance(req.get("required_actions"), list) or not req["required_actions"]:
            raise ValueError("Explicit required actions required")
        for line in req.get("lines", []):
            a, b = line.get("start"), line.get("end")
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in (a, b)) or not start <= a < b <= end:
                raise ValueError("Dialogue window must fit its beat")
        previous = end


def scaffold_receipt(asset: str | Path, beat: str, requirement: dict | None = None) -> dict[str, object]:
    """Prefill asset identity + hash; a reviewer fills the rest."""
    return {
        "beat": str(beat),
        "requirement_sha256": requirement_sha256(requirement) if requirement is not None else None,
        "asset": str(Path(asset).resolve()),
        "asset_sha256": sha256_file(asset),
        "reviewer": None,
        "reviewed_at": None,
        "checks": {name: None for name in SHOT_REVIEW_CHECKS},
        "notes": "",
    }


def _receipt_problems(receipt: dict, asset: str | Path) -> list[str]:
    problems = []
    if receipt.get("asset_sha256") != sha256_file(asset):
        problems.append("receipt is stale: asset bytes changed after review")
    reviewer = receipt.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        problems.append("named human reviewer required")
    stamp = receipt.get("reviewed_at")
    try:
        parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            problems.append("review timestamp requires timezone")
        elif parsed > datetime.now(timezone.utc):
            problems.append("review timestamp is in the future")
    except (ValueError, TypeError):
        problems.append("review timestamp missing or invalid")
    return problems


def evaluate_shot(requirement: dict, asset: str | Path,
                  receipt: dict | None, mechanical: dict | None = None) -> dict[str, object]:
    """One beat's gate verdict.

    requirement: entry from the gate-requirements config (beat id, timing,
    required_actions as review inputs, dialogue lines).
    mechanical: precomputed detectors.mechanical_report for this asset, or
    None to compute it here.
    """
    beat = str(requirement.get("beat"))
    reasons: list[str] = []
    mechanical = mechanical if mechanical is not None else mechanical_report(asset)

    # A measured freeze is a hard asset defect: the bytes cannot carry the
    # scripted action. That is a reject, not a review pause.
    mechanical_reject = False
    for defect in mechanical.get("defects", []):
        if defect["type"] == "freeze":
            mechanical_reject = True
            reasons.append(
                f"mechanical freeze {defect['start']}-{defect['end']}s: "
                "a frozen window cannot carry scripted action or motion")

    if receipt is None:
        reasons.append("no review receipt: action, expression, lip sync and "
                       "continuity are unestablished, so the shot pauses for review")
        return {"beat": beat,
                "status": REJECTED if mechanical_reject else REVIEW_REQUIRED,
                "reasons": reasons,
                "mechanical_defects": mechanical.get("defects", [])}

    problems = _receipt_problems(receipt, asset)
    if str(receipt.get("beat")) != beat:
        problems.append("receipt belongs to another beat")
    if receipt.get("requirement_sha256") != requirement_sha256(requirement):
        problems.append("receipt is not bound to current requirements")
    if problems:
        return {"beat": beat, "status": REJECTED if mechanical_reject else REVIEW_REQUIRED,
                "reasons": reasons + problems,
                "mechanical_defects": mechanical.get("defects", [])}

    checks = receipt.get("checks", {})
    rejected = False
    for name in SHOT_REVIEW_CHECKS:
        value = checks.get(name)
        if value is False:
            rejected = True
            reasons.append(f"reviewer marked {name}=false")
        elif value is not True:
            reasons.append(f"{name} not established by review (pause, not pass)")

    # Strict reject: reviewer says a scripted action is absent, or the shot is
    # mechanically frozen. Either way the asset does not ship and no local
    # patch (still, crop, retime) is substituted by this gate.
    if rejected or mechanical_reject:
        status = REJECTED
    elif reasons:
        status = REVIEW_REQUIRED
    else:
        status = APPROVED
    return {"beat": beat, "status": status, "reasons": reasons,
            "mechanical_defects": mechanical.get("defects", []),
            "reviewer": receipt.get("reviewer"),
            "reviewed_at": receipt.get("reviewed_at")}


def gate_check(requirements: dict, assets: dict[str, str | Path],
               receipts: dict[str, dict] | None = None) -> dict[str, object]:
    """Evaluate every beat. assets/receipts are keyed by beat id."""
    validate_requirements(requirements)
    receipts = receipts or {}
    results = []
    expected = {str(b["beat"]) for b in requirements["beats"]}
    if set(assets) - expected:
        raise ValueError("Assets contain unexpected beats")
    for req in requirements["beats"]:
        beat = str(req["beat"])
        asset = assets.get(beat)
        if asset is None:
            results.append({"beat": beat, "status": REVIEW_REQUIRED,
                            "reasons": ["no asset supplied for this beat"]})
            continue
        results.append(evaluate_shot(req, asset, receipts.get(beat)))
    counts = {APPROVED: 0, REJECTED: 0, REVIEW_REQUIRED: 0}
    for r in results:
        counts[r["status"]] += 1
    return {
        "beats": results,
        "all_approved": counts[APPROVED] == len(results) and len(results) > 0,
        "counts": counts,
        "scope": ("Mechanical facts are measured. Actions, expressions, emotion "
                  "and lip sync come only from named human review receipts; "
                  "this gate enforces their presence, not their truth."),
    }


def evaluate_episode(assembled: str | Path, receipt: dict | None,
                     dialogue_windows: list[dict[str, float]] | None = None,
                     mechanical: dict | None = None) -> dict[str, object]:
    """Episode-level gate on the assembled file.

    Mechanical defects or a missing/incomplete episode receipt mean the file
    is a REVIEW CANDIDATE, never a finished episode.
    """
    mechanical = mechanical if mechanical is not None else mechanical_report(
        assembled, dialogue_windows=dialogue_windows)
    reasons = []
    for defect in mechanical.get("defects", []):
        reasons.append(f"mechanical {defect['type']} at {defect.get('start')}")
    if receipt is None:
        reasons.append("no episode review receipt: full playback and emotional "
                       "listen are unestablished")
    else:
        problems = _receipt_problems(receipt, assembled)
        reasons.extend(problems)
        if not problems:
            checks = receipt.get("checks", {})
            for name in EPISODE_REVIEW_CHECKS:
                if checks.get(name) is not True:
                    reasons.append(f"episode check {name} not established by review")
    status = APPROVED if not reasons else REVIEW_REQUIRED
    return {"status": status, "reasons": reasons,
            "mechanical_defects": mechanical.get("defects", []),
            "scope": ("APPROVED means: no mechanical defects and a named reviewer "
                      "states they watched the full file and listened for emotion. "
                      "It is not a guarantee of quality."),
           }


def load_receipts(receipts_dir: str | Path) -> dict[str, dict]:
    """Load every *.receipt.json in a directory, keyed by beat."""
    out: dict[str, dict] = {}
    root = Path(receipts_dir)
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*.receipt.json")):
        data = json.loads(path.read_text())
        if data.get("beat") is not None:
            key = str(data["beat"])
            if key in out:
                raise ValueError("Duplicate receipt for beat: " + key)
            out[key] = data
    return out
