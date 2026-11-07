import subprocess
import tempfile
import unittest
from pathlib import Path

from microdrama.detectors import (detect_freezes, detect_silence,
                                  dialogue_free_gaps, mechanical_report)


def make_video(path: Path, video_src: str, audio_expr: str | None,
               duration: float = 4.0) -> Path:
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", video_src]
    if audio_expr:
        cmd += ["-f", "lavfi", "-i", audio_expr]
    cmd += ["-t", str(duration), "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", str(path)]
    subprocess.run(cmd, check=True)
    return path


class DetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.moving = make_video(root / "moving.mp4", "testsrc2=size=320x240:rate=10",
                                "sine=frequency=440")
        cls.frozen = make_video(root / "frozen.mp4", "color=c=red:size=320x240:rate=10",
                                "sine=frequency=440")
        cls.opening_silence = make_video(
            root / "opens_silent.mp4", "testsrc2=size=320x240:rate=10",
            "aevalsrc='if(lt(t,1.5),0,0.5*sin(440*2*PI*t))':d=4")
        cls.quiet_tail = make_video(
            root / "quiet_tail.mp4", "testsrc2=size=320x240:rate=10",
            "aevalsrc='if(lt(t,2),0.8*sin(440*2*PI*t),0.005*sin(220*2*PI*t))':d=4")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_freeze_flags_static_clip(self):
        windows = detect_freezes(self.frozen, min_duration_s=2.0)
        self.assertTrue(windows, "static color clip must be detected as frozen")

    def test_freeze_ignores_moving_clip(self):
        windows = detect_freezes(self.moving, min_duration_s=2.0)
        self.assertEqual(windows, [])

    def test_opening_silence_detected(self):
        report = mechanical_report(self.opening_silence)
        kinds = [d["type"] for d in report["defects"]]
        self.assertIn("opening_silence", kinds)
        self.assertFalse(report["mechanical_pass"])

    def test_no_false_silence_on_tone(self):
        self.assertEqual(detect_silence(self.moving), [])

    def test_quiet_gap_flagged_against_full_mean(self):
        report = mechanical_report(
            self.quiet_tail, dialogue_windows=[{"start": 0.0, "end": 2.0}])
        kinds = [d["type"] for d in report["defects"]]
        self.assertIn("bed_level", kinds)
        flagged = [g for g in report["gap_levels"] if g.get("flag")]
        self.assertTrue(flagged, "the quiet tail gap must be flagged")

    def test_gap_math(self):
        gaps = dialogue_free_gaps(10.0, [{"start": 2.0, "end": 4.0},
                                         {"start": 5.0, "end": 7.0}],
                                  min_gap_s=0.5, pad_s=0.15)
        self.assertEqual([(g["start"], g["end"]) for g in gaps],
                         [(0.0, 1.85), (4.15, 4.85), (7.15, 10.0)])


if __name__ == "__main__":
    unittest.main()
