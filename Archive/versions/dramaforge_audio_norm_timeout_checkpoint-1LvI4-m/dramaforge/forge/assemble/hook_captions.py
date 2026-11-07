"""Caption hierarchy: white dialogue subtitles + yellow hook/cliffhanger text.

The reference pattern keeps two caption layers distinct: white word-by-word
dialogue at the bottom, and yellow retention text (the opening hook and the
closing question) in a larger style at the top. This is pure editing work -
it costs no credits and no generation.

Additive alongside forge.assemble.captions (which writes the dialogue layer);
this writer produces both layers in one ASS file so the hierarchy survives
into the edit without restyling by hand.
"""
from typing import Dict, List
import pysubs2

WHITE = "&H00FFFFFF"
YELLOW = "&H0000FFFF"  # ASS colour order is AABBGGRR


def write_hierarchy_ass(words: List[Dict], hooks: List[Dict], out_path,
                        per_line: int = 3, w: int = 1080, h: int = 1920,
                        font: str = "DejaVu Sans", size: int = 64) -> str:
    """words: [{"word","start","end"}] dialogue timings (white, bottom).
    hooks: [{"text","start","end","kind"}] with kind 'hook' or 'cliffhanger'
    (yellow, top, larger). Times in seconds."""
    subs = pysubs2.SSAFile()
    subs.info["PlayResX"], subs.info["PlayResY"] = str(w), str(h)
    dialogue = pysubs2.SSAStyle(fontname=font, fontsize=size, bold=True, outline=4, shadow=1,
                                primarycolor=WHITE, alignment=pysubs2.Alignment.BOTTOM_CENTER,
                                marginv=260)
    hook = pysubs2.SSAStyle(fontname=font, fontsize=int(size * 1.35), bold=True, outline=5, shadow=1,
                            primarycolor=YELLOW, alignment=pysubs2.Alignment.TOP_CENTER,
                            marginv=180)
    subs.styles["Dialogue"] = dialogue
    subs.styles["Hook"] = hook
    for i in range(0, len(words), per_line):
        g = words[i:i + per_line]
        subs.append(pysubs2.SSAEvent(start=int(g[0]["start"] * 1000),
                                     end=int(g[-1]["end"] * 1000),
                                     style="Dialogue",
                                     text=" ".join(x["word"] for x in g)))
    for hk in hooks:
        subs.append(pysubs2.SSAEvent(start=int(hk["start"] * 1000),
                                     end=int(hk["end"] * 1000),
                                     style="Hook", text=hk["text"]))
    subs.save(out_path)
    return out_path


def hooks_from_episode(hook_text: str, cliffhanger_text: str, total_seconds: float,
                       hook_s: float = 3.0, cliff_s: float = 3.0) -> List[Dict]:
    """Standard placement: hook over the opening seconds, cliffhanger question
    over the closing seconds."""
    out = []
    if hook_text:
        out.append({"text": hook_text, "start": 0.0, "end": min(hook_s, total_seconds), "kind": "hook"})
    if cliffhanger_text:
        out.append({"text": cliffhanger_text, "start": max(0.0, total_seconds - cliff_s),
                    "end": total_seconds, "kind": "cliffhanger"})
    return out
