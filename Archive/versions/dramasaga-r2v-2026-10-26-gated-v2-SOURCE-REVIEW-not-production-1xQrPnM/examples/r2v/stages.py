"""Stage-artifact contracts for the staged production pipeline.
Stages: frames -> video -> assemble -> lipsync -> edit.
A stage may only consume an upstream artifact that is RECORDED in run-receipts.json
with an accepted/verified state AND whose local file still matches the recorded sha256.
Missing, unaccepted, or drifted artifacts hard-stop the run: a failed stage can never
propagate downstream by construction. No stage auto-retries; acceptance is a recorded
decision (--accept-frame with --approval-ref), never automatic."""
import hashlib, json, sys
from pathlib import Path

STAGE_ORDER = ["frames", "video", "assemble", "lipsync", "edit"]
IMPLEMENTED = {"frames", "video", "assemble", "lipsync", "edit"}
# state required on the upstream artifact before the named stage may consume it
REQUIRES = {"video": ("frames", "frame_accepted"),
            "assemble": ("video", "video_verified"),
            "lipsync": ("assemble", "assembled"),
            "edit": ("lipsync", "lipsync_done")}


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _shots(receipts):
    return receipts.setdefault("stage_shots", {})


def _key(ep, shot, beat=None):
    return "%s:%d" % (ep, shot) if beat is None else "%s:%d#b%d" % (ep, shot, beat)


def record_artifact(receipts, ep, shot, stage, path, state, beat=None, **extra):
    key = _key(ep, shot, beat)
    rec = {"stage": stage, "state": state,
           "artifact": str(path), "sha256": sha256_file(path)}
    rec.update(extra)
    _shots(receipts).setdefault(key, {})[stage] = rec
    return rec


def get_artifact(receipts, ep, shot, stage, beat=None):
    return _shots(receipts).get(_key(ep, shot, beat), {}).get(stage)


def require_artifact(receipts, ep, shot, stage, stop, beat=None):
    """Hard-stop unless the upstream artifact for `stage` is accepted/verified and intact."""
    if stage not in IMPLEMENTED:
        stop("stage '%s' is declared but not implemented yet - refusing to propagate" % stage)
    if stage not in REQUIRES:
        return None
    up_stage, up_state = REQUIRES[stage]
    rec = get_artifact(receipts, ep, shot, up_stage, beat=beat)
    if not rec:
        stop("%s s%02d: stage '%s' blocked - no recorded '%s' artifact (compose and accept the upstream stage first)"
             % (ep, shot, stage, up_stage))
    if rec.get("state") != up_state:
        stop("%s s%02d: stage '%s' blocked - upstream '%s' state is '%s', need '%s'"
             % (ep, shot, stage, up_stage, rec.get("state"), up_state))
    p = Path(rec["artifact"])
    if not p.exists():
        stop("%s s%02d: stage '%s' blocked - upstream artifact file missing: %s" % (ep, shot, stage, p))
    if sha256_file(p) != rec.get("sha256"):
        stop("%s s%02d: stage '%s' blocked - upstream artifact %s drifted from recorded hash"
             % (ep, shot, stage, p))
    return rec


# --- Lip-sync decision (from eye-test findings on the user's reference videos) ---
# Findings are planning DEFAULTS, not gates: dialogue normally sits on a speaker CU
# with a readable mouth, or plays as offscreen voice over inserts/wides. But the
# actual decision must come from the GENERATED video (our camera has drifted), so
# every on-screen dialogue shot needs a face_verdict recorded from real sampled
# frames of the assembled clip before paid lip-sync runs. framing_class only sets
# the default when no verdict exists yet.
FRAMING_DEFAULT_SYNC = {"cu_dialogue": True, "two_shot_dialogue": True,
                        "reaction_cu": False, "insert": False, "wide_action": False}


