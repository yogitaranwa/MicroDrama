"""Story-state continuity for planned shots.

This tracks facts that pixel checks cannot see: where a character is, what a
prop's state is, and which character knows which revealed fact. It is additive:
plans without a ``continuity``/``state_changes`` field pass unchanged.
"""
from copy import deepcopy
from typing import Dict, Iterable, List, Mapping, Optional, Sequence


class ContinuityError(ValueError):
    pass


def _names(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def infer_characters(shots: Iterable[Mapping]) -> List[str]:
    seen: List[str] = []
    for shot in shots:
        for name in _names(shot.get("visible_characters")) + _names(shot.get("speaker")):
            if name and name not in seen:
                seen.append(name)
        for line in shot.get("lines") or []:
            name = line.get("speaker")
            if name and name not in seen:
                seen.append(name)
    return seen


def initial_state(characters: Sequence[str], props: Optional[Sequence[str]] = None) -> Dict:
    return {
        "characters": {name: {"facts": {}, "history": []} for name in characters},
        "props": {name: {"facts": {}, "history": []} for name in (props or [])},
        "knowledge": {},
    }


def _require_reason(change: Mapping) -> str:
    reason = str(change.get("reason", "")).strip()
    if len(reason) < 3:
        raise ContinuityError("state change needs an explicit story reason")
    return reason


def _entity_change(state: Dict, scope: str, change: Mapping, shot_label) -> Dict:
    name = str(change.get("name", "")).strip()
    field = str(change.get("field", "")).strip()
    if not name or not field:
        raise ContinuityError(f"{scope} change needs name and field")
    if "to" not in change:
        raise ContinuityError(f"{scope} change needs a new value in 'to'")
    bucket = state["characters" if scope == "character" else "props"]
    if name not in bucket:
        raise ContinuityError(f"unknown {scope} {name!r}")
    facts = bucket[name]["facts"]
    old = facts.get(field)
    if "from" in change and change["from"] != old:
        raise ContinuityError(
            f"{scope} {name!r}.{field} expected {change['from']!r}, found {old!r}")
    new = change["to"]
    if new == old:
        raise ContinuityError(f"{scope} {name!r}.{field} is already {new!r}")
    reason = _require_reason(change)
    facts[field] = new
    entry = {"shot": shot_label, "scope": scope, "name": name, "field": field,
             "from": old, "to": new, "reason": reason}
    bucket[name]["history"].append(entry)
    return entry


def _knowledge_change(state: Dict, change: Mapping, shot_label) -> Dict:
    fact = str(change.get("fact", change.get("name", ""))).strip()
    character = str(change.get("character", "")).strip()
    if not fact or not character:
        raise ContinuityError("knowledge change needs fact and character")
    if character not in state["characters"]:
        raise ContinuityError(f"unknown character {character!r}")
    reason = _require_reason(change)
    rec = state["knowledge"].setdefault(fact, {"known_by": [], "revealed_at": shot_label,
                                              "reveal_reason": reason})
    if character in rec["known_by"]:
        raise ContinuityError(f"{character!r} already knows {fact!r}")
    rec["known_by"].append(character)
    rec["known_by"].sort()
    return {"shot": shot_label, "scope": "knowledge", "fact": fact,
            "character": character, "reason": reason}


def apply_transition(state: Dict, change: Mapping, shot_label=None) -> Dict:
    scope = str(change.get("scope", change.get("kind", ""))).lower().strip()
    if scope in ("character", "prop"):
        return _entity_change(state, scope, change, shot_label)
    if scope == "knowledge":
        return _knowledge_change(state, change, shot_label)
    raise ContinuityError("continuity scope must be character, prop or knowledge")


def validate_plan_continuity(shots: Iterable[Mapping],
                             characters: Optional[Sequence[str]] = None,
                             props: Optional[Sequence[str]] = None) -> Dict:
    """Apply every shot's optional state changes and return a JSON ledger.

    If ``props`` is omitted, prop names are accepted on first use. Pass an
    explicit prop list when unknown-prop errors should be caught.
    """
    shots = list(shots)
    cast = list(characters) if characters is not None else infer_characters(shots)
    if props is None:
        inferred_props = []
        for shot in shots:
            for change in shot.get("continuity") or shot.get("state_changes") or []:
                scope = str(change.get("scope", change.get("kind", ""))).lower()
                name = str(change.get("name", "")).strip()
                if scope == "prop" and name and name not in inferred_props:
                    inferred_props.append(name)
        props = inferred_props
    state = initial_state(cast, props)
    changes: List[Dict] = []
    errors: List[Dict] = []
    for i, shot in enumerate(shots, 1):
        label = shot.get("plan_n", shot.get("n", i))
        for change in shot.get("continuity") or shot.get("state_changes") or []:
            try:
                changes.append(apply_transition(state, change, label))
            except ContinuityError as e:
                errors.append({"shot": label, "error": str(e), "change": dict(change)})
    return {"ok": not errors, "characters": cast, "props": list(props or []),
            "changes": changes, "errors": errors, "state": state}


def knowledge_known_by(state: Mapping, fact: str) -> List[str]:
    return list((state.get("knowledge", {}).get(fact) or {}).get("known_by", []))
