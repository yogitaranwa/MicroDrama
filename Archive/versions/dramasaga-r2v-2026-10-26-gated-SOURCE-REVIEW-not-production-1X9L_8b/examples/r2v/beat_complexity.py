#!/usr/bin/env python3
"""Beat-complexity linter: flags the empirically observed frame-generation failure class.

Evidence base and LIMITS: two paid failures of ONE beat (s14 b1, main pixel verdicts 11:49 and 15:12)
motivated these rules. Two frames cannot isolate cause, so the rules are a screening heuristic for a
KNOWN risk pattern - not a proven causal model, and a "clean" census result does NOT certify the
visual feasibility of any beat. Only generated frames reviewed by main establish feasibility.
  1. Motion-state collapse: a still start frame asked to PROVE a completed motion or
     causal chain ("completes her spin", "still raised from the redirected spell",
     "fading shimmer") renders as a static pose instead.
  2. Actor-attribute migration: with two actors on screen, an action verb that is not
     syntactically bound to an actor in its clause ("jabbing a finger upward" following
     "his wand still raised") migrates to the wrong actor.

A frame prompt is text-only compositing: there is no per-actor layout/pose conditioning,
so prompt syntax is the ONLY binding mechanism. This linter makes the risk objective.

Rules (per beat, evaluated on the frame PROMPT - the model input):
  R1 multi_actor_actions : 2+ actors each carrying an action verb
  R2 single_actor_overload: one actor carrying 3+ distinct action verbs
  R3 ambiguous_binding   : action verb in a clause with no actor descriptor/possessive
  R4 motion_causality    : still must prove a completed/past motion or causal chain
  R5 fx_event_overload   : 2+ distinct FX events in a beat that also has people
Risk: high = R3 with R1, or 3+ flags; medium = 2 flags; watch = 1 flag.
"""
import json, re, sys

FEMALE = re.compile(r"\b(platinum[- ]blonde|woman in the green|draconia)\b", re.I)
MALE = re.compile(r"\b(black[- ]haired|boy in black|harry)\b", re.I)
AMBIENT = re.compile(r"\b(students|dancers|crowd|guests|onlookers|couples)\b", re.I)
ENTITY = re.compile(r"\b(suits? of armor|armor|masked figure|hooded figure|the figure)\b", re.I)
ENV_SUBJ = re.compile(r"\b(mist|fog|smoke|snow|ice|frost|candles?|flames?|spotlight|light|treeline|forest|floor|chandeliers? dim\w*)\b", re.I)
POSS = [(re.compile(r"\bher\b", re.I), "draconia"), (re.compile(r"\bhis\b", re.I), "harry"),
        (re.compile(r"\bshe\b", re.I), "draconia"), (re.compile(r"\bhe\b", re.I), "harry"),
        (re.compile(r"\bhim\b", re.I), "harry")]

# action-verb stems; matched with word boundary + inflection suffix
VERB_STEMS = ["turn", "jab", "rais", "spin", "spun", "duck", "lunge", "step", "grab",
              "pull", "push", "gestur", "point", "whirl", "recoil", "block", "cast(?!le)",
              "fire", "sweep", "kneel", "ris", "lean", "dodg", "twirl", "storm",
              "march", "reach", "aim", "hurl", "fling", "throw", "stagger", "shove",
              "drag", "lift", "lower", "bow", "wave", "danc", "cross", "stumbl"]
VERB_RE = re.compile(r"\b(" + "|".join(VERB_STEMS) + r")\w*\b", re.I)
NOUN_CONTEXT = [re.compile(p, re.I) for p in
    [r"dance[- ]floor", r"dance[- ]steps?", r"dance[- ]hold", r"mid-dance", r"dance positions?",
     r"bow-shaped", r"formal dance", r"next dance", r"the waltz", r"waltz grid", r"point of",
     r"dancing feet", r"dancing couples?", r"a steps? back", r"back a step", r"step by step"]]
# verbs that are set-dressing when bound to ambient crowds, not actor actions
AMBIENT_OK = {"danc", "step", "ris", "cross", "march"}

MOTION_CAUSALITY = re.compile(
    r"\b(complet\w+ (?:her |his |the )?\w*spin|fading|fallen|redirected|still \w+ing? from|"
    r"still raised|after \w+ing|mid-spin|post-spin|recoils? from|stagger\w* from|"
    r"just (?:dodged|cast|fired|thrown|blocked)|mid-stumble|mid-fall)\b", re.I)

# FX EVENTS (things happening), not ambient set dressing (ice/snow/candlelight excluded)
FX_EVENT = re.compile(r"\b(shield|spell|bolt|blast|hex|jinx|jet of|burst|explosion|"
                      r"groan\w*|sway\w*|spark\w*|firework\w*|ice crystal\w* forming|"
                      r"freez\w+|frost spread\w*)\w*\b", re.I)

CLAUSE_SPLIT = re.compile(r"[,;:\u2014]")


def _actors_in(clause):
    """Ordered (pos, actor) mentions: descriptors first, then possessives."""
    out = []
    for m in FEMALE.finditer(clause): out.append((m.start(), "draconia"))
    for m in MALE.finditer(clause): out.append((m.start(), "harry"))
    for rx, who in POSS:
        for m in rx.finditer(clause): out.append((m.start(), who))
    if AMBIENT.search(clause): out.append((CLAUSE_SPLIT.search(clause).start() if False else 10**6, "ambient"))
    out.sort()
    return out


