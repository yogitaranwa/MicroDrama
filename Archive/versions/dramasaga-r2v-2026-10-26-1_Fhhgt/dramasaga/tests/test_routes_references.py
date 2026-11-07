import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from magicdrama.audiofirst.continuity import continuity_report
from magicdrama.audiofirst.references import coverage_report, validate_reference_bank
from magicdrama.audiofirst.routes import Route, default_registry, plan_route


def bank(views=("front", "close")):
    return {"references": [{"id": "harry", "kind": "character", "views": list(views),
                            "version": 1}]}


def story(framing="close", visible=("harry",)):
    return {"episodes": [{"shots": [
        {"id": "s1", "framing": framing, "visible_characters": list(visible)}]}]}


class ReferenceBankTests(unittest.TestCase):
    def test_valid_bank(self):
        self.assertEqual(validate_reference_bank(bank()), [])

    def test_duplicate_id_rejected(self):
        bad = {"references": [{"id": "h", "kind": "character", "views": ["front"]},
                              {"id": "h", "kind": "character", "views": ["close"]}]}
        self.assertTrue(any("duplicate" in e for e in validate_reference_bank(bad)))

    def test_bad_version_rejected(self):
        bad = {"references": [{"id": "h", "kind": "character", "views": ["front"], "version": 0}]}
        self.assertTrue(any("version" in e for e in validate_reference_bank(bad)))


class CoverageTests(unittest.TestCase):
    def test_covered_view_passes(self):
        self.assertEqual(coverage_report(story(), bank())["status"], "pass")

    def test_missing_view_is_explicit_gap_not_substitution(self):
        report = coverage_report(story(framing="profile"), bank())
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("explicit gap" in e and "no substitution" in e for e in report["errors"]))

    def test_unbanked_character_is_gap(self):
        report = coverage_report(story(visible=("draconia",)), bank())
        self.assertTrue(any("no reference banked" in e for e in report["errors"]))

    def test_missing_framing_flagged(self):
        report = coverage_report({"episodes": [{"shots": [{"id": "s1", "visible_characters": ["harry"]}]}]}, bank())
        self.assertEqual(report["status"], "fail")

    def test_invalid_bank_fails_closed(self):
        self.assertEqual(coverage_report(story(), {"references": "no"})["status"], "fail")


class RouteTests(unittest.TestCase):
    def test_prose_blocked_for_locked_camera_with_evidence(self):
        report = plan_route({"locked_camera": True})
        prose = next(r for r in report["routes"] if r["route"] == "prose_i2v")
        self.assertEqual(prose["status"], "blocked")
        self.assertTrue(any("F23" in e for e in prose["evidence"]))

    def test_unverified_route_caution(self):
        report = plan_route({"audio_led_performance": True})
        avatar = next(r for r in report["routes"] if r["route"] == "audio_led_avatar")
        self.assertEqual(avatar["status"], "caution")

    def test_all_blocked_reports_no_route(self):
        # structure_controls only unverified on vace; unsupported elsewhere, and
        # audio_led requirement blocks vace's audio gap - combine both flags
        report = plan_route({"masked_or_structured_edit": True, "audio_led_performance": True})
        statuses = {r["route"]: r["status"] for r in report["routes"]}
        self.assertIn(statuses["vace_masked_edit"], ("blocked", "caution"))
        self.assertEqual(statuses["prose_i2v"], "blocked")

    def test_duration_and_reference_limits(self):
        report = plan_route({"seconds": 20})
        self.assertEqual(next(r for r in report["routes"] if r["route"] == "audio_led_avatar")["status"], "blocked")
        report = plan_route({"references": 3})
        self.assertEqual(next(r for r in report["routes"] if r["route"] == "prose_i2v")["status"], "blocked")

    def test_override_rules(self):
        base = {"locked_camera": True}
        report = plan_route(base, overrides={"prose_i2v": {"operator": "", "reason": "x"}})
        self.assertEqual(next(r for r in report["routes"] if r["route"] == "prose_i2v")["status"], "blocked")
        report = plan_route(base, overrides={"prose_i2v": {"operator": "owner", "reason": "accept drift risk"}})
        prose = next(r for r in report["routes"] if r["route"] == "prose_i2v")
        self.assertEqual(prose["status"], "override")
        self.assertTrue(prose["blocked_reasons"])

    def test_bad_route_definition_rejected(self):
        with self.assertRaises(ValueError):
            Route(name="x", capabilities={"camera_control": "yes"}, reference_slots=0, max_seconds=None)

    def test_unknown_flag_rejected(self):
        with self.assertRaises(ValueError):
            plan_route({"looks_nice": True})


def v2_story(end_wardrobe="robe", end_eyeline=None, start_eyeline=None):
    def chard(wardrobe, eyeline):
        d = {"position": "door", "facing": "left", "wardrobe": wardrobe, "emotion": "calm"}
        if eyeline is not None:
            d["eyeline"] = eyeline
        return d
    shots = [{
        "id": "s1", "scene_id": "hall", "location": "hall", "visible_characters": ["harry"],
        "narrative_purpose": "establish hall",
        "start_state": {"characters": {"harry": chard("robe", start_eyeline)}, "props": {},
                        "knowledge": {"harry": []}},
        "end_state": {"characters": {"harry": chard(end_wardrobe, end_eyeline)}, "props": {},
                      "knowledge": {"harry": []}},
    }]
    return {"schema_version": 2, "episodes": [{"shots": shots}]}


