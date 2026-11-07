"""Live script generation: NVIDIA first via Instructor-validated schema. Writes JSON + readable text."""
import json, os, sys
from typing import List, Literal
from pydantic import BaseModel, Field
from forge.llm import Writer

import re
from pydantic import field_validator, model_validator

FILLERS = re.compile(r"\b(um+|uh+|er+|hmm+|ah+|like,|you know|i mean|kinda|sorta|whatever)\b|\.\.\.|--|—", re.I)

class Line(BaseModel):
    speaker: str
    text: str = Field(description="Two or three complete, grammatical English sentences, 18-45 words total, spoken aloud. No fillers, no fragments, no stage directions.")
    emotion: str = Field(description="delivery, e.g. 'barely controlled anger', 'shaky relief'")
    expression: str = Field(description="what the face/eyes/body do while speaking")

    @field_validator("text")
    @classmethod
    def full_sentences(cls, v):
        words = v.split()
        if not 16 <= len(words) <= 45:
            raise ValueError(f"line has {len(words)} words; need 16-45 in complete sentences")
        if FILLERS.search(v):
            raise ValueError("remove fillers, ellipses and dashes; write clean complete sentences")
        sents = [x for x in re.split(r"(?<=[.!?])\s+", v.strip()) if x]
        if len(sents) < 2 or any(len(x.split()) < 5 for x in sents) or v.strip()[-1] not in ".!?" or not v[0].isupper():
            raise ValueError("need at least two full sentences of 5+ words each, properly capitalised and punctuated")
        return v

class Shot(BaseModel):
    n: int
    location: str
    camera: str
    action: str
    lines: List[Line]
    seconds: int = Field(ge=4, le=15)

    @model_validator(mode="after")
    def time_fits_speech(self):
        words = sum(len(l.text.split()) for l in self.lines)
        if words and self.seconds < words / 3.0:
            raise ValueError(f"shot {self.n}: {words} words need at least {round(words/3.0)} s at normal speech pace")
        return self

class Episode(BaseModel):
    title: str
    hook: str
    shots: List[Shot] = Field(min_length=8, max_length=14)
    cliffhanger: str

    @model_validator(mode="after")
    def length(self):
        tot = sum(s.seconds for s in self.shots)
        if not 90 <= tot <= 120:
            raise ValueError(f"total runtime {tot}s; must be between 90 and 120 s")
        if sum(len(s.lines) for s in self.shots) < 12:
            raise ValueError("need at least 12 spoken lines across the episode")
        return self

CANON = """Canon sheet (follow strictly, invent nothing that contradicts it):
- Harry Potter: seventh year, Gryffindor, reserved and strategic, dry restrained humour, notices details, hides worry behind calm.
- Draconia Malfoy: female version of Draco, Slytherin, expressive and spontaneous, proud, quick tongue, vulnerable underneath. Her family name carries a heavy reputation. Do NOT give her a Dark Mark, do NOT call anyone a Death Eater, do NOT invent a dead relative.
- Setting: Hogwarts, the night of the Yule Ball. Harry and Draconia carry the dialogue; Pansy Parkinson, Argus Filch and Professor McGonagall may speak only in shots where the outline lists them, in one short line each (still complete sentences).
- Magic limited to wands, lumos, simple charms."""

BRIEF = CANON + """

Write episode 1 of a photorealistic vertical microdrama (9:16), total runtime 90 to 120 seconds.
Rivals who both suspect something about the other end up alone after a public clash at the ball.
DIALOGUE RULES (strict): every spoken line is two or three COMPLETE grammatical English sentences of 25 to 40 words (one or two lines per shot), in natural spoken English, with a clear thought, a feeling and a reason in it. Never write clipped two or three word replies, never use filler words, ellipses or dashes. Characters answer each other's actual point, reveal motive and emotion, and escalate.
Depth: each line carries a specific emotion and a physical expression (eyes, hands, breath, posture). Open on a hook in the first 3 seconds. End on a cliffhanger.
Use 8 to 11 shots, 10 to 14 seconds each where people talk, with location, camera, action, then lines with emotion and expression."""

class Beat(BaseModel):
    n: int
    sheet_step: str = ''
    turn: str = ''
    speakers: List[str] = []
    location: str
    camera: str
    action: str
    purpose: str = Field(description="what changes emotionally or in the plot in this shot")
    seconds: int = Field(ge=8, le=14)

class Outline(BaseModel):
    title: str
    hook: str
    beats: List[Beat] = Field(min_length=8, max_length=10)
    cliffhanger: str

    @model_validator(mode="after")
    def length(self):
        tot = sum(b.seconds for b in self.beats)
        if not 92 <= tot <= 118:
            raise ValueError(f"total runtime {tot}s; must be 92 to 118 s")
        return self

