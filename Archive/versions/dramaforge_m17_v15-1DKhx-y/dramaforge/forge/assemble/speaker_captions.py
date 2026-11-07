"""Speaker-differentiated dialogue captions.

The reference format (multi-character dialogue shorts) distinguishes each
speaker's subtitles by style: colour per speaker, optional italic and a
">>" prefix. Single-style captions make two-character exchanges unreadable,
so speakers get deterministic styles derived from their first appearance
order unless overridden.

Additive alongside captions.py (single style) and hook_captions.py
(dialogue + hook layers): this writer styles the dialogue layer per
speaker and composes with write_hierarchy_ass hooks by sharing the ASS.
"""
from typing import Dict, List
import pysubs2

WHITE = "&H00FFFFFF"
YELLOW = "&H0000FFFF"
CYAN = "&H00FFFF00"
PINK = "&H00FF80FF"

PALETTE = [WHITE, YELLOW, CYAN, PINK]


def speaker_styles(speakers: List[str], overrides: Dict = None,
                   font: str = "DejaVu Sans", size: int = 64,
                   margin_v: int = 260) -> Dict:
    """speaker name -> pysubs2 style, deterministic by first appearance.
    overrides: {"NAME": {"color": YELLOW, "italic": True, "prefix": ">> "}}.
    margin_v is the bottom margin in PlayResY units: raise it when the
    input video already carries burned captions at the bottom so the new
    speaker captions stack above them instead of colliding."""
    overrides = overrides or {}
    styles = {}
    for i, name in enumerate(speakers):
        o = overrides.get(name, {})
        styles[name] = {
            "color": o.get("color", PALETTE[i % len(PALETTE)]),
            "italic": o.get("italic", False),
            "prefix": o.get("prefix", ">> " if i == 0 else ""),
            "style": pysubs2.SSAStyle(
                fontname=font, fontsize=size, bold=True,
                italic=o.get("italic", False), outline=4, shadow=1,
                primarycolor=o.get("color", PALETTE[i % len(PALETTE)]),
                alignment=pysubs2.Alignment.BOTTOM_CENTER, marginv=margin_v),
        }
    return styles


def write_speaker_ass(segments: List[Dict], out_path, overrides: Dict = None,
                      w: int = 1080, h: int = 1920, font: str = "DejaVu Sans",
                      size: int = 64, margin_v: int = 260) -> str:
    """segments: [{"speaker": "DRACONIA", "text": "...", "start": s, "end": e}]
    (seconds). Writes one ASS with one style per speaker; event text carries
    the speaker's prefix so the exchange stays readable even without colour."""
    if not segments:
        raise ValueError("write_speaker_ass needs at least one segment")
    names = []
    for s in segments:
        if "speaker" not in s:
            raise ValueError(f"segment missing speaker: {s!r}")
        if s["speaker"] not in names:
            names.append(s["speaker"])
    styles = speaker_styles(names, overrides, font, size, margin_v)
    subs = pysubs2.SSAFile()
    subs.info["PlayResX"], subs.info["PlayResY"] = str(w), str(h)
    for name in names:
        subs.styles[f"spk_{name}"] = styles[name]["style"]
    for s in segments:
        st = styles[s["speaker"]]
        subs.append(pysubs2.SSAEvent(
            start=int(s["start"] * 1000), end=int(s["end"] * 1000),
            style=f"spk_{s['speaker']}",
            text=st["prefix"] + s["text"]))
    subs.save(out_path)
    return out_path
