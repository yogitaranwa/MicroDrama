"""Shot/reverse-shot planning: split multi-speaker dialogue shots into
separate single-speaker shots, with optional silent listener reaction shots.

Why this exists: a reference scene that held identity and wardrobe across
every angle did it by never asking one long moving shot to carry both sides
of a conversation. Each generated clip showed ONE person speaking (or one
person reacting), so every clip was small enough to check and cheap enough
to replace. This module turns a written episode into that kind of plan.

Pure planning: no model calls, no credits. The output plan is still subject
to the normal gates (locked stills, proof scene, human review) before any
of its shots may be rendered.
"""
from typing import Dict, List, Optional

# Camera labels are text suggestions for the prompt/still stages, not
# commands to any renderer.
ANGLE_OTS = "over_shoulder"
ANGLE_REVERSE = "reverse"
ANGLE_REACTION = "reaction_closeup"
ANGLE_SINGLE = "single"
ANGLE_VISUAL = "visual"

REACTION_SECONDS = 1.5
QUESTION_MARKS = ("?",)


def _other_speaker(lines: List[Dict], speaker: str, characters: List[str]) -> Optional[str]:
    for c in characters:
        if c != speaker:
            return c
    for l in lines:
        if l.get("speaker") != speaker:
            return l.get("speaker")
    return None


def _characters(shots: List[Dict]) -> List[str]:
    seen: List[str] = []
    for s in shots:
        for l in s.get("lines", []):
            sp = l.get("speaker")
            if sp and sp not in seen:
                seen.append(sp)
    return seen


def split_dialogue_shot(shot: Dict, characters: List[str],
                        insert_reactions: bool = True) -> List[Dict]:
    """Expand one scripted shot into single-speaker planned shots.

    shot: {"n", "location", "camera", "action", "seconds",
           "lines": [{"speaker", "text", ...}]}

    Returns a list of planned shots. Each planned shot carries at most ONE
    spoken line: two speakers never share a generated clip. Reaction shots
    (kind == "reaction") are silent close-ups of the listener, inserted only
    where a line ends with a question and the next line is a different
    speaker answering it - the beat where the audience wants the listener's
    face. Shot order and total dialogue are preserved exactly.
    """
    lines = list(shot.get("lines", []))
    base = {"src_shot": shot.get("n"), "location": shot.get("location", ""),
            "action": shot.get("action", "")}
    if not lines:
        return [dict(base, sub=1, kind="visual", speaker=None, line=None,
                     camera=ANGLE_VISUAL, seconds=float(shot.get("seconds", 4)))]
    if len(lines) == 1:
        sp = lines[0]["speaker"]
        return [dict(base, sub=1, kind="speaker", speaker=sp, line=lines[0],
                     camera=f"{ANGLE_SINGLE}:{sp}", seconds=float(shot.get("seconds", 6)))]

    # Weight the source shot's seconds across its lines by word count.
    words = [max(1, len(l.get("text", "").split())) for l in lines]
    total_w = float(sum(words))
    total_s = float(shot.get("seconds", 6))
    speakers = [l.get("speaker") for l in lines]
    primary = speakers[0]

    planned: List[Dict] = []
    for i, (line, w) in enumerate(zip(lines, words)):
        sp = line.get("speaker")
        over = _other_speaker(lines, sp, characters)
        if sp == primary:
            cam = f"{ANGLE_OTS}:{sp}" + (f"_over_{over}" if over else "")
        else:
            cam = f"{ANGLE_REVERSE}:{sp}" + (f"_over_{over}" if over else "")
        secs = max(2.0, round(total_s * w / total_w, 1))
        planned.append(dict(base, sub=len(planned) + 1, kind="speaker", speaker=sp,
                            line=line, camera=cam, seconds=secs))
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        if (insert_reactions and nxt is not None and nxt.get("speaker") != sp
                and line.get("text", "").rstrip().endswith(QUESTION_MARKS)):
            planned.append(dict(base, sub=len(planned) + 1, kind="reaction",
                                speaker=nxt.get("speaker"), line=None,
                                camera=f"{ANGLE_REACTION}:{nxt.get('speaker')}",
                                seconds=REACTION_SECONDS))
    return planned


