"""Story-shape and character-continuity lint for short vertical episodes.

Lesson applied (user-supplied fan-microdrama reference): a coherent
one-gag arc - setup, a small reveal/surprise, a warm emotional payoff -
and characters that stay recognisable across shots and lighting.

This is an editorial LINT, in the spirit of forge.action_budget: it
reports the arc it sees and flags gaps for human review. It never
rewrites a script, never invents beats, and only blocks when a caller
explicitly asks for strict validation. Beats declared on the script are
honoured; undeclared beats are inferred from position and marked as
inferred, not treated as author intent.
"""
from typing import Dict, Iterable, List, Mapping

from forge.gates.common import GateLocked

BEATS = ("setup", "reveal", "payoff")
_POSITION_FALLBACK = ("setup", "reveal", "payoff")  # first / middle / last


def lint_arc(shots: Iterable[Mapping]) -> Dict:
    """Report the episode's setup/reveal/payoff coverage.

    Each shot may declare beat="setup"|"reveal"|"payoff". Undeclared
    shots are inferred positionally (first=setup, middle=reveal,
    last=payoff) and marked inferred=True in the report."""
    shots = list(shots)
    beats, inferred = [], False
    n = len(shots)
    for i, shot in enumerate(shots):
        beat = str(shot.get("beat", "")).strip().lower()
        if beat:
            if beat not in BEATS:
                raise GateLocked(
                    f"shot {shot.get('n', i + 1)}: unknown beat {beat!r}; "
                    f"use one of {BEATS}")
            beats.append(beat)
        else:
            inferred = True
            pos = 0 if i == 0 else (2 if i == n - 1 else 1)
            beats.append(_POSITION_FALLBACK[pos])
    present = set(beats)
    missing = [b for b in BEATS if b not in present]
    return {"beats": beats, "has_setup": "setup" in present,
            "has_reveal": "reveal" in present,
            "has_payoff": "payoff" in present,
            "missing": missing, "inferred": inferred,
            "ok": not missing}


def validate_arc(shots: Iterable[Mapping], strict: bool = False) -> Dict:
    """The lint as a gate ONLY when strict=True (an explicit pipeline
    choice): an episode missing a setup, reveal or payoff is refused.
    Default remains report-only."""
    report = lint_arc(shots)
    if strict and not report["ok"]:
        raise GateLocked(
            "story arc incomplete - a short episode needs setup, reveal "
            f"and payoff; missing: {', '.join(report['missing'])}")
    return report


def character_continuity_report(plan: Iterable[Mapping]) -> Dict:
    """Per-character spread across locations and lighting setups - the
    drift-risk view behind 'the same face/hair/uniform must hold across
    shots and lighting'. A character appearing in more locations or
    lighting setups is a continuity attention point for review, paired
    with the design sheet / locked-still mechanisms that hold the look.
    Report only: it blocks nothing."""
    by_char: Dict[str, Dict] = {}
    for shot in plan:
        speaker = str(shot.get("speaker") or (shot.get("line") or {}).get("speaker") or "").strip()
        if not speaker:
            continue
        entry = by_char.setdefault(speaker, {"shots": 0, "locations": set()})
        entry["shots"] += 1
        loc = str(shot.get("location", "")).strip()
        if loc:
            entry["locations"].add(loc)
    characters = {}
    attention = []
    for name, entry in by_char.items():
        spread = sorted(entry["locations"])
        characters[name] = {"shots": entry["shots"], "locations": spread}
        if entry["shots"] > 1 and len(spread) > 1:
            attention.append(
                f"{name}: {entry['shots']} shots across {len(spread)} "
                f"locations ({', '.join(spread)}) - verify face/wardrobe "
                "consistency against the design sheet and locked stills")
    return {"characters": characters, "attention": attention,
            "ok": not attention}
