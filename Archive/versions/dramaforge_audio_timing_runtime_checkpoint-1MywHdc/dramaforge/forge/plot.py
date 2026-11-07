"""Plot stage as a LangGraph (MIT): develop_story -> beat outline -> judge -> (revise) -> done.
Reuses ViMax's Screenwriter story-development prompt (MIT) and a DSPy (MIT) judge signature.
Resumable: every stage caches to out/plot/*.json."""
import json, os, pathlib, re
from typing import List, TypedDict
from pydantic import BaseModel, Field, model_validator
from langgraph.graph import StateGraph, END
import dspy
from forge.llm import Writer, NVIDIA_URL
from forge.script_run import CANON

OUT = pathlib.Path("out/plot"); OUT.mkdir(parents=True, exist_ok=True)

CAST = """Cast (canon-safe): Harry Potter, Draconia Malfoy (leads). Side characters allowed, at most two, speaking briefly or seen:
Argus Filch (caretaker, suspicious, wheezy menace), Pansy Parkinson (Slytherin, jealous gossip), Professor McGonagall (stern, fair)."""

# Beat sheet for a 90-120 s vertical microdrama (Save-the-Cat style, compressed)
BEAT_SHEET = ["HOOK (0-3s): a shocking image or line", "INCITING: a secret object or fact surfaces",
              "ESCALATION 1: a new location and a new obstacle", "ESCALATION 2: a side character raises the stakes",
              "REVERSAL: one lead learns the other lied or was right", "ALL IS LOST: trust breaks or danger arrives",
              "CHOICE: a risky act that costs something", "CLIFFHANGER: a revelation or threat that demands episode 2"]

BANNED = re.compile(r"dark mark|death eater|riddle|voldemort|you-know-who|bloodline|horcrux|marauder|patronus|thestral|dead (father|mother|brother|sister)", re.I)

class Beat(BaseModel):
    n: int
    sheet_step: str = Field(description="which beat sheet step this shot serves")
    location: str = Field(description="a specific Hogwarts place; must differ from the previous shot")
    camera: str
    action: str = Field(description="what visibly HAPPENS: a movement, discovery or event, not just feelings")
    turn: str = Field(description="what changes in the plot in this shot (new info, new danger, decision)")
    speakers: List[str]
    seconds: int = Field(ge=8, le=14)

class Outline(BaseModel):
    title: str
    hook: str = Field(description="the first line or image, must create a question in 3 seconds")
    beats: List[Beat] = Field(min_length=8, max_length=10)
    cliffhanger: str = Field(description="a concrete reveal or threat, not a mood")

    @model_validator(mode="after")
    def checks(self):
        blob = self.model_dump_json()
        m = BANNED.search(blob)
        if m:
            raise ValueError(f"canon violation: '{m.group(0)}' is not allowed; keep the mystery small (a missing object, a secret meeting, a rule broken), no Dark Lord plots")
        locs = [b.location.strip().lower() for b in self.beats]
        PLACES = ["staircase","great hall","astronomy","library","greenhouse","dungeon","owlery","courtyard","lake","grounds","forest","hospital","kitchen","common room","trophy","bathroom","room of requirement","clock tower","quidditch","corridor","gallery","entrance hall","office"]
        def place(l): return next((k for k in PLACES if k in l), l)
        roots = [place(l) for l in locs]
        if len(set(roots)) < 6:
            raise ValueError(f"only {len(set(roots))} truly different places {sorted(set(roots))}; need 6 or more. No more than 2 shots in the same tower or area; use e.g. grand staircase, library, greenhouse, dungeons, Owlery, kitchens, lake, Room of Requirement")
        if max(roots.count(r) for r in set(roots)) > 2:
            raise ValueError("no more than two shots may share the same place; move the story across the castle")
        if len(set(locs)) < 5:
            raise ValueError(f"only {len(set(locs))} distinct locations; need at least 5")
        if any(a == b for a, b in zip(locs, locs[1:])):
            raise ValueError("two consecutive shots share a location; move the story every shot")
        if len({b.turn.strip().lower() for b in self.beats}) < len(self.beats):
            raise ValueError("every shot needs a different plot turn")
        tot = sum(b.seconds for b in self.beats)
        if not 86 <= tot <= 118:
            raise ValueError(f"total runtime {tot}s; need 86 to 118 s")
        if not any(s not in ("Harry Potter", "Draconia Malfoy", "Harry", "Draconia") for b in self.beats for s in b.speakers):
            raise ValueError("include at least one side character appearing in the story")
        return self

class JudgeSig(dspy.Signature):
    """Judge a 90-second vertical microdrama outline for short-form retention. Be strict and concrete."""
    outline: str = dspy.InputField()
    hook_score: int = dspy.OutputField(desc="0-10: does the first 3 seconds create a burning question")
    escalation_score: int = dspy.OutputField(desc="0-10: does each shot raise stakes or change the situation")
    variety_score: int = dspy.OutputField(desc="0-10: locations, side characters and visuals vary")
    cliffhanger_score: int = dspy.OutputField(desc="0-10: does the ending force a click to episode 2")
    fix: str = dspy.OutputField(desc="the two most valuable concrete changes, one sentence each")

