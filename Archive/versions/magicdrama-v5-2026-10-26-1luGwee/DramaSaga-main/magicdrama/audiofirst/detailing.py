"""Per-line performance detailing for voice direction.

User direction (2026-10-26): every line carries its own emotional/performance
detailing; the writing is not constrained to a fixed emotion vocabulary.
So detailing values are free text: presence is enforced, wording is not.

Only the tag lexicon below is injected into eleven_v3 request text: the ten
existing project tags plus [rushed], [urgent] and [interrupting] named in the
accepted 2026-10-25 revised-script performance notes. Any other direction
stays in the detailing record as guidance for review; code never invents a
bracket tag and hopes the model honors it. Tags are instructions, not proof
of emotional acting; the audio still requires human listening review.

ElevenLabs text-to-dialogue settings verified 2026-10-26:
https://elevenlabs.io/docs/api-reference/text-to-dialogue
- settings.stability: lower values broaden emotional range (default 0.5).
- No documented per-line speed control on this endpoint; brisk delivery is
  directed with tags such as [rushed], and measured after the fact against
  the actual WAV (dialogue_timing), never assumed.
"""
from __future__ import annotations

REQUIRED_FIELDS = ("emotion", "delivery")
OPTIONAL_FIELDS = ("emphasis", "pause_before", "pause_after", "reaction")
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

TAG_LEXICON = {
    "angry": "[angry]", "whisper": "[whispers]", "sad": "[sad]",
    "suspicion": "[curious]", "nervous": "[nervous]", "excited": "[excited]",
    "quiet": "[softly]", "laugh": "[laughs]", "sigh": "[sighs]",
    "rushed": "[rushed]", "urgent": "[urgent]", "interrupting": "[interrupting]",
}
MAX_TAGS_PER_LINE = 2
SETTINGS_SOURCE = "https://elevenlabs.io/docs/api-reference/text-to-dialogue"


def validate_detailing(detailing, line_id="?"):
    """Presence-validated, vocabulary-unconstrained performance detailing."""
    if not isinstance(detailing, dict):
        raise ValueError("%s: detailing map required for every dialogue line" % line_id)
    unknown = sorted(set(detailing) - set(ALL_FIELDS))
    if unknown:
        raise ValueError("%s: unknown detailing fields %s" % (line_id, unknown))
    for field in REQUIRED_FIELDS:
        value = detailing.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s: detailing needs nonempty %s" % (line_id, field))
    for field in OPTIONAL_FIELDS:
        value = detailing.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError("%s: detailing field %s must be nonempty text when present" % (line_id, field))
    return {k: v.strip() for k, v in detailing.items()}


def tags_for(detailing):
    """Map detailing text to the verified tag lexicon; unknown wording is not tagged."""
    haystack = " ".join(detailing.values()).casefold()
    return list(dict.fromkeys(tag for word, tag in TAG_LEXICON.items() if word in haystack))[:MAX_TAGS_PER_LINE]


def tagged_text(line):
    """Line text with verified v3 tags from its detailing (or legacy performance field)."""
    detailing = line.get("detailing")
    if detailing is not None:
        detailing = validate_detailing(detailing, line.get("id", "?"))
        tags = tags_for(detailing)
    else:
        from .voices import TAGS
        direction = line.get("performance", "")
        if not isinstance(direction, str):
            raise ValueError("%s: legacy performance direction must be text" % line.get("id", "?"))
        haystack = direction.casefold()
        tags = list(dict.fromkeys(tag for word, tag in TAGS.items() if word in haystack))[:MAX_TAGS_PER_LINE]
    text = line["text"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("%s: dialogue text required" % line.get("id", "?"))
    return (" ".join(tags) + " " if tags else "") + text


def validate_voice_settings(settings):
    """Optional text-to-dialogue settings; only documented fields, documented ranges."""
    if settings is None:
        return None
    if not isinstance(settings, dict):
        raise ValueError("voice settings must be a map")
    unknown = sorted(set(settings) - {"stability", "similarity"})
    if unknown:
        raise ValueError("undocumented dialogue settings %s; verified fields: stability, similarity" % unknown)
    out = {}
    for key, value in settings.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError("voice setting %s must be a number in [0, 1]" % key)
        out[key] = float(value)
    return out


def episode_detailing_report(episode):
    """Every line's detailing status; missing detailing is an explicit gap list."""
    gaps, detailed = [], 0
    for line in episode.get("lines", []):
        if line.get("detailing") is None:
            gaps.append(line.get("id", "?"))
        else:
            validate_detailing(line["detailing"], line.get("id", "?"))
            detailed += 1
    return {"episode_id": episode.get("id"), "lines": len(episode.get("lines", [])),
            "detailed": detailed, "missing": gaps,
            "status": "complete" if not gaps else "gaps",
            "note": "detailing is direction, not proof of emotional delivery; audio still needs listening review"}
