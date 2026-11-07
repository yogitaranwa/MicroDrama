"""E01 v9: 4 locations, one line per shot, 4 prop inserts. Writes shots JSON, lines JSON and a readable shot list."""
import json, re
D, H, F, P, M = "Draconia Malfoy", "Harry Potter", "Argus Filch", "Pansy Parkinson", "Professor McGonagall"
LOC = {
 "A": ("Corridor outside the Great Hall", "warm amber candlelight, 2700K", "A"),
 "B": ("Hidden passage behind the tapestry", "cool teal-blue, 6500K, damp stone", "B"),
 "C": ("Seventh-floor corridor, Room of Requirement wall", "blown-out white-gold doorway glow, overexposed highlights", "C"),
 "D": ("Astronomy Tower stairwell", "cold silver moonlight, deep blue shadows", "D"),
}
OUTFIT = {D: "emerald ball gown with black travelling cloak, braid", H: "charcoal dress robes, loosened collar",
          P: "dark green velvet dress", M: "emerald-trimmed black robes, tartan shawl", F: "grey greatcoat, lantern"}
S = []
def shot(loc, kind, cam, action, sp=None, text=None, emo=None, e=None, c=None, sec=None, bg=None):
    S.append(dict(loc=loc, kind=kind, camera=cam, action=action, speaker=sp, text=text, emotion=emo, e=e, c=c, seconds=sec, background=bg))
BG = "background students dark, soft-focus, on screen under 2 s"
shot("A","line","ECU, finger-to-lips inches from lens, 85mm","Draconia presses a finger to her lips, eyes cutting to the corner. Hook.",D,
 "Do not even breathe, Potter. Filch is ten steps away, and if he catches us out of bed tonight, I lose far more than a Saturday.","urgent whisper, fear under bravado",0.6,0.3)
shot("A","insert","Macro, 100mm","Filch's lantern swings into frame, light sliding under a stone doorway.")
shot("A","line","Close-up Harry, 50mm","Harry's eyes flick from the lantern light to her face, a half smile he cannot hide.",H,
 "You promised me the party would be dull and safe, Malfoy. I am beginning to think you lied about both.","dry amusement over tension",0.35,0.5)
shot("A","line","Close-up Draconia, 85mm","She lifts her chin, stung and delighted at once.",D,
 "I never lie, I only choose which truths to share. Besides, I do not run from anyone, and I will not start with a caretaker.","proud, indignant, secretly thrilled",0.8,0.3)
shot("A","line","Medium-wide, Filch enters from the corridor end, handheld","Filch shuffles into the amber light, lantern raised, " + BG + " behind him.",F,
 "I can smell perfume and mischief in this corridor, my sweet little rule breakers. Come out now, and I may only hang you by your thumbs.","wheezing menace, relishing it",0.6,0.3,bg=BG)
shot("A","line","Close-up Harry, 35mm, push-in","Harry grabs her wrist and nods at a tapestry.",H,
 "Take my hand and follow me behind that tapestry before he reaches us. We can argue about your dignity once we are out of sight.","controlled urgency, a flash of command",0.5,0.4)
shot("B","line","Handheld follow, low angle, cool teal","They stumble through the passage. Dust, dripping stone.",H,
 "For someone who never runs from anyone, you are moving remarkably fast through this tunnel, Malfoy. I am barely keeping up.","teasing, breathless",0.45,0.4)
shot("B","line","Close-up Draconia, 50mm","She brushes grime from her gown, furious and trying not to laugh.",D,
 "This is a strategic retreat conducted with great dignity. The ruined hem of this gown is entirely your fault.","mock outrage, laughter fighting through",0.7,0.3)
shot("B","insert","Macro, 100mm","Harry's hand unfolds a crumpled parchment sealed with the initials B.P.")
shot("B","line","Two-shot, Harry in foreground, rack focus","Harry holds the note up between them.",H,
 "I found this note outside the ballroom, and it carries Pansy's initials. She was waiting for you tonight, and I need to understand why.","quiet, probing, genuinely worried",0.35,0.5)
shot("B","line","ECU Draconia's eyes, 100mm","Her eyes harden. Her hand snaps toward the parchment.",D,
 "Give me that parchment this instant, Potter. Whatever Pansy knows about my family is my burden, and I will not let you read a single line.","cold fear turning to rage",1.0,0.2)
shot("B","line","Silhouette at tunnel mouth, shallow focus, face unseen","Pansy's outline stands in the dark where the tunnel opens, " + BG + ".",P,
 "How very touching, Draco, and how typical of you. My father's owl reaches Lucius by dawn, unless you hand me your prefect badge tomorrow morning. Consider it the price of my silence.","silky, smug, savouring the threat",0.9,0.2,bg=BG)
shot("B","line","Close-up Draconia, 85mm, slight Dutch tilt","She steps toward the silhouette, voice cracking at the edges.",D,
 "You have always hidden behind your father's name, Parkinson. Step into the light and say that to my face if you dare.","wounded fury, voice shaking",0.9,0.25)
shot("B","line","Close-up Harry, 50mm","The silhouette is gone. Harry lowers his voice, piecing it together.",H,
 "Three nights ago I found Polyjuice ingredients in her trunk, and every missing one has led here. She used your scandal as a distraction while she stole.","slow realisation, steady voice",0.5,0.45)
