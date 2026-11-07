"""Action-budget lint tests. Stdlib only."""
from forge.action_budget import find_actions, lint_shot, lint_episode

CALM = {"n": 1, "action": "She sits at the table.",
        "seconds": 10, "lines": [{"speaker": "A", "text": "word " * 22}]}
OVERLOADED = {"n": 2, "seconds": 10,
              "action": "He storms in, crosses the room, grabs the letter, slams the door and throws it on the table.",
              "lines": [{"speaker": "B", "text": "word " * 8}]}
WALK_AND_TALK = {"n": 3, "action": "She walks down the corridor.",
                 "seconds": 12, "lines": [{"speaker": "C", "text": "word " * 25}]}


def test_calm_dialogue_shot_passes():
    r = lint_shot(CALM)
    assert not r["overloaded"], r["flags"]


def test_overloaded_action_flagged():
    r = lint_shot(OVERLOADED)
    assert r["overloaded"]
    assert any("distinct movements" in f or "action beats" in f for f in r["flags"])
    assert "storms" in r["actions"] and "grabs" in r["actions"]


def test_movement_under_long_dialogue_flagged():
    r = lint_shot(WALK_AND_TALK)
    assert any("camera-blocking movement" in f for f in r["flags"])


def test_movement_with_short_line_ok():
    shot = dict(WALK_AND_TALK, lines=[{"speaker": "C", "text": "wait, stop."}])
    r = lint_shot(shot)
    assert not any("camera-blocking movement" in f for f in r["flags"])


def test_find_actions_distinct_and_casefold():
    assert find_actions("Walks, then walks again, and sits.") == ["walks", "sits"]


def test_episode_report_aggregates():
    rep = lint_episode([CALM, OVERLOADED, WALK_AND_TALK])
    assert rep["n_shots"] == 3 and rep["n_flagged"] == 2
    assert rep["flagged_shots"] == [2, 3] and not rep["ok"]
