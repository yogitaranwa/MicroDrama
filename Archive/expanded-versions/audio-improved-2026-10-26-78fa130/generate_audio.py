"""Improved emotional voice pass for E01-E03, per user direction 2026-10-26
("please make the audio first then / permission granted").

Scope grounding: ElevenLabs Creator, 120,275 chars remaining of included
allowance (live read 02:27), need <= 2,851 chars worst case. Within the
recorded grant: included characters only, auto top-up OFF (verified:
can_extend_character_limit=false). No new dollars.

Per-line generation with the verified v3 tag lexicon, stability 0.35 for
broader emotional range (ElevenLabs docs: lower stability broadens range),
no speed field (does not exist on this API) - briskness directed by
[rushed]/[urgent] tags and measured afterward against the WAVs.
"""
import json, re, subprocess, sys, time
from pathlib import Path
import requests

KEY = Path(open('/tmp/elkey.path').read().strip()).read_text().strip()
LEX = {"[angry]","[whispers]","[sad]","[curious]","[nervous]","[excited]","[softly]","[laughs]","[sighs]","[rushed]","[urgent]","[interrupting]"}
VOICES = {"HARRY": "4dZr8J4CBeokyRkTRpoN", "DRACONIA": "ZF6FPAbjXT4488VcRRnw"}
OUT = Path('/home/sandbox/work/audio-2026-10-26')

EPISODES = {
    "e01": "/home/sandbox/work/DramaSaga-work/docs/E01-script-v2-detailing-addendum.md",
    "e02": "/home/sandbox/work/scripts/E02-script-v1-detailed.md",
    "e03": "/home/sandbox/work/scripts/E03-script-v1-detailed.md",
}

def parse(path):
    rows = []
    for m in re.finditer(r'^(\d+)\.\s+(HARRY|DRACONIA|CURSE)\s+"([^"]+)"\s*-\s*(.+)$', open(path).read(), re.M):
        n, spk, text, detail = m.groups()
        tags = [t for t in re.findall(r'\[[a-z]+\]', detail) if t in LEX][:2]
        rows.append({"n": int(n), "speaker": spk, "text": text, "tags": tags})
    return rows

def duration(p):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())

def main():
    qa = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "model": "eleven_v3",
          "settings": {"stability": 0.35, "similarity_boost": 0.75},
          "episodes": {}, "skipped": []}
    chars = 0
    for ep, path in EPISODES.items():
        rows = parse(path)
        epdir = OUT / ep; epdir.mkdir(exist_ok=True)
        entries = []
        for row in rows:
            if row["speaker"] == "CURSE":
                qa["skipped"].append({"episode": ep, "line": row["n"], "reason": "no accepted voice id for CURSE; needs voice selection"})
                continue
            text = " ".join(row["tags"] + [row["text"]])
            vid = VOICES[row["speaker"]]
            chars += len(text)
            out = epdir / ("%s-line-%02d.mp3" % (ep, row["n"]))
            r = requests.post(
                "https://api.elevenlabs.io/v1/text-to-speech/%s?output_format=mp3_44100_128" % vid,
                headers={"xi-api-key": KEY, "Content-Type": "application/json"},
                json={"text": text, "model_id": "eleven_v3",
                      "voice_settings": {"stability": 0.35, "similarity_boost": 0.75}},
                timeout=120)
            if r.status_code != 200:
                print("STOP %s line %d: HTTP %s %s" % (ep, row["n"], r.status_code, r.text[:300]))
                (OUT / "qa.json").write_text(json.dumps(qa, indent=1))
                sys.exit(2)
            out.write_bytes(r.content)
            entries.append({"line": row["n"], "speaker": row["speaker"], "tags": row["tags"],
                            "chars": len(text), "file": out.name, "seconds": round(duration(out), 3)})
            print(ep, row["n"], row["speaker"], row["tags"], entries[-1]["seconds"], "s")
            time.sleep(0.3)
        qa["episodes"][ep] = {"lines": entries, "total_dialogue_seconds": round(sum(e["seconds"] for e in entries), 2)}
    qa["submitted_characters"] = chars
    (OUT / "qa.json").write_text(json.dumps(qa, indent=1))
    print("TOTAL submitted chars:", chars)

main()
