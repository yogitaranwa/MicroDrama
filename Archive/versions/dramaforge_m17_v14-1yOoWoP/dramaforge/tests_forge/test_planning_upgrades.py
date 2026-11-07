"""DramaSaga-derived planning upgrades. Stdlib unittest so they run without pytest."""
import asyncio
import json
import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

from forge.planning import (build_visual_bible, director_prompt, enrich_plan,
                            layout_svg, validate_plan, validate_plan_blocking,
                            validate_plan_continuity)
from forge.gates import GateLocked
from forge.render_plan import build_render_jobs, default_prompt, dry_run, execute_plan


class RouteTests(unittest.TestCase):
    def test_veo_audio_quote_snaps_to_supported_duration(self):
        report = validate_plan([{"plan_n": 1, "seconds": 5.1}], "veo3.1-lite",
                               resolution="720p", audio=True)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["jobs"][0]["seconds"], 6)
        self.assertEqual(report["jobs"][0]["credits"], 6 * 72)

    def test_continuous_route_accepts_integer_snap_and_rejects_overrun(self):
        report = validate_plan([{"plan_n": 1, "seconds": 1.2}], "ltx-2.5",
                               resolution="720p", audio=True)
        self.assertTrue(report["ok"])
        self.assertEqual(report["jobs"][0]["seconds"], 2)
        bad = validate_plan([{"plan_n": 1, "seconds": 61}], "ltx-2.5",
                            resolution="720p", audio=True)
        self.assertFalse(bad["ok"])

    def test_credit_cap_fails_closed(self):
        report = validate_plan([{"plan_n": 1, "seconds": 5}], "kling-3.0",
                               resolution="720p", audio=True, credit_cap=100)
        self.assertFalse(report["ok"])
        self.assertIn("credit cap exceeded", report["errors"][-1]["error"])


class ContinuityTests(unittest.TestCase):
    def test_reasoned_character_and_knowledge_changes_are_tracked(self):
        shots = [{
            "plan_n": 1,
            "lines": [{"speaker": "Asha", "text": "I found the key."}],
            "continuity": [
                {"scope": "character", "name": "Asha", "field": "has_key", "to": True,
                 "reason": "She finds the key in shot one."},
                {"scope": "knowledge", "fact": "The door is locked", "character": "Asha",
                 "reason": "She tries the door before finding the key."},
            ],
        }]
        report = validate_plan_continuity(shots)
        self.assertTrue(report["ok"], report["errors"])
        self.assertTrue(report["state"]["characters"]["Asha"]["facts"]["has_key"])
        self.assertEqual(report["state"]["knowledge"]["The door is locked"]["known_by"], ["Asha"])

    def test_missing_reason_and_unknown_character_fail(self):
        shots = [{"plan_n": 1, "lines": [{"speaker": "Asha", "text": "Hello."}],
                  "continuity": [{"scope": "character", "name": "Asha", "field": "has_key", "to": True},
                                 {"scope": "knowledge", "fact": "Secret", "character": "Ravi", "reason": "He heard it."}]}]
        report = validate_plan_continuity(shots)
        self.assertFalse(report["ok"])
        self.assertEqual(len(report["errors"]), 2)


class BlockingTests(unittest.TestCase):
    def layout(self):
        return {"width": 10, "depth": 8,
                "cameras": {"wide": {"x": 5, "y": 0, "angle": 90, "fov": 80}},
                "actors": {"Asha": {"x": 3, "y": 4, "facing": 270},
                           "Ravi": {"x": 8, "y": 4, "facing": 270}},
                "obstacles": [{"name": "table", "x": 6.5, "y": 0.5, "width": 1, "depth": 5}]}

    def test_must_show_and_occluded_must_not_show(self):
        shot = {"plan_n": 1, "kind": "speaker", "speaker": "Asha",
                "blocking": {"camera": "wide", "must_show": ["Asha"], "must_not_show": ["Ravi"]}}
        report = validate_plan_blocking(self.layout(), [shot])
        self.assertTrue(report["ok"], report["errors"])
        self.assertTrue(report["shots"][0]["visible"]["Asha"])
        self.assertFalse(report["shots"][0]["visible"]["Ravi"])

    def test_teleport_between_explicit_positions_fails(self):
        shots = [
            {"plan_n": 1, "blocking": {"camera": "wide", "positions": {"Asha": {"x": 3, "y": 4}}}},
            {"plan_n": 2, "blocking": {"camera": "wide", "positions": {"Asha": {"x": 9, "y": 4}}}},
        ]
        report = validate_plan_blocking(self.layout(), shots)
        self.assertFalse(report["ok"])
        self.assertIn("moves", report["errors"][0]["error"])

    def test_layout_svg_uses_supplied_names(self):
        svg = layout_svg(self.layout())
        self.assertIn("Asha", svg)
        self.assertIn("wide", svg)
        self.assertNotIn("Mia", svg)
        self.assertNotIn("Tomas", svg)


