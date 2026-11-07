from forge.audio.casting import settings, CAST
def test_anger_raises_expression_and_calm_lowers():
    a = settings("Harry Potter", "barely controlled anger")["chatterbox"]["exaggeration"]
    c = settings("Harry Potter", "flat calm")["chatterbox"]["exaggeration"]
    assert a > CAST["Harry Potter"].base_exag > c
def test_all_script_speakers_cast():
    import json, glob
    names = {l["speaker"] for f in glob.glob("out/shots/*.json") for l in json.load(open(f))["lines"]}
    assert names <= set(CAST), names - set(CAST)

def test_line_tempo_clamps():
    from forge.audio.pace import line_tempo
    assert line_tempo(208) == 1.5      # slow line capped at 1.5x
    assert line_tempo(328) == 1.15
    assert 1.15 <= line_tempo(268) <= 1.5