shot("B","line","Close-up Draconia, 85mm, soft key","The anger drains out of her face, replaced by something raw.",D,
 "She played me from the very beginning, and I thought I was the one hunting her. We have been chasing the same snake in opposite directions all night.","stunned, softer, hurt and relieved",0.55,0.4)
shot("C","insert","Macro, 100mm, blown-out white-gold","A glass vial rolls across the flagstones into a pool of doorway light.")
shot("C","line","Medium close-up, McGonagall in doorway glow, backlit","McGonagall's silhouette fills the glowing doorway.",M,
 "Potter, Malfoy, stay exactly where you are. Two students missing from the ball and a caretaker shouting about shadows is no coincidence.","stern, tired authority",0.35,0.55)
shot("C","line","Close-up Harry, 35mm, overexposed edges","Harry holds up the vial, stepping forward.",H,
 "Professor, someone is brewing Polyjuice inside the Room of Requirement tonight. I found this vial by the tapestry, and I can prove it if you let us look.","bold, quick, pleading",0.5,0.4)
shot("C","line","Close-up McGonagall, 85mm","She studies him over her spectacles, unmoved.",M,
 "A vial in your pocket and a story at midnight prove nothing, Mr Potter. You have both earned detention every Saturday until June.","disbelief hardening into steel",0.5,0.5)
shot("C","insert","Macro, 100mm","A wall clock, minute hand sliding toward five minutes to midnight.")
shot("C","line","Medium close-up Draconia, parchment glowing in her palm","Ink crawls across the parchment on its own.",D,
 "Look at my palm, Potter, because the ink is moving by itself. It says the Polyjuice will be ready at midnight in the Astronomy Tower, signed with a single letter.","eerie wonder, barely breathing",0.55,0.4)
shot("C","line","Close-up Harry, 50mm","Harry reads over her shoulder, the colour leaving his face.",H,
 "That is not Pansy's handwriting, and I do not recognise the letter at the bottom. Whoever wrote it knew we would find this tonight.","low alarm, quiet dread",0.4,0.45)
shot("D","line","Full-body hero shot, Draconia running up the spiral stairs, moonlit","She hikes her gown and sprints up the stairs, Harry behind her.",D,
 "The clock strikes twelve in four minutes, and I will stand in that tower before it does. Whoever signed that letter is waiting, and I intend to see their face.","resolute, defiant, afraid and refusing to show it",0.8,0.35)
shot("D","cliffhanger","Wide, tower door cracks open, silhouette with a glowing vial, hard cut to black","The door swings open on a cloaked figure holding a glowing vial against the midnight moon. Hard cut to black on the first chime.")
LAST = None
words = lambda t: len(t.split())
sec = lambda t: round(words(t) / 5.4 + 0.25 + 0.4, 1)
for s in S:
    if s["kind"] == "line": s["seconds"] = sec(s["text"])
    elif s["kind"] == "insert": s["seconds"] = 1.7
    else: s["seconds"] = 3.0
# validation
lines = [s for s in S if s["kind"] == "line"]
FILL = re.compile(r"\b(um+|uh+|er+|hmm+|you know|i mean|kinda|sorta)\b|\.\.\.|--|\u2014", re.I)
for s in lines:
    t = s["text"]; sents = [x for x in re.split(r"(?<=[.!?])\s+", t) if x]
    assert 16 <= words(t) <= 36, (words(t), t)
    if not (not FILL.search(t) and len(sents) >= 2 and all(words(x) >= 5 for x in sents)): print('BAD', t)
tot = sum(s["seconds"] for s in S)
locs = {s["loc"] for s in S}
print("shots", len(S), "lines", len(lines), "inserts", sum(s["kind"]=="insert" for s in S), "locations", len(locs), "est runtime", round(tot,1))
assert 90 <= tot <= 120 and len(locs) <= 4
json.dump({"title": "The Debt of Champions", "version": "v9", "locations": {k: dict(name=v[0], colour=v[1]) for k, v in LOC.items()},
           "outfits": OUTFIT, "shots": [{"n": i+1, **s} for i, s in enumerate(S)]}, open("out/script_v9/e01_script_v9.json", "w"), indent=1)
li = [dict(id=f"v9_{i:02d}", sp=s["speaker"], t=s["text"], e=s["e"], c=s["c"]) for i, s in enumerate(lines)]
json.dump(li, open("out/audio/lines_v9.json", "w"), indent=1)
md = ["# E01 v9 shot list (4 locations, one line per shot, 4 prop inserts)", "", "Locations and colour temperature:"]
md += [f"- {k}: {v[0]} - {v[1]}" for k, v in LOC.items()]
md += ["", "One outfit per character for the whole episode:"] + [f"- {k}: {v}" for k, v in OUTFIT.items()] + ["", "| # | Loc | Type | Camera | Action | Line | Emotion | s |", "|---|---|---|---|---|---|---|---|"]
for i, s in enumerate(S, 1):
    md.append(f"| {i} | {s['loc']} | {s['kind']} | {s['camera']} | {s['action']} | {(s['speaker'] + ': ' + s['text']) if s['text'] else ''} | {s['emotion'] or ''} | {s['seconds']} |")
open("out/script_v9/e01_shotlist_v9.md", "w").write("\n".join(md))
