"""Floor-plan blocking: geometry, continuity checks, framing text and the layout drawing."""
import copy
import json
import unittest

import numpy as np

from magicdrama.audiofirst.blocking import (Camera, blocked_by_wall, check_blocking, facing_cos, framing_text, render_floor_plan, render_layout, view_report)
from magicdrama.audiofirst.directed import directed_prompt, keyframe_request, validate_directed
from tests.helpers import ROOT

STORY = json.loads((ROOT / 'examples' / 'late-night' / 'directed-story.json').read_text(encoding='utf-8'))
PLAN = STORY['plan']


class GeometryTests(unittest.TestCase):
    def test_camera_projection_puts_the_target_in_the_centre(self):
        cam = Camera([0, 0, 1.5], [4, 0, 1.5], lens=35)
        sx, sy, depth = cam.project([4, 0, 1.5])
        self.assertAlmostEqual(sx, 0, places=6);self.assertAlmostEqual(sy, 0, places=6);self.assertAlmostEqual(depth, 4, places=6)
        self.assertIsNone(cam.project([-1, 0, 1.5]))  # behind the camera
        self.assertGreater(cam.project([4, -1, 1.5])[0], 0)  # camera looks east, so south is on its right

    def test_the_wall_hides_the_chair_from_the_hallway_but_not_from_the_kitchen(self):
        chair_centre = [1.05, 2.95, 0.5]
        self.assertTrue(blocked_by_wall(PLAN, [-2.0, 1.6, 1.5], chair_centre))
        self.assertFalse(blocked_by_wall(PLAN, [1.5, 1.6, 1.5], chair_centre))
        self.assertFalse(blocked_by_wall(PLAN, [-2.0, 1.6, 1.5], [3.0, 1.7, 0.5]))  # the table is visible through the doorway

    def test_facing_towards_and_away_from_the_camera(self):
        self.assertGreater(facing_cos([0, 0], 0, [5, 0, 1]), 0.99)
        self.assertLess(facing_cos([0, 0], 180, [5, 0, 1]), -0.99)


class ScriptSupervisionTests(unittest.TestCase):
    def test_the_directed_script_blocking_is_consistent(self):
        self.assertEqual(check_blocking(STORY), [])
        self.assertTrue(validate_directed(STORY))

    def test_a_person_who_teleports_between_shots_is_caught(self):
        bad = copy.deepcopy(STORY)
        bad['plan']['shots']['d4-answer']['figures']['Mia']['start']['pos'] = [2.5, 0.5]
        self.assertTrue(any('teleport' in p for p in check_blocking(bad)))
        with self.assertRaisesRegex(ValueError, 'teleport'):validate_directed(bad)

    def test_a_reverse_shot_that_would_show_what_is_behind_the_camera_is_caught(self):
        bad = copy.deepcopy(STORY)
        bad['plan']['shots']['d4-answer']['camera']['end']['target'] = [3.0, 1.7, 1.2]  # turned round to face the table and window
        problems = check_blocking(bad)
        self.assertTrue(any('would be in frame' in p or 'should be in frame' in p for p in problems))

    def test_a_speaker_with_their_back_to_the_camera_is_caught(self):
        bad = copy.deepcopy(STORY)
        bad['plan']['shots']['d5-receipt']['figures']['Tomas']['end']['facing'] = 54  # turned away from the camera
        self.assertTrue(any('back to the camera' in p for p in check_blocking(bad)))

    def test_a_shot_with_no_blocking_entry_is_caught(self):
        bad = copy.deepcopy(STORY)
        del bad['plan']['shots']['d2-switch']
        self.assertTrue(any('no blocking entry' in p for p in check_blocking(bad)))


class FramingTests(unittest.TestCase):
    def test_the_reverse_shot_sees_the_doorway_behind_mia_and_not_the_window(self):
        r = view_report(PLAN, 'd4-answer', 'end')
        self.assertIn('doorway to the dark hallway', [n for n, _ in r['visible']])
        self.assertIn('tall window with city lights', r['not_visible'])
        self.assertIn('table', r['not_visible'])
        mia = next(p for p in r['people'] if p['name'] == 'Mia')
        self.assertEqual(mia['screen'], 'centre');self.assertEqual(mia['facing'], 'facing the camera')

    def test_the_hallway_shots_cannot_see_tomas_but_the_reveal_can(self):
        self.assertIn("Tomas's wooden chair", view_report(PLAN, 'd2-switch', 'end')['not_visible'])
        reveal = view_report(PLAN, 'd3-reveal', 'end')
        self.assertTrue(next(p for p in reveal['people'] if p['name'] == 'Tomas')['coverage'] > 0)

    def test_prompts_and_keyframes_carry_the_framing_and_the_layout_guide(self):
        p4 = directed_prompt(STORY, 3)
        self.assertIn('FRAMING (exact, from the floor plan)', p4)
        self.assertIn('NOT in frame (do not draw)', p4)
        self.assertLessEqual(len(p4), 2500)
        k = keyframe_request(STORY, 3)
        self.assertEqual(k['refs'][-1], 'layout:d4-answer')
        self.assertIn('LAYOUT GUIDE', k['prompt'])
        self.assertIn('doorway to the dark hallway', k['prompt'])

    def test_every_prompt_fits_the_service_limit(self):
        for i in range(len(STORY['shots'])):
            self.assertLessEqual(len(directed_prompt(STORY, i)), 2500)

    def test_framing_text_names_the_camera_direction(self):
        text = framing_text(PLAN, 'd1-return')
        self.assertIn('camera looks east', text)


class RenderTests(unittest.TestCase):
    def test_layout_drawings_are_not_blank_and_differ_between_shots(self):
        a = np.asarray(render_layout(PLAN, 'd2-switch', 'start', size=(320, 180)))
        b = np.asarray(render_layout(PLAN, 'd4-answer', 'start', size=(320, 180)))
        self.assertEqual(a.shape, (180, 320, 3))
        self.assertGreater(len({tuple(px) for px in a.reshape(-1, 3)}), 4)
        self.assertGreater(np.abs(a.astype(int) - b.astype(int)).mean(), 10)

    def test_the_hidden_chair_is_not_drawn_over_the_wall_in_a_hallway_shot(self):
        img = np.asarray(render_layout(PLAN, 'd2-switch', 'end', size=(480, 270)))
        chair = np.array([0x6b, 0x4a, 0x2b])
        brownish = (np.abs(img.astype(int) - chair * 0.8).sum(axis=2) < 40).sum()
        self.assertLess(brownish, 40)

    def test_the_floor_plan_draws(self):
        self.assertEqual(render_floor_plan(PLAN, 'd3-reveal').size, (720, 520))


if __name__ == '__main__':
    unittest.main()