def analyze_prompt(prompt):
    """Return per-beat analysis: actor->verbs, ambiguous clauses, flags with evidence."""
    actor_verbs = {}
    ambiguous = []           # (clause, verbs) with action verbs but no actor mention
    for raw in CLAUSE_SPLIT.split(prompt or ""):
        clause = raw.strip()
        if not clause:
            continue
        verbs = []
        for m in VERB_RE.finditer(clause):
            span = clause[max(0, m.start()-12):m.end()+12]
            if any(rx.search(span) for rx in NOUN_CONTEXT):
                continue
            verbs.append(m.group(0).lower())
        mentions = _actors_in(clause)
        ent = ENTITY.search(clause); env = ENV_SUBJ.search(clause)
        if not verbs:
            continue
        if not mentions and (ent or env):
            continue  # single non-human entity / environment owns its motion - no binding risk
        if not mentions:
            ambiguous.append((clause, verbs))
            continue
        # bind verbs: before first mention -> nearest following actor (subject-first prose);
        # between mentions -> previous actor; ambient crowds don't count as actors for R1
        real = [(p, a) for p, a in mentions if a != "ambient"]
        if not real:
            continue
        for vm in VERB_RE.finditer(clause):
            span = clause[max(0, vm.start()-12):vm.end()+12]
            if any(rx.search(span) for rx in NOUN_CONTEXT):
                continue
            v = vm.group(0).lower()
            owner = None
            for pos, a in real:
                if pos <= vm.start():
                    owner = a
            if owner is None:
                owner = real[0][1]
            stem = next(s for s in VERB_STEMS if v.startswith(s))
            actor_verbs.setdefault(owner, set()).add(stem)
    flags = []
    acting = [a for a, vs in actor_verbs.items() if vs - AMBIENT_OK or a in ("draconia", "harry")]
    acting = [a for a in acting if actor_verbs[a]]
    if len([a for a in acting if actor_verbs[a] - AMBIENT_OK]) >= 2:
        flags.append(("R1", "multi_actor_actions: " + ", ".join(
            "%s[%s]" % (a, "/".join(sorted(actor_verbs[a]))) for a in acting)))
    for a, vs in actor_verbs.items():
        if a in ("draconia", "harry") and len(vs) >= 3:
            flags.append(("R2", "single_actor_overload: %s[%s]" % (a, "/".join(sorted(vs)))))
    both_actors = bool(FEMALE.search(prompt or "")) and bool(MALE.search(prompt or ""))
    if ambiguous and both_actors:
        flags.append(("R3", "ambiguous_binding: " + " | ".join(
            "'%s' (%s)" % (c[:60], "/".join(v)) for c, v in ambiguous)))
    mc = [m.group(0) for m in MOTION_CAUSALITY.finditer(prompt or "")]
    if mc:
        flags.append(("R4", "motion_causality: " + ", ".join(sorted(set(mc)))))
    fx = sorted(set(m.group(0).lower() for m in FX_EVENT.finditer(prompt or "")))
    has_people = bool(FEMALE.search(prompt or "") or MALE.search(prompt or "") or
                      re.search(r"\b(her|his)\b", prompt or "", re.I))
    if has_people and len(fx) >= 2:
        flags.append(("R5", "fx_event_overload: " + ", ".join(fx)))
    n = len(flags)
    ids = {f[0] for f in flags}
    risk = "high" if (("R3" in ids and "R1" in ids) or n >= 3) else "medium" if n == 2 else "watch" if n == 1 else "clean"
    return {"actor_verbs": {a: sorted(v) for a, v in actor_verbs.items()},
            "flags": flags, "risk": risk}


def census(manifest_path):
    m = json.load(open(manifest_path))
    rows = []
    for s in m["shots"]:
        beats = s.get("beats") or []
        if not beats:
            beats = [{"id": None, "frame": {"prompt": ""}, "action": s.get("action", "")}]
        for b in beats:
            prompt = ((b.get("frame") or {}).get("prompt")) or ""
            a = analyze_prompt(prompt)
            rows.append({"shot": "%s:%s#b%s" % (s["episode"], s["shot"], b.get("id")),
                         "risk": a["risk"], "flags": a["flags"],
                         "actor_verbs": a["actor_verbs"],
                         "action": (b.get("action") or s.get("action") or "")[:110]})
    return rows


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "shot-manifest-wan30.json"
    rows = census(path)
    order = {"high": 0, "medium": 1, "watch": 2, "clean": 3}
    rows.sort(key=lambda r: (order[r["risk"]], r["shot"]))
    counts = {}
    for r in rows:
        counts[r["risk"]] = counts.get(r["risk"], 0) + 1
    print("CENSUS %s: %s" % (path, counts))
    for r in rows:
        if r["risk"] == "clean":
            continue
        print("\n%s [%s] %s" % (r["shot"], r["risk"].upper(), r["action"]))
        for rid, why in r["flags"]:
            print("   %s %s" % (rid, why))
