"""End-to-end enforcement tests for the assemble entrypoint: exit codes and
the presence or absence of an output file, on real synthetic media."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from microdrama.reviewgate import scaffold_receipt
from test_detectors import make_video

ROOT = Path(__file__).resolve().parents[1]


def run_assemble(req, assets, receipts_dir, audio, out, episode_receipt=None):
    cmd = [sys.executable, str(ROOT / "run_pipeline.py"), "assemble",
           "--requirements", str(req), "--assets", str(assets),
           "--receipts-dir", str(receipts_dir), "--audio", str(audio),
           "--out", str(out)]
    if episode_receipt:
        cmd += ["--episode-receipt", str(episode_receipt)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


def write_full_receipt(receipts_dir: Path, asset: Path, beat: str):
    receipt = scaffold_receipt(asset, beat)
    receipt["reviewer"] = "reviewer-one"
    receipt["reviewed_at"] = "2026-10-25T18:00:00+05:30"
    receipt["checks"] = {k: True for k in receipt["checks"]}
    (receipts_dir / f"beat{beat}.receipt.json").write_text(json.dumps(receipt))
    return receipt


class AssembleCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.root = root
        cls.shot_a = make_video(root / "a.mp4", "testsrc2=size=320x240:rate=10",
                                None, duration=3.0)
        cls.shot_b = make_video(root / "b.mp4", "testsrc2=size=320x240:rate=10",
                                None, duration=3.0)
        cls.frozen = make_video(root / "frozen.mp4", "color=c=red:size=320x240:rate=10",
                                None, duration=3.0)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                        "-i", "sine=frequency=440", "-t", "6",
                        str(root / "audio.aac")], check=True)
        cls.audio = root / "audio.aac"
        cls.requirements = root / "req.json"
        cls.requirements.write_text(json.dumps({"beats": [
            {"beat": "1", "start": 0, "end": 3.0,
             "required_actions": ["entrance walk at natural speed"], "lines": []},
            {"beat": "2", "start": 3.0, "end": 6.0,
             "required_actions": ["arrows land on the beat"],
             "lines": [{"line": 1, "start": 3.2, "end": 5.5}]}]}))
        cls.assets = root / "assets.json"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.receipts = self.root / f"receipts-{self._testMethodName}"
        self.receipts.mkdir()
        self.out = self.root / f"out-{self._testMethodName}.mp4"
        self.out.unlink(missing_ok=True)

    def write_assets(self, a, b):
        self.assets.write_text(json.dumps({"1": str(a), "2": str(b)}))

    def test_missing_receipt_exits_1_with_no_output(self):
        self.write_assets(self.shot_a, self.shot_b)
        write_full_receipt(self.receipts, self.shot_a, "1")  # beat 2 unreceived
        proc = run_assemble(self.requirements, self.assets, self.receipts,
                            self.audio, self.out)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertFalse(self.out.exists(), "no file may be assembled on pause")
        self.assertIn("REVIEW_REQUIRED", proc.stdout)

    def test_rejected_action_exits_1_with_no_output(self):
        self.write_assets(self.shot_a, self.shot_b)
        write_full_receipt(self.receipts, self.shot_a, "1")
        receipt = write_full_receipt(self.receipts, self.shot_b, "2")
        receipt["checks"]["action_present"] = False
        (self.receipts / "beat2.receipt.json").write_text(json.dumps(receipt))
        proc = run_assemble(self.requirements, self.assets, self.receipts,
                            self.audio, self.out)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertFalse(self.out.exists())
        self.assertIn("REJECTED", proc.stdout)

    def test_frozen_shot_exits_1_with_no_output(self):
        self.write_assets(self.shot_a, self.frozen)
        write_full_receipt(self.receipts, self.shot_a, "1")
        write_full_receipt(self.receipts, self.frozen, "2")
        proc = run_assemble(self.requirements, self.assets, self.receipts,
                            self.audio, self.out)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertFalse(self.out.exists(), "a frozen beat must never assemble")
        self.assertIn("freeze", proc.stdout)

    def test_clean_run_without_episode_receipt_is_candidate_exit_2(self):
        self.write_assets(self.shot_a, self.shot_b)
        write_full_receipt(self.receipts, self.shot_a, "1")
        write_full_receipt(self.receipts, self.shot_b, "2")
        proc = run_assemble(self.requirements, self.assets, self.receipts,
                            self.audio, self.out)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertTrue(self.out.exists())
        self.assertIn("REVIEW_REQUIRED", proc.stdout)  # candidate, not final

    def test_clean_run_with_episode_receipt_approves(self):
        self.write_assets(self.shot_a, self.shot_b)
        write_full_receipt(self.receipts, self.shot_a, "1")
        write_full_receipt(self.receipts, self.shot_b, "2")
        candidate = self.root / "candidate.mp4"
        proc = run_assemble(self.requirements, self.assets, self.receipts,
                            self.audio, candidate)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        episode_receipt = scaffold_receipt(candidate, "episode")
        episode_receipt["reviewer"] = "reviewer-one"
        episode_receipt["reviewed_at"] = "2026-10-25T19:00:00+05:30"
        episode_receipt["checks"] = {"full_playback": True, "emotional_listen": True}
        ep_path = self.root / "episode.receipt.json"
        ep_path.write_text(json.dumps(episode_receipt))
        final = self.root / "final.mp4"
        import shutil
        shutil.copy(candidate, final)
        proc = run_assemble(self.requirements, self.assets, self.receipts,
                            self.audio, final, episode_receipt=ep_path)
        # Receipt is bound to identical bytes (same content hash).
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('"episode_status": "APPROVED"', proc.stdout)


if __name__ == "__main__":
    unittest.main()