class DirectorTests(unittest.TestCase):
    def test_director_prompt_is_bounded_and_uses_end_state(self):
        bible = build_visual_bible(
            style="Photorealistic vertical microdrama",
            locations={"kitchen": "Small blue kitchen, window on the left wall."},
            characters={"Asha": "Asha has short black hair and wears a red jacket."},
            lighting={"kitchen": "Cool window light with a warm practical over the table."})
        shot = {"kind": "speaker", "speaker": "Asha", "location": "kitchen",
                "camera": "single:Asha", "action": "she holds the key",
                "line": {"text": "I found it where you left it."},
                "end_state": "Asha stands by the table with the key raised."}
        prompt = director_prompt(shot, bible, previous_end_state="Asha enters from the hallway.")
        self.assertLessEqual(len(prompt), 2500)
        self.assertIn("Small blue kitchen", prompt)
        self.assertIn("Asha enters from the hallway", prompt)
        self.assertIn("I found it where you left it", prompt)

    def test_enrich_plan_combines_reports_without_mutating_input(self):
        shots = [{"plan_n": 1, "kind": "speaker", "speaker": "Asha", "location": "kitchen",
                  "camera": "single:Asha", "action": "she holds the key", "seconds": 4,
                  "line": {"text": "I found it."},
                  "continuity": [{"scope": "character", "name": "Asha", "field": "has_key",
                                  "to": True, "reason": "She found it before this shot."}]}]
        result = enrich_plan(shots, model="veo3.1-lite", resolution="720p", audio=True)
        self.assertTrue(result["ok"], result["reports"])
        self.assertIn("director_prompt", result["shots"][0])
        self.assertNotIn("director_prompt", shots[0])
        self.assertEqual(result["reports"]["route"]["jobs"][0]["credits"], 4 * 72)


class RenderPlanCompatibilityTests(unittest.TestCase):
    def _project(self, plan):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "out").mkdir()
        (root / "out" / "e01_plan.json").write_text(json.dumps(plan))
        return tmp, root

    def test_old_render_plan_flow_is_unchanged(self):
        plan = [{"plan_n": 1, "kind": "speaker", "speaker": "Asha", "location": "kitchen",
                 "camera": "single:Asha", "action": "she sits", "seconds": 5,
                 "line": {"text": "One line only."}}]
        tmp, root = self._project(plan)
        self.addCleanup(tmp.cleanup)
        jobs = build_render_jobs(root)
        self.assertEqual(jobs[0]["prompt"], default_prompt(plan[0]))
        manifest = dry_run(root, credits_per_second=10)
        self.assertEqual(manifest["jobs"][0]["credits_est"], 50)
        self.assertNotIn("route_report", manifest)

    def test_new_render_plan_route_and_director_prompt_are_opt_in(self):
        plan = [{"plan_n": 1, "kind": "speaker", "speaker": "Asha", "location": "kitchen",
                 "camera": "single:Asha", "action": "she sits", "seconds": 5.1,
                 "line": {"text": "One line only."}}]
        tmp, root = self._project(plan)
        self.addCleanup(tmp.cleanup)
        bible = {"locations": {"kitchen": "Small blue kitchen."},
                 "characters": {"Asha": "Asha wears a red jacket."}}
        manifest = dry_run(root, route_name="veo3.1-lite", resolution="720p",
                           audio=True, director_bible=bible)
        job = manifest["jobs"][0]
        self.assertEqual(job["requested_seconds"], 5.1)
        self.assertEqual(job["seconds"], 6)
        self.assertEqual(job["credits_est"], 432)
        self.assertIn("Small blue kitchen", job["prompt"])
        self.assertIn("route_report", manifest)
        self.assertTrue(manifest["route_report"]["ok"])


