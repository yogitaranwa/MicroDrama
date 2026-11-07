"""Canonical Wan 3.0 production shot manifest, built from the ACCEPTED rev audio
(/tmp/rev/qa.json, per-line ASR-verified) + canonical scripts in work/scripts/.
Rules:
- dialogue shot seconds = ceil(accepted line duration + 0.5s visible-reaction tail), min 2, max 10
- action-only hold shots keep their designed durations from the script tables
- billing = shot seconds x 96 cr (720p Wan 3.0, audio included, integer durations 2-10)
- no rerolls included; probe clip NOT counted as passed
"""
import json, math, re
from pathlib import Path

QA = json.load(open("/tmp/rev/qa.json"))
SCRIPTS = {
    "e01": "/home/sandbox/work/scripts/E01-script-v3-human-dialogue.md",
    "e02": "/home/sandbox/work/scripts/E02-script-v2-human-dialogue.md",
    "e03": "/home/sandbox/work/scripts/E03-script-v2-human-dialogue.md",
}
TWO_BODY = re.compile(r"grabs his|spins harry|catches her|catches his|hauls him|pulls harry|drags him|dances? with|dancing together|offers his hand|they dance|they improvise|duels her|slashes at", re.I)
CLIFF = {("e01", 18), ("e02", 16), ("e03", 16)}

def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower())

manifest = []
for ep, path in SCRIPTS.items():
    rows = re.findall(r"^\| (\d+) \| (\d+)-(\d+) \| (.+?) \| (.*?) \|$", open(path).read(), re.M)
    lines = [e for e in QA if e["file"].startswith(ep)]
    used = set()
    for n, t0, t1, action, dialogue in rows:
        n = int(n); designed = int(t1) - int(t0)
        m = re.search(r'(HARRY|DRACONIA|CURSE).*?"(.+?)"', dialogue)
        shot = {"episode": ep, "shot": n, "designed_s": designed,
                "action": action.strip(), "speaker": None, "line": None,
                "line_dur": None, "shot_s": None, "billing_s": None,
                "refs": [], "two_body": bool(TWO_BODY.search(action)),
                "cliffhanger": (ep, n) in CLIFF}
        if m:
            speaker, text = m.group(1), m.group(2)
            nt = norm(text)
            best, bi = 0, None
            for i, e in enumerate(lines):
                if i in used: continue
                a, b = set(nt.split()), set(norm(e["text"]).split())
                sim = len(a & b) / max(1, len(a | b))
                if sim > best: best, bi = sim, i
            if bi is None or best < 0.6:
                shot["line"] = "UNMATCHED: " + text[:60]; shot["sim"] = round(best, 2)
            else:
                used.add(bi); e = lines[bi]
                shot.update(speaker=e["speaker"], line=e["text"][:70],
                            line_dur=float(e["dur_s"]), audio=e["file"],
                            asr_sim=e.get("asr_similarity"))
                shot["shot_s"] = min(10, max(2, math.ceil(float(e["dur_s"]) + 0.5)))
        if shot["shot_s"] is None:
            shot["shot_s"] = designed  # action hold keeps design
        shot["billing_s"] = shot["shot_s"]
        on = set()
        if shot.get("speaker"): on.add(shot["speaker"])
        if "draconia" in action.lower(): on.add("DRACONIA")
        if "harry" in action.lower(): on.add("HARRY")
        shot["refs"] = sorted(r.lower() for r in on if r != "CURSE")
        if not shot["refs"]:
            shot["refs"] = ["draconia", "harry"]  # two-lead story: unnamed "they/them" shots carry both leads
        manifest.append(shot)
    orphan = [e["file"] for i, e in enumerate(lines) if i not in used]
    if orphan: print("ORPHAN LINES", ep, orphan)

tot_s = sum(s["billing_s"] for s in manifest)
out = {"model": "wan-3.0", "res": "720p", "fps_actual_verified": 30, "rate_cr_per_s": 96,
       "rule": "dialogue shot = ceil(line+0.5s reaction), holds = design; no rerolls; probe not counted",
       "shots": manifest, "total_shots": len(manifest), "total_s": tot_s, "total_cr": tot_s * 96}
Path("/home/sandbox/work/DramaSaga-work/examples/r2v/shot-manifest-wan30.json").write_text(json.dumps(out, indent=1))
for ep in ("e01", "e02", "e03"):
    ss = [s for s in manifest if s["episode"] == ep]
    print(ep, len(ss), "shots,", sum(s["billing_s"] for s in ss), "s,", sum(s["billing_s"] for s in ss) * 96, "cr;",
          "two-body:", sum(1 for s in ss if s["two_body"]), "| >8s:", [(s["shot"], s["billing_s"]) for s in ss if s["billing_s"] > 8])
print("TOTAL", len(manifest), "shots,", tot_s, "s,", tot_s * 96, "cr")
print("unmatched:", [ (s["episode"], s["shot"]) for s in manifest if s.get("line","" ).startswith("UNMATCHED") if s.get("line")])