def lipsync_plan(shot, face_verdict=None):
    """Decide lip-sync vs soundtrack-only for one shot.
    shot: manifest shot dict (line, dialogue_on_screen, framing_class).
    face_verdict: None | 'readable' | 'not_readable' - verdict from inspecting
                  actual sampled frames of the generated video, never inferred.
    Returns {"mode": "lipsync"|"soundtrack", "needs_verdict": bool, "reason": str}."""
    if not shot.get("line"):
        return {"mode": "soundtrack", "needs_verdict": False,
                "reason": "no dialogue on this shot"}
    if shot.get("dialogue_on_screen") is False:
        return {"mode": "soundtrack", "needs_verdict": False,
                "reason": "declared offscreen/voiceover line"}
    if face_verdict == "ambiguous":
        return {"mode": "unresolved", "needs_verdict": False,
                "reason": "sampled frames are ambiguous (wide-vs-close or partial mouth visibility) - capture a denser sample or short motion strip and judge again; never silently pass"}
    if face_verdict == "readable":
        return {"mode": "lipsync", "needs_verdict": False,
                "reason": "mouth readable in actual generated frames"}
    if face_verdict == "not_readable":
        return {"mode": "soundtrack", "needs_verdict": False,
                "reason": "face not readable in actual generated frames (camera drift or framing); keep approved audio as soundtrack"}
    default = FRAMING_DEFAULT_SYNC.get(shot.get("framing_class"), False)
    return {"mode": "lipsync" if default else "soundtrack",
            "needs_verdict": True,
            "reason": "no face verdict yet - default from framing_class '%s'; inspect sampled frames of the generated video before paid lip-sync"
            % shot.get("framing_class")}


ALLOWED_CAMERA = {"static", "slow_push_in"}

# Magic Hour i2v contract (docs.magichour.ai/api-reference/video-projects/image-to-video,
# read 2026-10-26): wan-3.0 end_seconds must be one of these WHOLE seconds. Fractional
# beat lengths are NOT submittable; the runner generates the next allowed whole-second
# duration and trims to the exact frame-grid beat boundary locally.
I2V_ALLOWED_SECONDS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30)

def next_gen_s(dur_s):
    """Smallest provider-accepted whole-second generation duration covering dur_s."""
    for a in I2V_ALLOWED_SECONDS:
        if a >= dur_s - 1e-9:
            return a
    return None


def validate_manifest(shots):
    """Soft planner review from the eye-test findings. Returns warnings; NEVER blocks.
    These are defaults and review prompts, not universal rules: a wide with on-screen
    dialogue can be right when mouths stay readable - the lipsync stage re-decides
    from the actual generated frames via face_verdict."""
    warns = []
    for s in shots:
        tag = "%s s%02d" % (s["episode"], s["shot"])
        if s.get("line") and s.get("dialogue_on_screen") and s.get("framing_class") == "wide_action":
            warns.append("%s: on-screen dialogue declared on wide_action - the references put lip-synced lines on readable CUs or make them voiceover; confirm mouths stay readable" % tag)
        if s.get("line") and s.get("dialogue_on_screen") is None:
            warns.append("%s: dialogue shot without dialogue_on_screen flag - set it so the lipsync stage knows the intent" % tag)
        cam = s.get("camera", "static")
        if cam not in ALLOWED_CAMERA:
            warns.append("%s: unknown camera '%s' (allowed: static, slow_push_in)" % (tag, cam))
        if cam == "slow_push_in" and not s.get("reveal"):
            warns.append("%s: slow_push_in declared without 'reveal' beat - in the reference the push-in is reserved for the climax reveal; confirm intent" % tag)
    return warns


def beats_of(shot):
    """Normalized beat list for a shot, or None when the shot is undivided.
    Beats subdivide one approved shot WITHOUT changing its id, approved line, audio
    binding or total duration: the reference videos never ask one generation to carry
    several beats, so a packed shot becomes several single-carrier generations whose
    durations sum exactly to the approved shot length."""
    return shot.get("beats") or None


AUDIO_INTENTS = ("dialogue", "sound_fx", "silent")


def audio_intent(shot, beat=None):
    """Declared audio intent for one generation unit (explicit per beat/manifest).

    dialogue - the unit carries an approved line; Wan3 speaks it (quoted in the prompt).
    sound_fx - wordless but sound-bearing action (crash, spark, arrows); the generated
               track is still dropped at assemble, but we ask the model for sound so
               motion co-generates with it, and the verify gate requires the track.
    silent   - canonically soundless; requests audio:false and the verify gate REQUIRES
               the returned clip to carry no audio track.

    Nothing in the current manifest is silent: wordless is not silent - the chandelier
    crash is loud even while the masked figure applauds without sound.
    """
    if beat is not None and beat.get("audio_intent"):
        return beat["audio_intent"]
    if shot.get("audio_intent"):
        return shot["audio_intent"]
    if beat is not None:
        return "dialogue" if beat.get("carries_line") else "sound_fx"
    return "dialogue" if shot.get("audio") else "sound_fx"


