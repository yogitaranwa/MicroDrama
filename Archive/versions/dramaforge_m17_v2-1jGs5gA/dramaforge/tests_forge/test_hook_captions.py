"""Caption-hierarchy tests: white dialogue, yellow hook/cliffhanger."""
import pysubs2
from forge.assemble.hook_captions import write_hierarchy_ass, hooks_from_episode

WORDS = [{"word": w, "start": i * 0.5, "end": i * 0.5 + 0.4}
         for i, w in enumerate(["Your", "office", "closed", "at", "six."])]


def test_two_layers_distinct_styles(tmp_path):
    out = tmp_path / "cap.ass"
    hooks = hooks_from_episode("She said she was working late...", "What will she say?", 30.0)
    write_hierarchy_ass(WORDS, hooks, str(out))
    subs = pysubs2.load(str(out))
    by_style = {}
    for ev in subs:
        by_style.setdefault(ev.style, []).append(ev)
    assert set(by_style) == {"Dialogue", "Hook"}
    assert len(by_style["Hook"]) == 2
    assert len(by_style["Dialogue"]) == 2  # 5 words at 3 per line
    d = subs.styles["Dialogue"]
    h = subs.styles["Hook"]
    assert (d.primarycolor.r, d.primarycolor.g, d.primarycolor.b) == (255, 255, 255)
    assert (h.primarycolor.r, h.primarycolor.g, h.primarycolor.b) == (255, 255, 0)
    assert h.fontsize > d.fontsize
    assert d.alignment == pysubs2.Alignment.BOTTOM_CENTER
    assert h.alignment == pysubs2.Alignment.TOP_CENTER


def test_hook_and_cliffhanger_placement():
    hooks = hooks_from_episode("hook text", "cliff question", 30.0)
    hook, cliff = hooks
    assert (hook["start"], hook["end"]) == (0.0, 3.0)
    assert (cliff["start"], cliff["end"]) == (27.0, 30.0)
    assert hook["kind"] == "hook" and cliff["kind"] == "cliffhanger"


def test_empty_hooks_ok(tmp_path):
    out = tmp_path / "cap.ass"
    write_hierarchy_ass(WORDS, [], str(out))
    subs = pysubs2.load(str(out))
    assert all(ev.style == "Dialogue" for ev in subs)


def test_missing_text_skipped():
    assert hooks_from_episode("", "", 30.0) == []
