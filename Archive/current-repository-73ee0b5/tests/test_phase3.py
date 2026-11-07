"""Unit tests for Phase 3 components using Python's standard unittest library:

- SubtitleGenerator: ReelShort styled ASS subtitle generation and color coding
- EpisodeAssembler: FFmpeg frame extraction, concat assembly, and burned-in ASS subtitles
- MagicHourGenerator: Sequential shot generation with last-frame chaining
- SemanticVerificationRunner: Milestone semantic verification unit tests (Option C)
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from microdrama.models import Character, Shot, Screenplay
from microdrama.postprod.subtitle import SubtitleGenerator
from microdrama.postprod.assembler import EpisodeAssembler, get_ffmpeg_binary
from microdrama.client.generator import MagicHourGenerator
from microdrama.series.organizer import SeriesOrganizer
from microdrama.series.bible import SeriesBibleManager
from microdrama.series.semantic_verifier import SemanticVerificationRunner


class TestPhase3(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_phase3_"))
        self.screenplay = Screenplay(
            episode_number=1,
            title="The Price of Blood",
            genre="contract_marriage",
            logline="A fake marriage hides a deadly secret.",
            hook="Divorce papers slammed on mahogany desk.",
            cliffhanger="Alexander grabs Seraphina: 'You leave when I say.'",
            cast=[
                Character(name="Seraphina", role="Protagonist", look="Auburn hair"),
                Character(name="Alexander", role="Deuteragonist", look="Charcoal suit"),
                Character(name="Victoria", role="Antagonist", look="Crimson dress"),
            ],
            shots=[
                Shot(
                    id="s01",
                    mode="t2v",
                    duration=2,
                    visual="Penthouse office in evening light. Seraphina slams papers.",
                    action="Seraphina slams contract on desk.",
                    camera="Vertical 9:16 portrait: close-up push-in",
                    speaker="Seraphina",
                    dialogue="I signed it, Alexander.",
                    continuity="Cream sweater.",
                ),
                Shot(
                    id="s02",
                    mode="i2v",
                    duration=2,
                    visual="Alexander towers over Seraphina with a cold sneer.",
                    action="Alexander unbuttons cuffs, stepping forward.",
                    camera="Vertical 9:16 portrait: low-angle hero framing",
                    speaker="Alexander",
                    dialogue="Three rules. Obey them all.",
                    continuity="Charcoal suit.",
                ),
            ],
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ass_subtitle_generation(self):
        ass_path = self.test_dir / "episode_01.ass"
        content = SubtitleGenerator.generate_ass(self.screenplay, out_file=ass_path, safe_margin_bottom=120)

        self.assertTrue(ass_path.exists())
        self.assertIn("[Script Info]", content)
        self.assertIn("PlayResX: 720", content)
        self.assertIn("PlayResY: 1280", content)
        # Check speaker style definitions
        self.assertIn("Style: Seraphina", content)
        self.assertIn("Style: Alexander", content)
        # Check dialogue events
        self.assertIn("Dialogue: 0,", content)
        self.assertIn(r"{\b1}Seraphina: {\b0}I signed it, Alexander.", content)
        self.assertIn(r"{\b1}Alexander: {\b0}Three rules. Obey them all.", content)

    def test_ffmpeg_frame_extraction_and_assembly(self):
        assembler = EpisodeAssembler(output_dir=self.test_dir)
        ffmpeg_bin = assembler.ffmpeg_bin
        self.assertIsNotNone(ffmpeg_bin, "FFmpeg binary must be available via imageio-ffmpeg")

        # Create two 2-second test video clips
        clip1 = self.test_dir / "s01.mp4"
        clip2 = self.test_dir / "s02.mp4"
        for c in [clip1, clip2]:
            cmd = [
                "-f", "lavfi",
                "-i", "color=c=0x1a1a2e:s=720x1280:d=2",
                "-f", "lavfi",
                "-i", "anullsrc=r=48000:cl=stereo",
                "-t", "2",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                str(c.resolve()),
            ]
            assembler.run_ffmpeg(cmd)
            self.assertTrue(c.exists())

        # Test frame extraction
        extracted_frame = self.test_dir / "s01_lastframe.png"
        assembler.extract_last_frame(clip1, extracted_frame)
        self.assertTrue(extracted_frame.exists())
        self.assertGreater(extracted_frame.stat().st_size, 500)

        # Test assembly with burned ASS subtitles
        ass_file = self.test_dir / "test.ass"
        SubtitleGenerator.generate_ass(self.screenplay, out_file=ass_file)

        master_out = self.test_dir / "master.mp4"
        assembler.assemble(
            screenplay=self.screenplay,
            clip_paths=[clip1, clip2],
            out_master_path=master_out,
            ass_path=ass_file,
            burn_subtitles=True,
        )

        self.assertTrue(master_out.exists())
        self.assertGreater(master_out.stat().st_size, 5000)

    def test_sequential_generation_mock(self):
        organizer = SeriesOrganizer("Test Series", base_dir=self.test_dir)
        generator = MagicHourGenerator(mock_mode=True)

        clips = generator.generate_episode_sequentially(
            screenplay=self.screenplay,
            organizer=organizer,
            use_frame_extraction=True,
        )

        self.assertEqual(len(clips), 2)
        for c in clips:
            self.assertTrue(c.exists())
            self.assertGreater(c.stat().st_size, 500)

    def test_semantic_verification_runner(self):
        bible_path = self.test_dir / "bible.json"
        bible = SeriesBibleManager(bible_path)
        bible.initialize_series(
            title="The Price of Blood",
            genre="contract_marriage",
            logline="A fake marriage hides a deadly secret.",
            target_episodes=10,
        )

        report_file = self.test_dir / "semantic_test.json"
        report = SemanticVerificationRunner.run_verification(
            screenplay=self.screenplay,
            bible=bible,
            out_file=report_file,
        )

        self.assertTrue(report_file.exists())
        self.assertEqual(report["overall_verdict"], "PASS")
        self.assertGreaterEqual(report["continuity_score"], 4.0)
        self.assertGreaterEqual(report["tests_passed"], 4)


if __name__ == "__main__":
    unittest.main()
