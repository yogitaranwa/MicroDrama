"""Action-budget lint: keep every shot's visible action small enough that
dialogue and editing carry the tension.

Why this exists: overloaded shots (walk in AND sit AND pick something up AND
react, in ten seconds) are where identity and wardrobe drift shows up and
where pacing dies. The reference pattern was one small action per shot at
most - enter, or sit, or turn - with the conflict carried by what is said.
This lint reads scripted shots (or prompt text) and flags overload BEFORE a
prompt becomes a paid render. Pure stdlib heuristics; flags are for humans,
not verdicts.
"""
import re
from typing import Dict, List

# Visible-movement verbs that cost consistency when stacked in one shot.
ACTION_VERBS = re.compile(
    r"\b(walks?|runs?|crosses|enters?|exits?|leaves|sits?|stands?|rises?|"
    r"kneels?|lies|lay|turns?|spins?|picks? up|grabs?|takes?|throws?|tosses?|"
    r"opens?|closes?|slams?|pushes?|pulls?|draws?|raises?|lowers?|points?|"
    r"reaches?|touches?|grasps?|hugs?|kisses?|slaps?|hits?|paces?|storms?|"
    r"climbs?|descends?|follows?|approaches?|retreats?|backs? away|leans?)\b",
    re.I,
)

# Connectors that start a NEW action beat in prompt prose.
BEAT_SPLITTERS = re.compile(r"\b(?:and then|then|before|after that|while|as)\b|,|;|\.", re.I)

DEFAULT_MAX_ACTIONS = 2
HEAVY_DIALOGUE_WORDS = 20


def find_actions(text: str) -> List[str]:
    """Distinct visible-action verb phrases mentioned in the text."""
    seen: List[str] = []
    for m in ACTION_VERBS.finditer(text or ""):
        v = m.group(0).lower()
        if v not in seen:
            seen.append(v)
    return seen


def action_beats(text: str) -> int:
    """Approximate count of sequential action beats in prompt prose."""
    parts = [p for p in BEAT_SPLITTERS.split(text or "") if p.strip()]
    return max(1, len([p for p in parts if ACTION_VERBS.search(p)]))


def lint_shot(shot: Dict, max_actions: int = DEFAULT_MAX_ACTIONS) -> Dict:
    """shot: {"n", "action", "seconds", "lines": [{"speaker","text"}]}.
    Returns a flag report; 'overloaded' is the headline boolean."""
    action_text = shot.get("action", "") or ""
    verbs = find_actions(action_text)
    beats = action_beats(action_text)
    words = sum(len(l.get("text", "").split()) for l in shot.get("lines", []))
    flags: List[str] = []
    if len(verbs) > max_actions:
        flags.append(
            f"{len(verbs)} distinct movements ({', '.join(verbs)}); "
            f"keep at most {max_actions} and let the dialogue carry the rest")
    if beats > max_actions + 1:
        flags.append(f"~{beats} sequential action beats; split into separate shots")
    moving = [v for v in verbs if v.split()[0] in
              ("walk", "walks", "run", "runs", "crosses", "enter", "enters",
               "exit", "exits", "leaves", "paces", "storms", "climbs", "descends",
               "follows", "approaches", "retreats")]
    if moving and words > HEAVY_DIALOGUE_WORDS:
        flags.append(
            f"camera-blocking movement ({', '.join(moving)}) under {words} spoken words; "
            "hold the position for the speech or move the walk to its own shot")
    return {"shot": shot.get("n"), "actions": verbs, "beats": beats,
            "dialogue_words": words, "overloaded": bool(flags), "flags": flags}


def lint_episode(shots: List[Dict], max_actions: int = DEFAULT_MAX_ACTIONS) -> Dict:
    entries = [lint_shot(s, max_actions) for s in shots]
    flagged = [e for e in entries if e["overloaded"]]
    return {"shots": entries, "n_shots": len(entries), "n_flagged": len(flagged),
            "flagged_shots": [e["shot"] for e in flagged],
            "ok": not flagged}