def validate_beats(shot, fps=30, known_refs=None):
    """Hard validation of a shot's beat split and audio offset. Returns an error string or None.
    known_refs: when given, every declared frame/end_frame reference name must exist -
    a typo is otherwise silently dropped from prompts and crashes the frames stage."""
    if known_refs is not None:
        def _frefs(f):
            return (f or {}).get("refs") or []
        declared = list(_frefs(shot.get("frame"))) + list(_frefs(shot.get("end_frame")))
        for b in shot.get("beats") or []:
            declared += _frefs(b.get("frame")) + _frefs(b.get("end_frame"))
        unknown = [r for r in declared if r not in known_refs]
        if unknown:
            return "unknown reference name(s) %r - prompts would silently drop them and the frames stage would crash; fix the manifest" % (unknown,)
    off = shot.get("audio_offset_s")
    if off is not None:
        if not isinstance(off, (int, float)) or off < 0:
            return "audio_offset_s must be a non-negative number, got %r" % (off,)
        if abs(off * fps - round(off * fps)) > 1e-6:
            return "audio_offset_s %s is not on the %dfps frame grid" % (off, fps)
        if not shot.get("audio"):
            return "audio_offset_s set but the shot has no approved audio to delay - remove it"
    beats = shot.get("beats")
    si = shot.get("audio_intent")
    if si is not None and si not in AUDIO_INTENTS:
        return "audio_intent %r is not one of %s" % (si, list(AUDIO_INTENTS))
    if beats is None:
        if si == "dialogue" and not shot.get("audio"):
            return "audio_intent 'dialogue' but the shot has no approved audio - there is no line for the generation to carry"
        if si is not None and si != "dialogue" and shot.get("audio"):
            return "audio_intent %r on a shot with approved dialogue audio must be 'dialogue'" % (si,)
        if off:
            return "audio_offset_s %s on an undivided shot has no wordless head beat to delay past - the line would start late against its own visuals" % off
        return None
    if not beats:
        return "beats present but empty"
    if si is not None:
        return "shot-level audio_intent on a beat-subdivided shot is ambiguous - declare audio_intent per beat"
    for b in beats:
        bi = b.get("audio_intent")
        if bi is None:
            return ("beat %s declares no audio_intent - intent must be explicit "
                    "(dialogue for the carrier, sound_fx or silent for wordless beats)" % b.get("id"))
        if bi not in AUDIO_INTENTS:
            return "beat %s audio_intent %r is not one of %s" % (b.get("id"), bi, list(AUDIO_INTENTS))
        if b.get("carries_line") and bi != "dialogue":
            return "beat %s carries the approved line but audio_intent is %r - carriers must be 'dialogue'" % (b.get("id"), bi)
        if not b.get("carries_line") and bi == "dialogue":
            return ("beat %s is wordless but audio_intent is 'dialogue' - that would request "
                    "generated dialogue on a wordless beat" % b.get("id"))
    ids = [b.get("id") for b in beats]
    if len(set(ids)) != len(ids):
        return "duplicate beat ids %r" % ids
    total = sum(b.get("dur_s", 0) for b in beats)
    if abs(total - shot.get("shot_s", 0)) > 0.05:
        return "beat durations sum to %ss, approved shot is %ss - beats must preserve approved timing exactly" % (total, shot.get("shot_s"))
    carriers = [b["id"] for b in beats if b.get("carries_line")]
    if shot.get("line") and len(carriers) < 1:
        return "shot has an approved line but no beat claims it - at least one beat must carry the approved dialogue"
    if shot.get("audio"):
        head = 0.0
        for b in sorted(beats, key=lambda x: x["id"]):
            if b.get("carries_line"):
                break
            head += b.get("dur_s", 0)
        if abs((off or 0) - head) > 1e-9:
            return "audio_offset_s %s != leading wordless beat total %ss - the approved line would start over the wrong visuals (canon order breaks silently)" % (off or 0, head)
    for b in beats:
        if next_gen_s(b.get("dur_s", 0)) is None:
            return "beat %s dur_s %s exceeds the provider's maximum generation length (30s)" % (b.get("id"), b.get("dur_s"))
    for b in beats:
        if not isinstance(b.get("dur_s"), (int, float)) or b["dur_s"] <= 0:
            return "beat %s has non-positive dur_s" % b.get("id")
        frames = b["dur_s"] * fps
        if abs(frames - round(frames)) > 1e-6:
            return "beat %s dur_s %s is not on the %dfps frame grid (%.2f frames) - beat boundaries must align to encoded frame timestamps" % (b.get("id"), b["dur_s"], fps, frames)
    return None