def expand_episode(shots: List[Dict], insert_reactions: bool = True) -> List[Dict]:
    """Expand every scripted shot. Returns the flat planned shot list with a
    continuous 'plan_n' numbering; source shot numbers stay in 'src_shot'."""
    characters = _characters(shots)
    planned: List[Dict] = []
    for shot in shots:
        planned.extend(split_dialogue_shot(shot, characters, insert_reactions))
    for i, p in enumerate(planned, 1):
        p["plan_n"] = i
    return planned


def _clip_lines(p: Dict) -> List[Dict]:
    """All dialogue lines a planned clip carries, however they were stored."""
    line = p.get("line")
    lines = p.get("lines")
    out: List[Dict] = []
    if isinstance(line, dict):
        out.append(line)
    elif isinstance(line, list):
        out.extend(l for l in line if isinstance(l, dict))
    if isinstance(lines, list):
        out.extend(l for l in lines if isinstance(l, dict))
    return out


def plan_summary(planned: List[Dict]) -> Dict:
    """Counts used by reports and by the angle-still gate."""
    kinds: Dict[str, int] = {}
    for p in planned:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    speakers = sorted({p["speaker"] for p in planned if p.get("speaker")})
    # A planned clip must carry at most ONE spoken line: two speakers sharing
    # one generated clip is exactly the failure this planner exists to avoid.
    bad = [p["plan_n"] for p in planned if len(_clip_lines(p)) > 1]
    return {"planned_shots": len(planned), "by_kind": kinds,
            "speakers": speakers, "multi_speaker_clips": bad,
            "total_seconds": round(sum(float(p.get("seconds", 0)) for p in planned), 1),
            "reaction_seconds": round(sum(p["seconds"] for p in planned
                                          if p["kind"] == "reaction"), 1)}


def verify_dialogue_preserved(script_shots: List[Dict], planned: List[Dict]) -> Dict:
    """Prove the expansion kept the script's dialogue: every scripted
    (speaker, text) line must appear exactly once across the planned clips,
    in script order, and no planned clip may carry more than one line.

    This is the regression guard for 'shot order and total dialogue are
    preserved exactly': a dropped, duplicated or reordered line means the
    render plan no longer matches the script that was approved.
    """
    expected = [(l.get("speaker"), (l.get("text") or "").strip())
                for s in script_shots for l in s.get("lines", [])]
    actual: List = []
    for p in planned:
        for l in _clip_lines(p):
            actual.append((l.get("speaker"), (l.get("text") or "").strip()))
    used = [False] * len(actual)
    missing: List = []
    order_broken: List = []
    pos = 0
    for item in expected:
        found = next((j for j in range(pos, len(actual))
                      if not used[j] and actual[j] == item), None)
        if found is not None:
            used[found] = True
            pos = found + 1
            continue
        earlier = next((j for j in range(pos)
                        if not used[j] and actual[j] == item), None)
        if earlier is not None:
            used[earlier] = True
            order_broken.append({"speaker": item[0], "text": item[1][:80]})
        else:
            missing.append({"speaker": item[0], "text": item[1][:80]})
    duplicated = [{"speaker": actual[j][0], "text": actual[j][1][:80]}
                  for j in range(len(actual)) if not used[j]]
    multi = [p.get("plan_n") for p in planned if len(_clip_lines(p)) > 1]
    ok = not missing and not duplicated and not order_broken and not multi
    return {"ok": ok, "script_lines": len(expected), "planned_lines": len(actual),
            "missing": missing, "duplicated": duplicated,
            "order_broken": order_broken, "multi_line_clips": multi}