class ShotLines(BaseModel):
    seconds: int = 0
    lines: List[Line] = Field(min_length=1, max_length=3)

    def fits(self, seconds):
        words = sum(len(l.text.split()) for l in self.lines)
        if words > 85:
            raise ValueError(f"{words} words is too long for one shot; at most 85 words total")
        self.seconds = max(6, round(words / 4.6 + 0.6 * len(self.lines) + 1.0))  # 1.4x delivery, 0.6 s gaps
        return self



def write_plan_and_lint(shots, outdir="out"):
    """m11: derive the shot/reverse-shot plan and action-budget lint for a
    finished script. Additive outputs only: e01_plan.json is read by the
    render gate; e01_action_lint.json is a human-review report. The script
    itself is unchanged."""
    import json, pathlib
    from forge.dialogue_shots import expand_episode, plan_summary, verify_dialogue_preserved
    from forge.action_budget import lint_episode
    out = pathlib.Path(outdir); out.mkdir(parents=True, exist_ok=True)
    plan = expand_episode(shots)
    (out / "e01_plan.json").write_text(json.dumps(plan, indent=1))
    lint = lint_episode(shots)
    lint["plan_summary"] = plan_summary(plan)
    # m15: prove the plan kept the approved script's dialogue (exactly once,
    # in order, one line per clip). Reported with the lint for human review.
    lint["dialogue_check"] = verify_dialogue_preserved(shots, plan)
    (out / "e01_action_lint.json").write_text(json.dumps(lint, indent=1))
    return {"plan": plan, "lint": lint}


if __name__ == "__main__":
    import time, pathlib
    t0 = time.time()
    out = pathlib.Path("out/shots"); out.mkdir(parents=True, exist_ok=True)
    w = Writer(nvidia_key=open(os.environ["KEYFILE"]).read().strip(), stall_s=70, claude_key=None)
    of = pathlib.Path("out/outline.json")
    if of.exists():
        ol = Outline(**json.loads(of.read_text()))
    else:
        ol = w.structured(Outline, BRIEF, retries=1); of.write_text(ol.model_dump_json(indent=1))
    prior = []
    for b in ol.beats:
        f = out / f"{b.n:02d}.json"
        if f.exists():
            prior.append(json.loads(f.read_text())); continue
        if time.time() - t0 > 80:
            print("PAUSE: rerun to continue", b.n); break
        prompt = (CANON + f"\nEpisode: {ol.title}. Hook: {ol.hook}. Cliffhanger: {ol.cliffhanger}.\n"
                  f"Story so far (dialogue already written): {json.dumps([[l['speaker'], l['text']] for p in prior for l in p['lines']])[:2500]}\n"
                  f"Now write the spoken lines for shot {b.n}: location {b.location}; action {b.action}; purpose {b.purpose}; it lasts about {b.seconds} s; "
                  f"write two lines, 45 to 70 words in total. Each line: two or three COMPLETE grammatical English sentences of 25 to 40 words (one or two lines per shot), "
                  "specific emotion, physical expression, no fillers, no ellipses, no dashes, no clipped replies. Characters answer each other's actual point and escalate.")
        sl, err = None, ""
        for attempt in range(3):
            try:
                sl = w.structured(ShotLines, prompt + err, retries=0).fits(b.seconds); break
            except Exception as e:
                err = "\nPREVIOUS ATTEMPT REJECTED: " + str(e)[:300]; sl = None
        if sl is None:
            print("shot", b.n, "failed:", err[:700]); break
        f.write_text(json.dumps({"n": b.n, "seconds": sl.seconds, "lines": [l.model_dump() for l in sl.lines]}, indent=1))
        prior.append(json.loads(f.read_text()))
    done = [b for b in ol.beats if (out / f"{b.n:02d}.json").exists()]
    print("done", len(done), "of", len(ol.beats), "elapsed", round(time.time()-t0))
    if len(done) == len(ol.beats):
        with open("out/e01_script.txt", "w") as fh:
            tot = sum(json.loads((out / f"{b.n:02d}.json").read_text())["seconds"] for b in ol.beats)
            fh.write(f"{ol.title}\nHOOK: {ol.hook}\nTOTAL {tot}s\n\n")
            for b in ol.beats:
                fh.write(f"[{b.n}] {b.location} | {b.camera} | {b.seconds}s\n  {b.action}\n")
                for l in json.loads((out / f"{b.n:02d}.json").read_text())["lines"]:
                    fh.write(f"  {l['speaker']} ({l['emotion']}; {l['expression']}): {l['text']}\n")
            fh.write(f"\nCLIFFHANGER: {ol.cliffhanger}\n")
        scripted = []
        for b in ol.beats:
            d = json.loads((out / f"{b.n:02d}.json").read_text())
            scripted.append({"n": b.n, "location": b.location, "camera": b.camera,
                             "action": b.action, "seconds": d["seconds"], "lines": d["lines"]})
        res = write_plan_and_lint(scripted)
        print("planned", len(res["plan"]), "clips;", res["lint"]["n_flagged"], "shots over action budget")
