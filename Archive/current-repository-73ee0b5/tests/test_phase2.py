"""Unit tests for Phase 2 components using Python's standard unittest library:

- DramaBench few-shot pattern retrieval from dataset/patterns/
- Sequential shot prompt generation with context chaining and last-frame injection
- ContinuityValidator deterministic rule checks and edge-case detection
- Screenwriter multi-pass review loop and DramaBench quality scoring
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from microdrama.models import Character, Shot, Screenplay, GenreTemplate
from microdrama.narrative.prompt_builder import (
    get_dramabench_patterns,
    build_sequential_shot_prompt,
    build_screenplay_prompt,
)
from microdrama.narrative.screenwriter import Screenwriter
from microdrama.series.bible import SeriesBibleManager
from microdrama.series.continuity import ContinuityValidator


class TestPhase2(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_phase2_"))
        self.bible_file = self.test_dir / "series_bible.json"
        self.bible = SeriesBibleManager(self.bible_file)
        self.bible.initialize_series(
            title="The Cold CEO's Contract Bride",
            genre="contract_marriage",
            logline="A fake marriage hides a deadly secret.",
            target_episodes=10,
            initial_characters=[
                {
                    "name": "Seraphina",
                    "role": "Protagonist",
                    "archetype": "Trapped Heroine",
                    "look": "Auburn wavy hair, amber eyes",
                    "wardrobe_current": "Cream cashmere sweater",
                },
                {
                    "name": "Alexander",
                    "role": "Deuteragonist",
                    "archetype": "Cold CEO",
                    "look": "Tall athletic build, charcoal suit",
                    "wardrobe_current": "Charcoal bespoke suit",
                },
            ],
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_dramabench_pattern_retrieval(self):
        patterns = get_dramabench_patterns("contract_marriage")
        self.assertIn("hook_formulas", patterns)
        self.assertIn("cliffhanger_formulas", patterns)
        self.assertTrue(len(patterns["hook_formulas"]) > 0)
        self.assertTrue(len(patterns["cliffhanger_formulas"]) > 0)

    def test_sequential_shot_prompt_generation(self):
        shot1 = Shot(
            id="s01",
            mode="t2v",
            duration=8,
            visual="Penthouse office in evening light. Seraphina slaps Alexander.",
            action="Seraphina slaps Alexander sharply across the cheek.",
            camera="Vertical 9:16 portrait: close-up on slap impact",
            speaker="Seraphina",
            dialogue="Let go of me!",
            continuity="Seraphina in cream cashmere sweater; Alexander in charcoal suit.",
        )

        shot2 = Shot(
            id="s02",
            mode="i2v",
            duration=8,
            visual="Alexander touches his reddened cheek with a menacing glare.",
            action="Alexander stalks forward, towering over Seraphina.",
            camera="Vertical 9:16 portrait: low-angle push-in",
            speaker="Alexander",
            dialogue="Say that again.",
            continuity="Seraphina in cream cashmere sweater; Alexander in charcoal suit.",
        )

        # Test prompt for shot 2 chained from shot 1
        prompt = build_sequential_shot_prompt(
            shot=shot2,
            prev_shot=shot1,
            last_frame_path="outputs/clips/s01_lastframe.png",
        )

        self.assertIn("[CONTINUITY FROM PREVIOUS SHOT s01]", prompt)
        self.assertIn("Seraphina slaps Alexander", prompt)
        self.assertIn("[IMAGE-TO-VIDEO MODE]", prompt)
        self.assertIn("9:16 vertical orientation", prompt)
        self.assertIn("Alexander speaks fiercely", prompt)

    def test_continuity_validator_rules(self):
        # 1. Normal valid screenplay
        screenwriter = Screenwriter(provider="mock")
        screenplay = screenwriter.generate_screenplay(
            story_idea="A fake marriage hides a deadly secret.",
            cast=[
                Character(name="Seraphina", role="Protagonist", look="Auburn hair"),
                Character(name="Alexander", role="Deuteragonist", look="Charcoal suit"),
            ],
            episode_number=1,
        )

        report = ContinuityValidator.validate_screenplay(screenplay, self.bible)
        self.assertTrue(report.is_valid)
        self.assertEqual(len(report.violations), 0)

        # 2. Dead character test: mark character as dead in Bible
        self.bible.state.characters["Alexander"].status = "dead"
        dead_report = ContinuityValidator.validate_screenplay(screenplay, self.bible)
        self.assertFalse(dead_report.is_valid)
        self.assertTrue(any("Deceased character" in v for v in dead_report.violations))

    def test_multi_pass_review_loop(self):
        screenwriter = Screenwriter(provider="mock")
        screenplay, report, qscore = screenwriter.generate_screenplay_with_review(
            story_idea="Seraphina faces Alexander after discovering the contract terms.",
            bible=self.bible,
            cast=[
                Character(name="Seraphina", role="Protagonist", look="Auburn hair"),
                Character(name="Alexander", role="Deuteragonist", look="Charcoal suit"),
            ],
            episode_number=1,
            max_passes=2,
        )

        self.assertIsNotNone(screenplay)
        self.assertEqual(screenplay.episode_number, 1)
        self.assertEqual(len(screenplay.shots), 8)
        self.assertTrue(report.is_valid)
        self.assertGreaterEqual(qscore.hook_score, 4)
        self.assertGreaterEqual(qscore.cliffhanger_score, 4)
        self.assertTrue(qscore.is_approved)


if __name__ == "__main__":
    unittest.main()
