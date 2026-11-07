import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from microdrama.continuity import (check_cut_transition, check_reference_coverage,
                                   validate_action_phases, validate_continuity_document,
                                   validate_reference_bank)
from microdrama.routes import Route, default_registry, plan_route


def bank(views=("front", "close")):
    return {"references": [{"id": "harry", "kind": "character", "views": list(views)}]}


def state(wardrobe="robe", position="door", emotion="calm", eyeline="draconia", props=None):
    return {"characters": {"harry": {"position": position, "facing": "left", "eyeline": eyeline,
                                     "wardrobe": wardrobe, "emotion": emotion, "props": props or {}}},
            "lighting": "warm"}


def shot(sid="s1", scene="a", framing="close", action=None):
    return {"id": sid, "scene_id": scene, "framing": framing, "visible_characters": ["harry"],
            "start_state": state(), "end_state": state(), "action": action}


def doc(shots, views=("front", "close")):
    return {"reference_bank": bank(views), "cast": ["harry"], "shots": shots}


class ReferenceBankTests(unittest.TestCase):
    def test_valid_bank(self):
        self.assertEqual(validate_reference_bank(bank()), [])

    def test_duplicate_ids_rejected(self):
        bad = {"references": [{"id": "harry", "kind": "character", "views": ["front"]},
                              {"id": "harry", "kind": "character", "views": ["profile"]}]}
        self.assertTrue(any("duplicate" in e for e in validate_reference_bank(bad)))

    def test_unknown_view_rejected(self):
        bad = {"references": [{"id": "harry", "kind": "character", "views": ["aerial"]}]}
        self.assertTrue(any("unknown views" in e for e in validate_reference_bank(bad)))


class CoverageTests(unittest.TestCase):
    def test_missing_view_is_explicit_gap_not_substitution(self):
        s = shot(framing="profile")
        errors = check_reference_coverage(s, bank())
        self.assertTrue(any("explicit gap" in e and "no substitution" in e for e in errors))

    def test_missing_reference_is_explicit_gap(self):
        s = shot()
        s["visible_characters"] = ["draconia"]
        self.assertTrue(any("no reference banked" in e for e in check_reference_coverage(s, bank())))

    def test_covered_view_passes(self):
        self.assertEqual(check_reference_coverage(shot(framing="close"), bank()), [])


class CutTransitionTests(unittest.TestCase):
    def test_same_scene_wardrobe_change_flagged(self):
        errors = check_cut_transition(state(), state(wardrobe="sweater"), same_scene=True)
        self.assertTrue(any("wardrobe" in e for e in errors))

    def test_wardrobe_change_flagged_even_across_scenes(self):
        errors = check_cut_transition(state(), state(wardrobe="sweater"), same_scene=False)
        self.assertTrue(any("wardrobe" in e for e in errors))

    def test_physical_reset_allowed_across_scenes(self):
        errors = check_cut_transition(state(), state(position="stairs", emotion="shaken"), same_scene=False)
        self.assertEqual(errors, [])

    def test_prop_hand_change_flagged(self):
        before = state(props={"wand": {"hand": "right", "count": 1}})
        after = state(props={"wand": {"hand": "left", "count": 1}})
        self.assertTrue(any("prop change" in e for e in check_cut_transition(before, after, same_scene=False)))

    def test_lighting_change_within_scene_flagged(self):
        after = state()
        after["lighting"] = "cold"
        self.assertTrue(any("lighting" in e for e in check_cut_transition(state(), after, same_scene=True)))


class ActionPhaseTests(unittest.TestCase):
    def test_action_requires_all_phases(self):
        s = shot(action={"summary": "table flip", "phases": {"before": {"description": "grip", "review_items": ["hands on edge"]}}})
        self.assertTrue(any("phases" in e for e in validate_action_phases(s)))

    def test_complete_phases_pass(self):
        phases = {p: {"description": p, "review_items": ["visible"]} for p in ("before", "contact", "after")}
        self.assertEqual(validate_action_phases(shot(action={"summary": "flip", "phases": phases})), [])

    def test_phase_needs_review_items(self):
        phases = {p: {"description": p, "review_items": []} for p in ("before", "contact", "after")}
        self.assertTrue(any("review_items" in e for e in validate_action_phases(shot(action={"summary": "flip", "phases": phases}))))


class DocumentTests(unittest.TestCase):
    def test_clean_document_passes(self):
        self.assertEqual(validate_continuity_document(doc([shot()]))["status"], "pass")

    def test_offscreen_cast_must_be_enumerated(self):
        bad = doc([shot()])
        bad["cast"] = ["harry", "draconia"]
        self.assertEqual(validate_continuity_document(bad)["status"], "fail")

    def test_two_shot_cut_checked(self):
        s2 = shot(sid="s2", scene="a")
        s2["start_state"] = state(wardrobe="sweater")
        self.assertEqual(validate_continuity_document(doc([shot(), s2]))["status"], "fail")


