import json
import tempfile
import unittest
from pathlib import Path

from microdrama.manifest import sha256_file
from microdrama.reviewgate import (APPROVED, REJECTED, REVIEW_REQUIRED,
                                   evaluate_episode, evaluate_shot, gate_check,
                                   scaffold_receipt)
from test_detectors import make_video

REQ = {"beat": "3", "start": 13.584, "end": 22.584,
       "required_actions": ["ice arrows hit", "a guest freezes mid-run"],
       "lines": [{"line": 2, "start": 14.484, "end": 18.024}]}


def full_receipt(asset: Path, beat: str, reviewer: str = "reviewer-one") -> dict:
    receipt = scaffold_receipt(asset, beat)
    receipt["reviewer"] = reviewer
    receipt["reviewed_at"] = "2026-10-25T18:00:00+05:30"
    receipt["checks"] = {k: True for k in receipt["checks"]}
    return receipt


class ReviewGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.moving = make_video(root / "shot-clean.mp4", "testsrc2=size=320x240:rate=10",
                                "sine=frequency=440", duration=3.0)
        cls.frozen = make_video(root / "shot-frozen.mp4", "color=c=blue:size=320x240:rate=10",
                                "sine=frequency=440", duration=3.0)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_missing_receipt_pauses_for_review(self):
        result = evaluate_shot(REQ, self.moving, None)
        self.assertEqual(result["status"], REVIEW_REQUIRED)

    def test_complete_receipt_approves_clean_shot(self):
        result = evaluate_shot(REQ, self.moving, full_receipt(self.moving, "3"))
        self.assertEqual(result["status"], APPROVED, result["reasons"])

    def test_action_absent_is_strict_reject(self):
        receipt = full_receipt(self.moving, "3")
        receipt["checks"]["action_present"] = False
        result = evaluate_shot(REQ, self.moving, receipt)
        self.assertEqual(result["status"], REJECTED)

    def test_freeze_is_hard_reject_even_with_receipt(self):
        result = evaluate_shot(REQ, self.frozen, full_receipt(self.frozen, "3"))
        self.assertEqual(result["status"], REJECTED)
        self.assertTrue(any("freeze" in r for r in result["reasons"]))

    def test_stale_receipt_after_byte_change_pauses(self):
        receipt = full_receipt(self.moving, "3")
        with self.moving.open("ab") as f:
            f.write(b"tamper")
        result = evaluate_shot(REQ, self.moving, receipt)
        self.assertEqual(result["status"], REVIEW_REQUIRED)
        self.assertTrue(any("stale" in r for r in result["reasons"]))
        self.moving.write_bytes(self.moving.read_bytes()[:-6])
        self.assertEqual(receipt["asset_sha256"], sha256_file(self.moving))

    def test_gate_check_counts(self):
        requirements = {"beats": [REQ, {**REQ, "beat": "4"}]}
        assets = {"3": str(self.moving), "4": str(self.frozen)}
        receipts = {"3": full_receipt(self.moving, "3"),
                    "4": full_receipt(self.frozen, "4")}
        result = gate_check(requirements, assets, receipts)
        self.assertEqual(result["counts"][APPROVED], 1)
        self.assertEqual(result["counts"][REJECTED], 1)
        self.assertFalse(result["all_approved"])

    def test_episode_needs_playback_and_listen_receipt(self):
        result = evaluate_episode(self.moving, None)
        self.assertEqual(result["status"], REVIEW_REQUIRED)
        receipt = full_receipt(self.moving, "episode")
        receipt["checks"] = {"full_playback": True, "emotional_listen": True}
        result = evaluate_episode(self.moving, receipt)
        self.assertEqual(result["status"], APPROVED, result["reasons"])

    def test_episode_mechanical_defect_blocks_approval(self):
        receipt = full_receipt(self.frozen, "episode")
        receipt["checks"] = {"full_playback": True, "emotional_listen": True}
        result = evaluate_episode(self.frozen, receipt)
        self.assertEqual(result["status"], REVIEW_REQUIRED)


if __name__ == "__main__":
    unittest.main()
