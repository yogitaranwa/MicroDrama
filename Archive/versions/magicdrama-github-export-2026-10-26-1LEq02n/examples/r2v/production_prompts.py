"""Per-shot Wan 3.0 prompt builder from the canonical manifest + verified reference bank.
Grammar fixes from docs/flaw-log-wan30-probe-e01s13.md:
- lock camera explicitly (no zoom/pull-back/pan/tilt, framing unchanged entire shot)
- step/foot beats: feet + glowing floor grid visible in frame
- prop beats: prop visible during its own dialogue beat
- two-body shots: both characters present whole shot, no duplication/ghosting
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
MANIFEST = json.load(open(str(ROOT / "shot-manifest-wan30.json")))
BANK = json.load(open(str(ROOT / "harry-draconia-reference-bank.json")))
AUDIO_DIR = ROOT / "accepted-audio"

CAMERA_PUSH_IN = ("Slow steady push-in toward the subject's face for the whole shot: "
                  "no pan, no tilt, no cuts, framing tightens gradually.")
CAMERA_LOCK = ("Static locked camera on a tripod: no zoom, no pull-back, no pan, no tilt; "
               "the framing and focal length stay identical for the entire shot.")
SCENES = {
    "e01": "Candlelit Yule Ball in the Great Hall: chandeliers, formally dressed dancers, glowing waltz-grid lines on the marble floor.",
    "e02": "The Yule Ball hall under the curse: ice crawling across the doors, glowing waltz-grid lines on the marble floor, dimmed chandeliers.",
    "e03": "An under-castle dock by the Black Lake, then moonlit broom flight over black ice toward the Forbidden Forest.",
}
BANK_BY_NAME = {r["name"]: r for r in BANK["references"]}


def refs_for(shot):
    names = []
    chars = set(shot["refs"])
    for c in sorted(chars):
        names.append(c + "_front_close")
        # speaking-profile refs only when this character actually speaks in the shot:
        # avoids pushing the model toward speech on non-dialogue shots
        if (shot.get("speaker") or "").lower() == c:
            names.append(c + "_speaking_profile")
    if shot["two_body"]:
        names += ["two_shot_dialogue", "two_shot_action"]
    if shot["episode"] in ("e01", "e02"):
        names.append("yule_ball_location")
    return [n for n in names if n in BANK_BY_NAME]



_QA = None
def canonical_line(shot):
    """Spoken text quoted in the prompt must match the ACCEPTED AUDIO verbatim
    (accepted-audio/qa.json), not the manifest line field, which can lag or truncate."""
    global _QA
    if _QA is None:
        import json as _j
        from pathlib import Path as _P
        qf = _P(__file__).parent / "accepted-audio" / "qa.json"
        _QA = {}
        if qf.exists():
            for it in _j.loads(qf.read_text()):
                _QA[it["file"]] = it["text"].strip()
    return _QA.get(shot.get("audio"), (shot.get("line") or "").strip())


def _scrub_competing(action, shot):
    """Remove directions that compete with single-speaker speech conditioning."""
    if shot.get("speaker"):
        action = action.replace(" as screams rise", "")
    return action


_DELIV = None
def delivery_note(shot):
    """Per-line emotion/delivery/emphasis from the canonical scripts
    (accepted-audio/delivery-notes.json), for Wan3's documented
    dialogue + emotion + intonation + pace + timbre prompt recipe."""
    global _DELIV
    if _DELIV is None:
        import json as _j
        from pathlib import Path as _P
        nf = _P(__file__).parent / "accepted-audio" / "delivery-notes.json"
        _DELIV = _j.loads(nf.read_text()) if nf.exists() else {}
    return _DELIV.get((shot.get("audio") or "").rsplit(".", 1)[0], {})

FRAMING_NOTE = {
    "cu_dialogue": "Single close-up on the speaking character; the face is large, the mouth clearly visible, the background simple.",
    "two_shot_dialogue": "Both speakers share the frame; the active speaker's mouth is clearly visible.",
    "reaction_cu": "Close-up reaction shot; no dialogue; the expression carries the beat.",
    "insert": "Insert shot of the named prop or detail; no speaking face on screen.",
    "wide_action": "Wide shot; the action carries the beat.",
}
ALLOWED_CAMERA = {"static", "slow_push_in"}


def camera_note(shot):
    return CAMERA_PUSH_IN if shot.get("camera") == "slow_push_in" else CAMERA_LOCK


def prompt_for(shot):
    parts = [camera_note(shot), SCENES[shot["episode"]],
             FRAMING_NOTE.get(shot.get("framing_class"), ""),
             "Action beat: " + _scrub_competing(shot["action"], shot).rstrip(".") + "."]
    a = shot["action"].lower()
    if any(w in a for w in ("step", "dance", "dancing", "break", "grid")):
        parts.append("Keep the feet and the glowing floor grid visible in frame for the step beats; "
                     "when a character refers to the grid or the floor, the grid is visible at that moment.")
    if shot["two_body"]:
        parts.append("Both characters are present and interacting in frame for the whole shot; "
                     "do not duplicate, ghost or merge either body.")
    if shot.get("speaker"):
        line = canonical_line(shot)
        if line:
            note = delivery_note(shot)
            perf = ""
            if note:
                perf = " Emotion: %s. Delivery: %s." % (note["emotion"], note["delivery"] or "natural")
                if note.get("emphasis"):
                    perf += ' Emphasis on "%s".' % note["emphasis"]
            parts.append('%s says: "%s" Speak in the voice timbre and delivery of @%s; %s is the only speaker.%s'
                         % (shot["speaker"].title(), line, shot["audio"].rsplit(".", 1)[0], shot["speaker"].title(), perf))
        else:
            parts.append("Spoken dialogue and delivery follow @%s exactly; %s is the only speaker."
                         % (shot["audio"].rsplit(".", 1)[0], shot["speaker"].title()))
    char_refs = [n for n in refs_for(shot) if "two_shot" not in n and n != "yule_ball_location"]
    parts.append("Keep %s identical to the references in face, hair, wardrobe and proportions."
                 % ", ".join("@" + n for n in char_refs))
    scene_refs = [n for n in refs_for(shot) if "two_shot" in n or n == "yule_ball_location"]
    if scene_refs:
        parts.append("Match the staging, framing and lighting of @%s." % ", @".join(scene_refs))
    return " ".join(parts)


if __name__ == "__main__":
    for s in MANIFEST["shots"]:
        if (s["episode"], s["shot"]) in (("e01", 3), ("e01", 13)):
            print("=== %s s%02d (%ds, %d cr) refs=%s ===" % (s["episode"], s["shot"], s["billing_s"], s["billing_s"] * 96, refs_for(s)))
            print(prompt_for(s))


def missing_mentions(shot):
    """Every attached reference (image refs + audio stem) must be @-mentioned
    in the prompt; Magic Hour 422s otherwise. Returns the list missing."""
    prompt = prompt_for(shot)
    attached = refs_for(shot)
    if shot.get("audio"):
        attached = attached + [shot["audio"].rsplit(".", 1)[0]]
    return [n for n in attached if ("@" + n) not in prompt]
