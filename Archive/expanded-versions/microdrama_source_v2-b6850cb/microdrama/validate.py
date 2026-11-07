from .templates import STRUCTURE

def validate_script(script, brief):
    issues = []
    names = {c.name for c in brief.characters}
    shots = script.shots
    if not shots:
        return ["no shots"]
    if abs(shots[0].start_s) > 0.01:
        issues.append("first shot must start at 0")
    t = 0.0
    for s in shots:
        if abs(s.start_s - t) > 0.25:
            issues.append(f"shot {s.idx} not contiguous (starts {s.start_s}, expected {round(t,1)})")
        if not STRUCTURE["min_shot_s"] - 0.01 <= s.dur_s <= STRUCTURE["max_shot_s"] + 0.01:
            issues.append(f"shot {s.idx} duration {s.dur_s}s outside limits")
        words = len(s.dialogue.split()) if s.dialogue else 0
        if s.dur_s > 0 and words / s.dur_s > STRUCTURE["max_words_per_second"] + 0.01:
            issues.append(f"shot {s.idx} dialogue too dense ({words} words in {s.dur_s}s)")
        if names:
            bad = [c for c in s.characters if c not in names]
            if bad:
                issues.append(f"shot {s.idx} uses unknown characters {bad}")
            if s.speaker and s.speaker not in names:
                issues.append(f"shot {s.idx} unknown speaker {s.speaker}")
        t = s.start_s + s.dur_s
    if abs(t - brief.duration_s) > 1.0:
        issues.append(f"total runtime {round(t,1)}s differs from target {brief.duration_s}s")
    if shots[0].beat != "hook" or shots[0].start_s > STRUCTURE["hook_window_s"]:
        issues.append("episode must open with a hook shot")
    if shots[-1].beat != "cliffhanger":
        issues.append("last shot must be the cliffhanger")
    beats = {s.beat for s in shots}
    for b in ("setup", "escalation", "twist"):
        if b not in beats:
            issues.append(f"missing beat: {b}")
    if not script.cliffhanger.strip():
        issues.append("cliffhanger field empty")
    for s in shots:
        if len(s.visual.split()) < 8:
            issues.append(f"shot {s.idx} visual too vague")
    return issues
