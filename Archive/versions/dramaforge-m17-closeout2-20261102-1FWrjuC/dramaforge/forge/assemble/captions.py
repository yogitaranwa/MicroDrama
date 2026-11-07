"""Word-by-word captions from WhisperX timings via pysubs2 (MIT) -> ASS."""
import pysubs2

def words_to_ass(words, out_path, per_line=3, w=1080, h=1920, font="DejaVu Sans", size=64):
    subs = pysubs2.SSAFile()
    subs.info["PlayResX"], subs.info["PlayResY"] = str(w), str(h)
    st = pysubs2.SSAStyle(fontname=font, fontsize=size, bold=True, outline=4, shadow=1,
                          alignment=pysubs2.Alignment.BOTTOM_CENTER, marginv=260)
    subs.styles["Default"] = st
    for i in range(0, len(words), per_line):
        g = words[i:i + per_line]
        subs.append(pysubs2.SSAEvent(start=int(g[0]["start"] * 1000), end=int(g[-1]["end"] * 1000),
                                     text=" ".join(x["word"] for x in g)))
    subs.save(out_path)
    return out_path