class RouteTests(unittest.TestCase):
    def test_prose_route_blocked_for_locked_camera(self):
        report = plan_route({"locked_camera": True})
        prose = next(r for r in report["routes"] if r["route"] == "prose_i2v")
        self.assertEqual(prose["status"], "blocked")
        self.assertTrue(any("F23" in e or "F22" in e for e in prose["evidence"]))

    def test_unverified_route_is_caution_not_allowed(self):
        report = plan_route({"locked_camera": True})
        h3 = next(r for r in report["routes"] if r["route"] == "reference_r2v_h3")
        self.assertEqual(h3["status"], "caution")

    def test_no_hard_requirements_allows_prose(self):
        report = plan_route({})
        prose = next(r for r in report["routes"] if r["route"] == "prose_i2v")
        self.assertEqual(prose["status"], "allowed")

    def test_duration_limit_blocks(self):
        report = plan_route({"seconds": 20})
        avatar = next(r for r in report["routes"] if r["route"] == "audio_led_avatar")
        self.assertEqual(avatar["status"], "blocked")

    def test_reference_slots_block(self):
        report = plan_route({"references": 3})
        prose = next(r for r in report["routes"] if r["route"] == "prose_i2v")
        self.assertEqual(prose["status"], "blocked")

    def test_override_needs_named_operator_and_reason(self):
        report = plan_route({"locked_camera": True}, overrides={"prose_i2v": {"operator": "", "reason": "x"}})
        prose = next(r for r in report["routes"] if r["route"] == "prose_i2v")
        self.assertEqual(prose["status"], "blocked")
        report = plan_route({"locked_camera": True},
                            overrides={"prose_i2v": {"operator": "owner", "reason": "accept drift risk for test"}})
        prose = next(r for r in report["routes"] if r["route"] == "prose_i2v")
        self.assertEqual(prose["status"], "override")
        self.assertTrue(prose["blocked_reasons"], "override must not erase the evidence")

    def test_unknown_requirement_flag_rejected(self):
        with self.assertRaises(ValueError):
            plan_route({"make_it_good": True})

    def test_route_definition_validated(self):
        with self.assertRaises(ValueError):
            Route(name="bad", capabilities={"camera_control": "great"}, reference_slots=0, max_seconds=None)
        with self.assertRaises(ValueError):
            Route(name="bad", capabilities={}, reference_slots=0, max_seconds=None)

    def test_registry_covers_all_capabilities(self):
        for route in default_registry().values():
            self.assertEqual(len(route.capabilities), 6)


class CliTests(unittest.TestCase):
    def test_validate_continuity_cli(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            contract = Path(td) / "contract.json"
            contract.write_text(json.dumps(doc([shot()])))
            ok = subprocess.run([sys.executable, str(root / "run_pipeline.py"),
                                 "validate-continuity", "--contract", str(contract)],
                                capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            s2 = shot(sid="s2", scene="a")
            s2["start_state"] = state(wardrobe="sweater")
            contract.write_text(json.dumps(doc([shot(), s2])))
            bad = subprocess.run([sys.executable, str(root / "run_pipeline.py"),
                                  "validate-continuity", "--contract", str(contract)],
                                 capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)

    def test_plan_route_cli(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            req = Path(td) / "req.json"
            req.write_text(json.dumps({"locked_camera": True}))
            run = subprocess.run([sys.executable, str(root / "run_pipeline.py"),
                                  "plan-route", "--requirements", str(req)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0)
            report = json.loads(run.stdout)
            self.assertEqual(report["status"], "ok")


if __name__ == "__main__":
    unittest.main()


def _beats():
    return {"beats": [{"beat": 1, "start": 0.0, "end": 5.0,
                       "required_actions": ["hero enters"],
                       "lines": [{"start": 1.0, "end": 2.0}]}]}


class GateIntegrationTests(unittest.TestCase):
    """Declared contracts gate fail-closed through every reviewgate consumer."""

    def test_failing_continuity_contract_blocks_gate(self):
        from microdrama.reviewgate import gate_check
        reqs = _beats()
        reqs["continuity"] = doc([shot()], views=("front",))  # close view unbanked
        with self.assertRaisesRegex(ValueError, "Continuity contract failed"):
            gate_check(reqs, {})

    def test_blocked_route_blocks_gate(self):
        from microdrama.reviewgate import gate_check
        reqs = _beats()
        reqs["generation"] = {"route": "prose_i2v",
                              "hard_requirements": {"locked_camera": True}}
        with self.assertRaisesRegex(ValueError, "blocked by project failure evidence"):
            gate_check(reqs, {})

    def test_unknown_route_blocks_gate(self):
        from microdrama.reviewgate import gate_check
        reqs = _beats()
        reqs["generation"] = {"route": "invented_route"}
        with self.assertRaisesRegex(ValueError, "Unknown generation route"):
            gate_check(reqs, {})

    def test_operator_override_passes_gate_with_evidence_intact(self):
        from microdrama.reviewgate import gate_check
        reqs = _beats()
        reqs["generation"] = {"route": "prose_i2v",
                              "hard_requirements": {"locked_camera": True},
                              "overrides": {"prose_i2v": {"operator": "test-operator",
                                                          "reason": "recorded risk acceptance"}}}
        result = gate_check(reqs, {})
        self.assertFalse(result["all_approved"])  # still needs real assets/receipts

    def test_empty_override_does_not_unblock(self):
        from microdrama.reviewgate import gate_check
        reqs = _beats()
        reqs["generation"] = {"route": "prose_i2v",
                              "hard_requirements": {"locked_camera": True},
                              "overrides": {"prose_i2v": {"operator": "", "reason": ""}}}
        with self.assertRaisesRegex(ValueError, "blocked by project failure evidence"):
            gate_check(reqs, {})

    def test_passing_contract_and_caution_route_keep_gate_behavior(self):
        from microdrama.reviewgate import gate_check
        reqs = _beats()
        reqs["continuity"] = doc([shot()])
        reqs["generation"] = {"route": "reference_r2v_h3",
                              "hard_requirements": {"locked_camera": True}}
        result = gate_check(reqs, {})
        self.assertFalse(result["all_approved"])  # no assets: review required, not a crash