class State(TypedDict, total=False):
    story: str; outline: dict; scores: dict; rounds: int

def build(writer: Writer, key: str, min_score=8, max_rounds=2):
    lm = dspy.LM("openai/nvidia/nemotron-3-ultra-550b-a55b", api_base=NVIDIA_URL, api_key=key,
                 extra_body={"chat_template_kwargs": {"enable_thinking": False}}, temperature=0.3, timeout=70)
    judge = dspy.Predict(JudgeSig)

    def develop(s: State):
        f = OUT / "story.txt"
        if f.exists(): return {"story": f.read_text(), "rounds": 0}
        from agents.screenwriter import system_prompt_template_develop_story as VIMAX_PROMPT  # ViMax (MIT)
        sysmsg = VIMAX_PROMPT.split("[Input]")[0]  # role + task from ViMax; our own idea below
        idea = (CANON + "\n" + CAST + "\nIdea: Draconia and Harry, rivals, slip away from the Yule Ball after a public clash. "
                "Each hides a private reason for leaving: Harry is chasing who has been stealing items from Filch's confiscated-goods cabinet, Draconia is secretly meeting someone she must not be seen with. Their paths collide, they cross the castle together, and the truth about the theft changes how they see each other. Keep the stakes personal and school-sized: no Dark Lord, no Dark Mark, no ancestors.")
        req = "Microdrama, 8 scenes in different castle locations, twist ending, cliffhanger, 90 seconds. Young adults. Romance with tension."
        from openai import OpenAI
        c = OpenAI(base_url=NVIDIA_URL, api_key=key, timeout=100, max_retries=0)
        r = c.chat.completions.create(model="nvidia/nemotron-3.5-lightning-30b-a3b", messages=[{"role": "system", "content": sysmsg},
            {"role": "user", "content": f"<IDEA>{idea}</IDEA>\n<USER_REQUIREMENT>{req}</USER_REQUIREMENT>"}],
            extra_body={"chat_template_kwargs": {"enable_thinking": False}}, max_tokens=1100)
        t = r.choices[0].message.content; f.write_text(t); return {"story": t, "rounds": 0}

    def outline(s: State):
        f = OUT / f"outline_r{s.get('rounds',0)}.json"
        if f.exists(): return {"outline": json.loads(f.read_text())}
        fix = s.get("scores", {}).get("fix", "")
        p = (CANON + "\n" + CAST + "\nBeat sheet to follow, one step per shot: " + " | ".join(BEAT_SHEET) +
             f"\nStory treatment:\n{s['story'][:3500]}\nTurn this into a shot outline. The plot MUST move every shot: new location each shot, "
             "a visible event, a different turn each time, a hard cliffhanger revelation." + (f"\nJudge feedback to fix: {fix}" if fix else ""))
        ol, err = None, ""
        for _ in range(3):
            try: ol = writer.structured(Outline, p + err, retries=0); break
            except Exception as e: err = "\nPREVIOUS ATTEMPT REJECTED: " + str(e)[:300]
        if ol is None: raise RuntimeError("outline failed: " + err)
        f.write_text(ol.model_dump_json(indent=1)); return {"outline": ol.model_dump()}

    def score(s: State):
        sf = OUT / f"scores_r{s.get('rounds',0)}.json"
        if sf.exists():
            sc = json.loads(sf.read_text()); return {"scores": sc, "rounds": s.get("rounds", 0) + 1}
        with dspy.context(lm=lm):
            r = judge(outline=json.dumps(s["outline"]))
        sc = {k: int(getattr(r, k)) for k in ("hook_score", "escalation_score", "variety_score", "cliffhanger_score")}
        sc["fix"] = r.fix; (OUT / f"scores_r{s.get('rounds',0)}.json").write_text(json.dumps(sc, indent=1))
        return {"scores": sc, "rounds": s.get("rounds", 0) + 1}

    def route(s: State):
        ok = min(v for k, v in s["scores"].items() if k != "fix") >= min_score
        return END if ok or s["rounds"] > max_rounds else "outline"

    g = StateGraph(State)
    g.add_node("develop", develop); g.add_node("outline", outline); g.add_node("score", score)
    g.set_entry_point("develop"); g.add_edge("develop", "outline"); g.add_edge("outline", "score")
    g.add_conditional_edges("score", route, {END: END, "outline": "outline"})
    return g.compile()

if __name__ == "__main__":
    key = open(os.environ["KEYFILE"]).read().strip()
    w = Writer(nvidia_key=key, stall_s=70, claude_key=None)
    res = build(w, key).invoke({})
    print(json.dumps(res["scores"], indent=1)); pathlib.Path("out/outline_new.json").write_text(json.dumps(res["outline"], indent=1))
