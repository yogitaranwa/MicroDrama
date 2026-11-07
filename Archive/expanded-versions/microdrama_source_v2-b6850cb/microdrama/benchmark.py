import json, os, csv, time, statistics
from .schema import Brief, Character
from .pipeline import run_episode
from .validate import validate_script
from .llm import extract_json

CASES = [
    Brief("A delivery rider is mocked at a luxury gala; he is secretly the owner of the company that runs the building.", [Character("Arjun", "30s rider in a worn jacket"), Character("Vikram", "arrogant hotel heir"), Character("Meera", "sharp-eyed event manager")], "hidden_identity", 60, "en"),
    Brief("A fired accountant returns as the auditor of the firm that framed her.", [Character("Nina", "40s accountant, calm"), Character("Mr. Rao", "smug CFO"), Character("Dev", "junior analyst, secret ally")], "revenge", 60, "en"),
    Brief("A bride finds her husband's message to another woman minutes before the wedding vows.", [Character("Kavya", "bride in red"), Character("Rohan", "groom"), Character("Sana", "bridesmaid")], "betrayal", 60, "hi"),
    Brief("An intern is forced into a contract marriage with her ruthless boss to save her father's shop.", [Character("Lena", "intern"), Character("Mr. Kane", "cold CEO"), Character("Sofia", "Kane's ex")], "ceo_romance", 60, "en"),
    Brief("A waitress is claimed in public by a feared alpha during a full-moon feast.", [Character("Ivy", "waitress"), Character("Kael", "alpha"), Character("Brann", "beta rival")], "supernatural", 60, "en"),
    Brief("A will reading reveals a hidden heir sitting in the room.", [Character("Isabel", "eldest daughter"), Character("Tomas", "family lawyer"), Character("Luca", "stranger in a plain suit")], "family_inheritance", 90, "es"),
]

RUBRIC = {
    "hook": "Is there instant conflict or a strong visual question in the first 3 seconds?",
    "emotional_target": "Do you clearly want someone punished or rescued?",
    "escalation": "Does every shot change the situation?",
    "twist": "Is there a reversal that flips power and feels earned by a planted detail?",
    "cliffhanger": "Does it end on a specific open question that makes you want episode 2?",
    "dialogue": "Is the dialogue short, blunt, quotable, with no filler?",
    "juice": "Does it have gossip, intrigue and drama like real top microdramas?",
    "visual_filmability": "Are shots concrete and producible with consistent characters and look?",
}

VIDEO_RUBRIC = {
    "voice_consistency": "Does each character keep the same voice across shots?",
    "character_consistency": "Do faces, outfits and age stay the same across shots?",
    "art_style_consistency": "Is the look and colour grade stable across the episode?",
    "audio_video_sync": "Do lips, sound and action line up?",
    "watchability": "Would you keep watching, relative to real microdramas and shorts?",
}

def auto_score(script, brief):
    issues = validate_script(script, brief)
    shots = script.shots
    words = [len(s.dialogue.split()) for s in shots if s.dialogue]
    speakers = {s.speaker for s in shots if s.speaker}
    return {
        "structural_issues": len(issues),
        "shot_count": len(shots),
        "avg_shot_s": round(statistics.mean(s.dur_s for s in shots), 2) if shots else 0,
        "avg_line_words": round(statistics.mean(words), 1) if words else 0,
        "max_line_words": max(words) if words else 0,
        "speaker_count": len(speakers),
        "has_cliffhanger_beat": int(bool(shots) and shots[-1].beat == "cliffhanger"),
        "hook_in_3s": int(bool(shots) and shots[0].beat == "hook" and shots[0].start_s <= 3),
    }

JUDGE_SYSTEM = "You are a strict viewer who watches hundreds of microdramas. Score honestly; most scripts deserve 4 to 6. Output only JSON."

def judge(llm, script, brief):
    rubric = "\n".join(f"- {k}: {v}" for k, v in RUBRIC.items())
    user = f"""Score this microdrama script 1 to 10 on each criterion.
{rubric}
Return {{"scores": {{criterion: int}}, "weakest": str, "fix": str}}.
SCRIPT:
{script.to_json()}"""
    d = extract_json(llm.complete(JUDGE_SYSTEM, user, temperature=0.0))
    d["mean"] = round(statistics.mean(d["scores"].values()), 2)
    return d

def run_benchmark(gen_llm, judge_llm, out_root, version, backend=None, cases=None, log=print):
    cases = cases or CASES
    out = os.path.join(out_root, version)
    os.makedirs(out, exist_ok=True)
    rows = []
    for i, b in enumerate(cases):
        t0 = time.time()
        r = run_episode(gen_llm, b, os.path.join(out, f"case_{i:02d}"), backend, log=log)
        row = {"case": i, "template": b.template, "language": b.language, "duration_s": b.duration_s,
               "gen_seconds": round(time.time() - t0, 1)}
        row.update(auto_score(r["script"], b))
        try:
            j = judge(judge_llm, r["script"], b)
            row["judge_mean"] = j["mean"]
            row["judge_scores"] = j["scores"]
            row["judge_weakest"] = j.get("weakest", "")
        except Exception as e:
            row["judge_mean"] = None
            row["judge_error"] = str(e)
        rows.append(row)
        log(f"case {i} {b.template}: judge={row['judge_mean']} issues={row['structural_issues']}")
    json.dump(rows, open(os.path.join(out, "results.json"), "w"), indent=1)
    write_human_sheet(out, cases)
    return rows

def write_human_sheet(out, cases, include_video=False):
    crit = dict(RUBRIC)
    if include_video:
        crit.update(VIDEO_RUBRIC)
    with open(os.path.join(out, "human_scoring.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case", "template"] + list(crit) + ["would_i_enjoy_it_1_10", "notes"])
        for i, b in enumerate(cases):
            w.writerow([i, b.template] + [""] * (len(crit) + 2))

def compare(out_root, v_old, v_new):
    a = {r["case"]: r for r in json.load(open(os.path.join(out_root, v_old, "results.json")))}
    b = {r["case"]: r for r in json.load(open(os.path.join(out_root, v_new, "results.json")))}
    lines = []
    for k in sorted(a):
        if k in b and a[k].get("judge_mean") is not None and b[k].get("judge_mean") is not None:
            lines.append((k, a[k]["judge_mean"], b[k]["judge_mean"], round(b[k]["judge_mean"] - a[k]["judge_mean"], 2)))
    avg = round(statistics.mean(x[3] for x in lines), 2) if lines else None
    return {"per_case": lines, "mean_delta": avg}
