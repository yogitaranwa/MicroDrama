"""Casting sheet: one fixed voice identity per character across episodes, plus an emotion map
from the script's free-text emotion tags to engine settings.
Chatterbox (MIT) drafts: exaggeration + cfg_weight (+ audio_prompt_path for a fixed reference voice).
ElevenLabs finals: stability / style / speed (voice ids are chosen once from the account library; None until picked)."""
from dataclasses import dataclass, field
import re

@dataclass
class Voice:
    role: str
    kokoro: str                 # preview voice (Apache-2.0, runs on CPU)
    chatterbox_ref: str | None  # path to a fixed 10 s reference clip, set once from the first approved take
    base_exag: float            # Chatterbox baseline expressiveness
    base_cfg: float             # lower = faster, more dramatic pacing
    eleven_voice_id: str | None # picked once, then frozen
    eleven_stability: float
    traits: str
    pitch_note: str = ""

CAST = {
    "Harry Potter": Voice("male lead", "bm_george", None, 0.45, 0.5, None, 0.55,
                          "reserved, dry, controlled; emotion leaks through breath and pauses", "mid-low, steady"),
    "Draconia Malfoy": Voice("female lead", "af_bella", None, 0.7, 0.4, None, 0.35,
                             "expressive, proud, quick tongue; cracks into vulnerability", "mid-high, varied"),
    "Pansy Parkinson": Voice("side, rival", "af_nicole", None, 0.75, 0.35, None, 0.3,
                             "smug, sing-song, sharp edge", "high, bright"),
    "Professor McGonagall": Voice("side, authority", "bf_emma", None, 0.5, 0.55, None, 0.6,
                                  "stern, clipped Scots dryness, tired fairness", "mid-low, firm"),
    "Argus Filch": Voice("side, menace", "bm_lewis", None, 0.6, 0.45, None, 0.4,
                         "wheezy, suspicious, gravelly", "low, rasp"),
}

# keyword -> (exaggeration delta, cfg delta, eleven stability delta, eleven style)
EMOTION = [
    (r"fury|anger|rage|infuriat|snap", (+0.25, -0.05, -0.15, 0.6)),
    (r"panic|terror|fear|horror|desperat|urgent|adrenaline", (+0.2, -0.1, -0.2, 0.5)),
    (r"vulnerab|tremor|hurt|raw|grief|relief|shaky", (+0.1, +0.1, -0.1, 0.45)),
    (r"smug|amus|smirk|mock|sarcas|triumph", (+0.15, -0.05, -0.1, 0.5)),
    (r"calm|flat|cold|measured|quiet|controlled|stern|analytic", (-0.15, +0.1, +0.15, 0.15)),
    (r"realis|recogni|suspicio|scepti|puzzl", (0.0, +0.05, 0.0, 0.3)),
]

def settings(speaker: str, emotion: str) -> dict:
    v = CAST[speaker]
    de, dc, ds, style = 0.0, 0.0, 0.0, 0.25
    hits = [d for pat, d in EMOTION if re.search(pat, emotion, re.I)]
    for a, b, c, s in hits[:2]:
        de += a; dc += b; ds += c; style = max(style, s)
    clamp = lambda x, lo, hi: max(lo, min(hi, x))
    return {
        "chatterbox": {"exaggeration": round(clamp(v.base_exag + de, 0.25, 1.0), 2),
                       "cfg_weight": round(clamp(v.base_cfg + dc, 0.2, 0.7), 2),
                       "audio_prompt_path": v.chatterbox_ref},
        "elevenlabs": {"voice_id": v.eleven_voice_id, "stability": round(clamp(v.eleven_stability + ds, 0.15, 0.9), 2),
                       "style": style, "similarity_boost": 0.8, "speed": 1.0},
        "kokoro_voice": v.kokoro,
    }

def sheet_markdown() -> str:
    rows = ["| Character | Role | Traits | Preview voice | Chatterbox base (exag/cfg) | ElevenLabs stability |", "|---|---|---|---|---|---|"]
    for n, v in CAST.items():
        rows.append(f"| {n} | {v.role} | {v.traits} | {v.kokoro} | {v.base_exag}/{v.base_cfg} | {v.eleven_stability} |")
    return "\n".join(rows)