class RouteExecuteTests(unittest.TestCase):
    def _project(self):
        plan = [{"plan_n": 1, "kind": "visual", "speaker": None, "location": "kitchen",
                 "camera": "wide", "action": "steam rises", "seconds": 5.1}]
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "out").mkdir()
        (root / "out" / "e01_plan.json").write_text(json.dumps(plan))
        self.addCleanup(tmp.cleanup)
        return root

    class MatchingGenerator:
        model = "veo3.1-lite"
        resolution = "720p"
        supports_audio_request = True

        def __init__(self):
            self.calls = []

        def estimate(self, seconds, audio=False):
            return int(seconds * (48 + (24 if audio else 0)))

        async def generate_single_video(self, prompt, refs, **kwargs):
            self.calls.append((prompt, refs, kwargs))
            return SimpleNamespace(data="clip-url")

    class LegacyEstimateGenerator(MatchingGenerator):
        def estimate(self, seconds, audio=False):
            return int(seconds * 24)

    def test_execute_route_uses_snapped_duration_audio_and_matching_quote(self):
        root = self._project()
        generator = self.MatchingGenerator()
        urls = asyncio.run(execute_plan(root, generator, route_name="veo3.1-lite",
                                        resolution="720p", audio=True))
        self.assertEqual(urls, ["clip-url"])
        self.assertEqual(generator.calls[0][2]["seconds"], 6)
        self.assertIs(generator.calls[0][2]["audio"], True)

    def test_execute_route_estimate_mismatch_fails_before_any_call(self):
        root = self._project()
        generator = self.LegacyEstimateGenerator()
        with self.assertRaisesRegex(GateLocked, "ledger estimate mismatch"):
            asyncio.run(execute_plan(root, generator, route_name="veo3.1-lite",
                                     resolution="720p", audio=True))
        self.assertEqual(generator.calls, [])

    def test_execute_route_model_mismatch_fails_before_any_call(self):
        root = self._project()
        generator = self.MatchingGenerator()
        generator.model = "ltx-2.5"
        with self.assertRaisesRegex(GateLocked, "model/resolution"):
            asyncio.run(execute_plan(root, generator, route_name="veo3.1-lite",
                                     resolution="720p", audio=True))
        self.assertEqual(generator.calls, [])


class MagicHourRouteAlignmentTests(unittest.TestCase):
    def _generator(self, tmp):
        try:
            from tools.video_generator_magichour_api import VideoGeneratorMagicHourAPI
        except ModuleNotFoundError as e:
            raise unittest.SkipTest(f"optional project dependency unavailable: {e.name}")
        ledger = Path(tmp) / "ledger.json"
        ledger.write_text(json.dumps({"approved": 500, "spent": 0}))
        return VideoGeneratorMagicHourAPI(
            "test-key", model="veo3.1-lite", resolution="720p",
            credits_per_second=48, audio=True, audio_credits_per_second=24,
            ledger_path=str(ledger), enforce_gates=False), ledger

    def test_magichour_audio_request_and_ledger_use_same_route_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator, ledger_path = self._generator(tmp)
            old_live = os.environ.get("FORGE_LIVE")
            os.environ["FORGE_LIVE"] = "1"
            try:
                calls = []
                async def run():
                    async def fake_to_thread(func, *args):
                        calls.append(args)
                        return "clip-url"
                    with unittest.mock.patch("asyncio.to_thread", side_effect=fake_to_thread):
                        out = await generator.generate_single_video("prompt", [], seconds=6, audio=True)
                    return out
                out = asyncio.run(run())
            finally:
                if old_live is None:
                    os.environ.pop("FORGE_LIVE", None)
                else:
                    os.environ["FORGE_LIVE"] = old_live
            self.assertEqual(getattr(out, "data", out), "clip-url")
            self.assertEqual(calls[0][2:], (6, True))
            self.assertEqual(json.loads(ledger_path.read_text())["spent"], 432)

    def test_magichour_request_body_carries_audio_only_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator, _ = self._generator(tmp)
            response_post = unittest.mock.Mock()
            response_post.json.return_value = {"id": "job1"}
            response_post.raise_for_status.return_value = None
            response_get = unittest.mock.Mock()
            response_get.json.return_value = {"status": "complete", "downloads": [{"url": "clip-url"}]}
            with unittest.mock.patch("tools.video_generator_magichour_api.requests.post", return_value=response_post) as post,                  unittest.mock.patch("tools.video_generator_magichour_api.requests.get", return_value=response_get):
                self.assertEqual(generator._call("prompt", None, 6, audio=True), "clip-url")
            body = post.call_args.kwargs["json"]
            self.assertEqual(body["model"], "veo3.1-lite")
            self.assertEqual(body["resolution"], "720p")
            self.assertEqual(body["end_seconds"], 6)
            self.assertIs(body["audio"], True)

            with unittest.mock.patch("tools.video_generator_magichour_api.requests.post", return_value=response_post) as post,                  unittest.mock.patch("tools.video_generator_magichour_api.requests.get", return_value=response_get):
                generator._call("prompt", None, 6, audio=False)
            self.assertNotIn("audio", post.call_args.kwargs["json"])


if __name__ == "__main__":
    unittest.main()
