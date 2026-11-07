"""Unit tests for Phase 1 components using Python's standard unittest library."""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from microdrama.series.organizer import SeriesOrganizer
from microdrama.series.archetypes import ArchetypeSanitizer
from microdrama.series.bible import SeriesBibleManager
from microdrama.series.arc_planner import ArcPlanner


class TestPhase1(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_phase1_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_series_organizer(self):
        organizer = SeriesOrganizer("The Cold CEO's Contract Bride", base_dir=self.test_dir)
        self.assertEqual(organizer.series_slug, "The_Cold_CEOs_Contract_Bride")

        # Create 10-episode structure
        organizer.ensure_series_structure(episodes_count=10)

        for ep in range(1, 11):
            ep_dir = organizer.get_episode_dir(ep)
            self.assertTrue(ep_dir.exists(), f"Episode dir missing for ep {ep}")
            self.assertTrue((ep_dir / "clips").exists())
            self.assertTrue((ep_dir / "master").exists())
            self.assertTrue((ep_dir / "subtitles").exists())
            self.assertTrue((ep_dir / "storyboard").exists())
            self.assertTrue((ep_dir / "screenplay").exists())
            self.assertTrue((ep_dir / "verification").exists())

        # Path helper checks
        self.assertEqual(organizer.get_master_path(1).name, "episode_01_master.mp4")
        self.assertEqual(organizer.get_subtitles_path(1, "ass").name, "episode_01.ass")
        self.assertEqual(organizer.get_shot_clip_path(1, "s01", "hook").name, "s01_hook.mp4")
        self.assertEqual(organizer.get_last_frame_path(1, "s01").name, "s01_lastframe.png")

        # Metadata persistence
        metadata = {
            "title": "The Cold CEO's Contract Bride",
            "genre": "contract_marriage",
            "episodes_count": 10,
        }
        organizer.save_metadata(metadata)
        loaded = organizer.load_metadata()
        self.assertEqual(loaded["title"], "The Cold CEO's Contract Bride")
        self.assertEqual(loaded["episodes_count"], 10)

    def test_archetype_sanitizer(self):
        # Harry Potter sanitization
        raw_prompt = "Harry Potter confronts Voldemort at Hogwarts with Hermione Granger"
        sanitized = ArchetypeSanitizer.sanitize_text(raw_prompt)
        self.assertNotIn("Harry Potter", sanitized)
        self.assertNotIn("Voldemort", sanitized)
        self.assertNotIn("Hogwarts", sanitized)
        self.assertIn("Henry Ashford", sanitized)
        self.assertIn("Malakor", sanitized)
        self.assertIn("Aethelgard Arcane Academy", sanitized)

        # Genre taxonomy
        genre = ArchetypeSanitizer.get_genre_info("contract_marriage")
        self.assertEqual(genre["display_name"], "Contract Marriage & Cold CEO")
        self.assertIn("Seraphina", genre["default_protagonist"]["name"])
        self.assertIn("Alexander", genre["default_deuteragonist"]["name"])

    def test_series_bible_manager(self):
        bible_file = self.test_dir / "test_series_bible.json"
        bible = SeriesBibleManager(bible_file)

        bible.initialize_series(
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
                    "wardrobe_current": "Charcoal suit, unbuttoned collar",
                },
            ],
        )

        # Character tracking
        alex = bible.get_character("Alexander")
        self.assertIsNotNone(alex)
        self.assertEqual(alex.archetype, "Cold CEO")
        self.assertEqual(len(bible.get_dead_characters()), 0)

        # Record cliffhanger for Episode 1
        bible.record_cliffhanger(1, "Alexander pins Seraphina against the wall.")
        last_ch = bible.get_last_cliffhanger()
        self.assertEqual(last_ch.text, "Alexander pins Seraphina against the wall.")
        self.assertFalse(last_ch.resolved)

        # Plot thread tracking
        bible.add_plot_thread("contract_leak", "The marriage contract leaked to press", setup_episode=1, target_resolution_episode=6)
        open_threads = bible.get_open_plot_threads()
        self.assertEqual(len(open_threads), 1)
        self.assertEqual(open_threads[0].id, "contract_leak")

        # Context pack generation
        context_pack = bible.get_compact_context_pack(target_episode=2)
        self.assertIn("MANDATORY HOOK REQUIREMENT", context_pack)
        self.assertIn("Alexander pins Seraphina against the wall.", context_pack)
        self.assertIn("contract_leak", context_pack)
        self.assertIn("Seraphina", context_pack)

        # Resolve cliffhanger in Episode 2
        bible.resolve_cliffhanger(1, resolving_episode=2)
        self.assertEqual(len(bible.get_unresolved_cliffhangers()), 0)

        # Commit and reload
        bible.commit()
        reloaded = SeriesBibleManager(bible_file)
        self.assertEqual(reloaded.state.series_title, "The Cold CEO's Contract Bride")
        self.assertEqual(len(reloaded.state.characters), 2)

    def test_arc_planner(self):
        plan = ArcPlanner.plan_contract_marriage_10("The Cold CEO's Contract Bride")
        self.assertEqual(plan.total_episodes, 10)
        self.assertEqual(len(plan.episodes), 10)

        # Episode 1 is Act I
        ep1 = plan.episodes[0]
        self.assertEqual(ep1.episode_number, 1)
        self.assertEqual(ep1.act_phase, "Act I: The Trap")

        # Episode 10 is Season 1 Finale
        ep10 = plan.episodes[9]
        self.assertEqual(ep10.episode_number, 10)
        self.assertEqual(ep10.act_phase, "Season 1 Finale")
        self.assertIn("Season Finale", ep10.title)

    def test_pattern_files_exist(self):
        patterns_dir = Path("dataset/patterns")
        self.assertTrue((patterns_dir / "hook_taxonomy.json").exists())
        self.assertTrue((patterns_dir / "cliffhanger_library.json").exists())
        self.assertTrue((patterns_dir / "pacing_rules.json").exists())
        self.assertTrue((patterns_dir / "dialogue_norms.json").exists())
        self.assertTrue((patterns_dir / "genre_clusters.json").exists())


if __name__ == "__main__":
    unittest.main()
