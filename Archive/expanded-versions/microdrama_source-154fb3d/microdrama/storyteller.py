import json
from .schema import Script, Brief
from .templates import TEMPLATES, STRUCTURE, PRINCIPLES
from .llm import extract_json
from .validate import validate_script

SYSTEM = ("You are a head writer for top-performing vertical microdramas. You write tight shot-by-shot scripts "
          "that are addictive: instant hook, escalating conflict, a reversal, and a cliffhanger. "
          "Output only one JSON object, no prose.")

def beat_plan(duration_s):
    return [(n, round(a * duration_s, 1), round(b * duration_s, 1)) for n, a, b in STRUCTURE["beats"]]

def build_prompt(brief: Brief):
    t = TEMPLATES[brief.template]
    chars = "\n".join(f"- {c.name}: {c.description} (voice: {c.voice or 'natural'}; has reference image: {bool(c.ref_image)})" for c in brief.characters) or "- invent 2 to 4 characters"
    plan = "\n".join(f"- {n}: {a}s to {b}s" for n, a, b in beat_plan(brief.duration_s))
    scenes = "\n".join(f"- {s}" for s in brief.scenes) or "- none required"
    principles = "\n".join(f"{i+1}. {p}" for i, p in enumerate(PRINCIPLES))
    return f"""Write episode {brief.episode_number} of a microdrama.
Genre template: {t['name']}. Premise: {t['premise']}. Engine: {t['engine']}.
Hook ideas: {t['hook_patterns']}. Twist ideas: {t['twist_patterns']}. Cliffhanger ideas: {t['cliffhanger_patterns']}.
User story prompt: {brief.prompt}
Language of all dialogue: {brief.language}. Visual style: {brief.style}.
Total duration: {brief.duration_s} seconds. Shot length between {STRUCTURE['min_shot_s']} and {STRUCTURE['max_shot_s']} seconds. Max {STRUCTURE['max_words_per_second']} spoken words per second.
Characters (use only these names in the characters and speaker fields):
{chars}
Scenes the user requires:
{scenes}
Beat timing:
{plan}
Craft principles:
{principles}
JSON schema: {{"title": str, "logline": str, "cliffhanger": str, "next_episode_teaser": str,
"shots": [{{"idx": int, "start_s": float, "dur_s": float, "beat": "hook|setup|escalation|twist|cliffhanger",
"visual": str (concrete, filmable, includes setting, lighting, action), "camera": str, "characters": [names],
"speaker": name or null, "dialogue": str, "emotion": str, "sfx_music": str}}]}}
Shots must be contiguous, start at 0 and end at {brief.duration_s}."""

def write_script(llm, brief: Brief, max_attempts=3, log=print):
    prompt = build_prompt(brief)
    feedback = ""
    best = None
    for attempt in range(1, max_attempts + 1):
        raw = llm.complete(SYSTEM, prompt + feedback)
        try:
            script = Script.from_dict(extract_json(raw))
        except Exception as e:
            feedback = f"\nYour previous output was invalid ({e}). Return valid JSON only."
            log(f"attempt {attempt}: parse failure")
            continue
        issues = validate_script(script, brief)
        log(f"attempt {attempt}: {len(issues)} issues")
        if best is None or len(issues) < best[1]:
            best = (script, len(issues), issues)
        if not issues:
            return script, []
        feedback = "\nFix these problems and return the full corrected JSON:\n" + "\n".join("- " + i for i in issues)
    if best is None:
        raise RuntimeError("no valid script produced")
    return best[0], best[2]
