import unittest
from pathlib import Path

from microdrama.scriptqa import validate_script_text
from microdrama.stills import build_candidate_plan, estimate_cost

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def test_v3_script_has_no_short_fragments(self):
        issues = validate_script_text((ROOT / "docs/E01_script_v3.md").read_text())
        self.assertFalse([i for i in issues if i.severity == "error"], issues)

    def test_script_time_notation_is_valid(self):
        bad = "Shot | 0:61-0:69 | visual | HARRY: \"Tell me you are not serious.\""
        issues = validate_script_text(bad)
        self.assertTrue(any("Invalid time notation" in i.message for i in issues))

    def test_right_sized_candidate_plan_is_explicit(self):
        plan = build_candidate_plan(ROOT / "config/E01_shot_plan_v3.json", 252)
        self.assertEqual(plan["candidate_count"], 252)
        self.assertEqual(plan["required_states"], 84)
        self.assertTrue(all("sword" in c["negative_prompt"] for c in plan["candidates"]))
        self.assertTrue(all("ice skates" in c["negative_prompt"] for c in plan["candidates"]))
        self.assertTrue(all("tiara" in c["negative_prompt"] for c in plan["candidates"]))
        self.assertTrue(all("black buttoned waistcoat" in c["prompt"] for c in plan["candidates"]))
        self.assertTrue(all("braided crown" not in c["prompt"] for c in plan["candidates"]))
        self.assertTrue(all("wand" in c["prompt"].lower() for c in plan["candidates"] if c["shot"] in {7, 8}))

    def test_cost_estimate_is_explicit_floor(self):
        est = estimate_cost(252, "nano-banana-2.1")
        self.assertEqual(est["estimated_floor_credits"], 12600)


if __name__ == "__main__":
    unittest.main()
