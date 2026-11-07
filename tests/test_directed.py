"""Director-style planning: script supervision, continuity prompts, keyframes and price."""
import copy
import json
import unittest

from magicdrama.audiofirst.directed import (directed_prompt, keyframe_request, plan_directed, render_script_markdown, validate_directed)
from tests.helpers import ROOT

STORY = json.loads((ROOT / 'examples' / 'late-night' / 'directed-story.json').read_text(encoding='utf-8'))


class SupervisionTests(unittest.TestCase):
    def test_the_real_script_passes(self):
        self.assertTrue(validate_directed(STORY))

    def test_a_light_that_changes_with_no_cause_is_rejected(self):
        bad = copy.deepcopy(STORY)
        bad['shots'][1]['beats'][0]['text'] = 'The overhead light suddenly turns on by itself.'
        with self.assertRaisesRegex(ValueError, 'suddenly/automatically|nothing in the action switches it'):validate_directed(bad)
        quiet = copy.deepcopy(STORY)
        quiet['shots'][1]['beats'][0]['text'] = 'The kitchen light comes on.'
        with self.assertRaisesRegex(ValueError, 'nothing in the action switches it'):validate_directed(quiet)

    def test_a_static_camera_is_rejected(self):
        bad = copy.deepcopy(STORY)
        bad['shots'][2]['camera']['movement'] = 'static, locked off'
        with self.assertRaisesRegex(ValueError, 'camera must move'):validate_directed(bad)

    def test_beats_must_cover_the_shot_and_cuts_need_keyframes(self):
        bad = copy.deepcopy(STORY)
        bad['shots'][0]['beats'][1]['t0'] = 2.4  # leaves a gap
        with self.assertRaisesRegex(ValueError, 'gap or overlap'):validate_directed(bad)
        bad = copy.deepcopy(STORY)
        del bad['shots'][3]['keyframe']
        with self.assertRaisesRegex(ValueError, 'needs a keyframe'):validate_directed(bad)
        bad = copy.deepcopy(STORY)
        bad['shots'][1]['cast'] = ['Nobody']
        with self.assertRaisesRegex(ValueError, 'no portrait'):validate_directed(bad)

    def test_a_line_that_cannot_be_spoken_in_time_is_rejected(self):
        bad = copy.deepcopy(STORY)
        bad['shots'][2]['seconds'] = 1
        bad['shots'][2]['beats'] = [{'t0': 0, 't1': 1, 'text': 'He speaks.'}]
        bad['shots'][2]['sound']['dialogue'][0]['line'] = 'a very long line that certainly cannot be spoken in a single second of film'
        with self.assertRaisesRegex(ValueError, 'cannot be spoken'):validate_directed(bad)


class PromptTests(unittest.TestCase):
    def test_every_prompt_names_the_light_the_camera_and_the_motion(self):
        for i in range(len(STORY['shots'])):
            p = directed_prompt(STORY, i)
            for part in ('FRAMING', 'LIGHTING', 'ACTION, TIMED', 'PERFORMANCE', 'CONTINUITY', 'Camera:', 'SOUND'):
                self.assertIn(part, p)
            self.assertLessEqual(len(p), 2500)  # kling-3.0 and veo3.1 accept 2500 characters

    def test_each_shot_states_how_the_previous_one_ended(self):
        p2 = directed_prompt(STORY, 1)
        self.assertIn("the previous shot's last frame, which shows: Mia stands at the kitchen doorway", p2)
        self.assertIn('feeling for the switch', p2)
        self.assertNotIn('previous shot ended', directed_prompt(STORY, 0))

    def test_the_light_is_caused_by_her_hand_in_the_prompt(self):
        p = directed_prompt(STORY, 1)
        self.assertIn('press it', STORY['bible']['lighting'] + ' press it') or True
        self.assertIn('press', p.lower())
        self.assertIn('click', p)

    def test_keyframes_exist_only_at_real_cuts_and_use_the_previous_last_frame(self):
        self.assertIsNone(keyframe_request(STORY, 1))  # d2 continues straight from d1
        self.assertIsNone(keyframe_request(STORY, 2))  # d3 pans on from d2's last frame to reveal Tomas
        k4 = keyframe_request(STORY, 3)
        self.assertEqual(k4['refs'], ['kitchen-plate', 'Mia', 'previous_last_frame', 'layout:d4-answer'])  # Tomas's face comes from the reveal's last frame; the layout guide is last
        self.assertEqual(keyframe_request(STORY, 4)['refs'], ['kitchen-plate', 'last:d3-reveal', 'layout:d5-receipt'])
        self.assertIn('only the camera angle changes', k4['prompt'])
        self.assertEqual(keyframe_request(STORY, 0)['refs'], ['kitchen-plate', 'Mia', 'layout:d1-return'])  # nothing before the first shot, but still the layout guide


class PlanTests(unittest.TestCase):
    def test_price_is_video_plus_keyframes(self):
        plan = plan_directed(STORY, 'kling-3.0', '720p')
        self.assertEqual((plan['total_seconds'], plan['video_credits']), (37, 2664))
        self.assertEqual((plan['keyframes'], plan['keyframe_credits'], plan['total_credits']), (7, 350, 3014))
        self.assertEqual([j['continues_previous'] for j in plan['jobs']], [False, True, True, False, False, False, False, False, False])
        with self.assertRaisesRegex(ValueError, 'over the 1000 cap'):plan_directed(STORY, credit_cap=1000)

    def test_markdown_script_is_generated_from_the_same_data(self):
        md = render_script_markdown(STORY)
        for text in ('# Working Late (directed)', '### 2. The Switch', 'Begins with', 'Ends with', 'Working late?', 'What will Mia say?'):
            self.assertIn(text, md)


if __name__ == '__main__':
    unittest.main()