class ContinuityExtensionTests(unittest.TestCase):
    def test_eyeline_optional(self):
        brief = {"characters": [{"id": "harry"}]}
        ok = continuity_report(brief, v2_story(end_eyeline="draconia", start_eyeline="draconia"))
        self.assertEqual(ok["errors"], [])
        # within one shot an eyeline change is legitimate staging when declared
        staged = v2_story(end_eyeline="lens", start_eyeline="draconia")
        staged["episodes"][0]["shots"][0]["changes"] = [
            {"field": "characters.harry.eyeline", "from": "draconia", "to": "lens",
             "reason": "he looks into the lens on the reveal"}]
        ok2 = continuity_report(brief, staged)
        self.assertEqual(ok2["errors"], [])
        # the same change without an explicit declaration is rejected
        undeclared = continuity_report(brief, v2_story(end_eyeline="lens", start_eyeline="draconia"))
        self.assertTrue(any("changed state fields" in e for e in undeclared["errors"]))

    def test_eyeline_change_flagged_on_same_scene_cut(self):
        brief = {"characters": [{"id": "harry"}]}
        s = v2_story(end_eyeline="draconia")
        s["episodes"][0]["shots"].append({
            "id": "s2", "scene_id": "hall", "location": "hall", "visible_characters": ["harry"],
            "narrative_purpose": "closer view",
            "start_state": {"characters": {"harry": {"position": "door", "facing": "left",
                                                     "wardrobe": "robe", "emotion": "calm",
                                                     "eyeline": "lens"}},
                            "props": {}, "knowledge": {"harry": []}},
            "end_state": {"characters": {"harry": {"position": "door", "facing": "left",
                                                   "wardrobe": "robe", "emotion": "calm",
                                                   "eyeline": "lens"}},
                          "props": {}, "knowledge": {"harry": []}},
        })
        errors = continuity_report(brief, s)["errors"]
        self.assertTrue(any("eyeline" in e for e in errors))

    def test_eyeline_reset_allowed_across_scenes(self):
        brief = {"characters": [{"id": "harry"}]}
        s = v2_story()
        s["episodes"][0]["shots"].append({
            "id": "s2", "scene_id": "garden", "location": "garden", "visible_characters": ["harry"],
            "narrative_purpose": "move outside", "transition_reason": "Harry leaves the hall",
            "start_state": {"characters": {"harry": {"position": "gate", "facing": "right",
                                                     "wardrobe": "robe", "emotion": "calm",
                                                     "eyeline": "sky"}},
                            "props": {}, "knowledge": {"harry": []}},
            "end_state": {"characters": {"harry": {"position": "gate", "facing": "right",
                                                   "wardrobe": "robe", "emotion": "calm",
                                                   "eyeline": "sky"}},
                          "props": {}, "knowledge": {"harry": []}},
        })
        self.assertEqual(continuity_report(brief, s)["errors"], [])


if __name__ == "__main__":
    unittest.main()


class RunnerIntegrationTests(unittest.TestCase):
    def setUp(self):
        from tests.helpers import pilot
        self.brief, self.story = pilot()

    def _run(self, story, brief=None):
        import tempfile
        from magicdrama.audiofirst.runner import run
        with tempfile.TemporaryDirectory() as tmp:
            return run(brief or self.brief, tmp, story)

    def test_declared_bank_gates_planning_fail_closed(self):
        import copy
        story = copy.deepcopy(self.story)
        story["reference_bank"] = {"references": [
            {"id": "harry", "kind": "character", "views": ["front"]}]}
        with self.assertRaisesRegex(ValueError, "Reference bank coverage failed"):
            self._run(story)

    def test_blocked_route_gates_planning_fail_closed(self):
        import copy
        story = copy.deepcopy(self.story)
        story["generation"] = {"route": "prose_i2v",
                               "hard_requirements": {"locked_camera": True}}
        with self.assertRaisesRegex(ValueError, "blocked by project failure evidence"):
            self._run(story)

    def test_no_declared_contracts_keeps_legacy_flow(self):
        result = self._run(self.story)
        self.assertEqual(result["continuity_status"], "contract_checked_not_semantic_proof")

    def test_covered_bank_and_overridden_route_write_reports(self):
        import copy, json, tempfile
        from magicdrama.audiofirst.runner import run
        story = copy.deepcopy(self.story)
        refs = []
        for ep in story["episodes"]:
            for shot in ep["shots"]:
                shot["framing"] = "front"
        ids = sorted({cid for ep in story["episodes"] for shot in ep["shots"]
                      for cid in shot.get("visible_characters", [])})
        story["reference_bank"] = {"references": [
            {"id": c, "kind": "character", "views": ["front", "close", "wide"]}
            for c in ids]}
        story["generation"] = {"route": "prose_i2v",
                               "hard_requirements": {"locked_camera": True},
                               "overrides": {"prose_i2v": {"operator": "test-operator",
                                                           "reason": "recorded risk acceptance"}}}
        with tempfile.TemporaryDirectory() as tmp:
            run(self.brief, tmp, story)
            plan = json.loads((Path(tmp) / "route-plan.json").read_text())
            self.assertTrue((Path(tmp) / "reference-coverage.json").is_file())
            selected = next(r for r in plan["routes"] if r["route"] == "prose_i2v")
            self.assertEqual(selected["status"], "override")
