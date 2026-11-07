"""Shot/reverse-shot planning tests. Stdlib only."""
from forge.dialogue_shots import (split_dialogue_shot, expand_episode, plan_summary,
                                  ANGLE_REACTION)

HARRY = {"speaker": "Harry", "text": "Your office closed at six, and I waited here because something is clearly wrong tonight."}
DRACONIA = {"speaker": "Draconia", "text": "Harry, please, let me explain before you decide what this looks like."}
QUESTION = {"speaker": "Draconia", "text": "Then tell me what it is?"}


def _shot(lines, seconds=10):
    return {"n": 1, "location": "kitchens", "camera": "wide", "action": "she enters",
            "seconds": seconds, "lines": lines}


def test_two_speakers_become_separate_shots():
    planned = split_dialogue_shot(_shot([HARRY, DRACONIA]), ["Harry", "Draconia"])
    speakers = [p for p in planned if p["kind"] == "speaker"]
    assert len(speakers) == 2
    assert all(p["line"] for p in speakers)
    # one line per planned clip, always
    assert all((p["line"] is None) or isinstance(p["line"], dict) for p in planned)


def test_no_planned_clip_mixes_speakers():
    planned = split_dialogue_shot(_shot([HARRY, DRACONIA, HARRY]), ["Harry", "Draconia"])
    for p in planned:
        assert p["kind"] != "speaker" or p["line"]["speaker"] == p["speaker"]


def test_reverse_angle_for_second_speaker():
    planned = split_dialogue_shot(_shot([HARRY, DRACONIA]), ["Harry", "Draconia"])
    cams = [p["camera"] for p in planned if p["kind"] == "speaker"]
    assert cams[0].startswith("over_shoulder:Harry")
    assert cams[1].startswith("reverse:Draconia")


def test_reaction_inserted_after_question_before_answer():
    planned = split_dialogue_shot(_shot([QUESTION, HARRY]), ["Harry", "Draconia"])
    kinds = [p["kind"] for p in planned]
    assert kinds == ["speaker", "reaction", "speaker"]
    reaction = planned[1]
    assert reaction["speaker"] == "Harry"  # the listener
    assert reaction["camera"] == f"{ANGLE_REACTION}:Harry"
    assert reaction["line"] is None


def test_no_reaction_without_question():
    planned = split_dialogue_shot(_shot([HARRY, DRACONIA]), ["Harry", "Draconia"])
    assert "reaction" not in [p["kind"] for p in planned]


def test_reactions_can_be_disabled():
    planned = split_dialogue_shot(_shot([QUESTION, HARRY]), ["Harry", "Draconia"],
                                  insert_reactions=False)
    assert all(p["kind"] == "speaker" for p in planned)


def test_visual_shot_passes_through():
    planned = split_dialogue_shot(_shot([], seconds=5), ["Harry"])
    assert planned[0]["kind"] == "visual" and planned[0]["seconds"] == 5.0


def test_dialogue_seconds_split_by_words():
    long_line = dict(HARRY, text="word " * 30)  # 3x the other line
    planned = split_dialogue_shot(_shot([long_line, DRACONIA], seconds=12), ["Harry", "Draconia"])
    a, b = [p for p in planned if p["kind"] == "speaker"]
    assert a["seconds"] > b["seconds"]
    assert abs(a["seconds"] + b["seconds"] - 12) < 1.0


def test_expand_episode_numbers_continuously_and_summarises():
    ep = [_shot([HARRY, DRACONIA]), dict(_shot([QUESTION, HARRY]), n=2)]
    planned = expand_episode(ep)
    assert [p["plan_n"] for p in planned] == list(range(1, len(planned) + 1))
    s = plan_summary(planned)
    assert s["multi_speaker_clips"] == []
    assert s["by_kind"]["reaction"] == 1
    assert s["speakers"] == ["Draconia", "Harry"]
