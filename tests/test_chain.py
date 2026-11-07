"""Chained first frames (each shot starts from the real last frame of the one before) and motivated action (nobody idle, nobody just appears)."""
import copy
import json
import unittest

from magicdrama.audiofirst.blocking import camera_setup
from magicdrama.audiofirst.directed import check_activity, directed_prompt, first_frame_plan, keyframe_request, validate_directed
from tests.helpers import ROOT

STORY = json.loads((ROOT / 'examples' / 'cold-cycle' / 'directed-story.json').read_text(encoding='utf-8'))
PLAN = {p['id']: p for p in first_frame_plan(STORY)}


class ChainTests(unittest.TestCase):
    def test_the_first_shot_is_built_and_later_shots_name_their_source(self):
        self.assertEqual(PLAN['c1-wide']['mode'], 'build')
        self.assertTrue(all(p['mode'] in ('continue', 'resume', 'build') for p in PLAN.values()))

    def test_a_return_to_a_camera_angle_resumes_from_the_last_frame_of_that_angle(self):
        # Nora's angle: shot 4, then 8, 10, 11, 14; each comes back to where the story left her
        self.assertEqual((PLAN['c8-just-one']['mode'], PLAN['c8-just-one']['from_shot']), ('resume', 'c4-tokens-offer'))
        self.assertEqual(PLAN['c10-understands']['from_shot'], 'c8-just-one')
        self.assertEqual(PLAN['c14-wait']['from_shot'], 'c11-cold-slow')
        self.assertEqual(PLAN['c9-smells']['from_shot'], 'c5-thank')

    def test_a_new_angle_is_built_from_the_previous_shots_last_frame(self):
        self.assertEqual((PLAN['c5-thank']['mode'], PLAN['c5-thank']['from_shot']), ('build', 'c4-tokens-offer'))

    def test_resume_keyframes_put_the_earlier_real_frame_first_and_say_to_resume_from_it(self):
        k = keyframe_request(STORY, [s['id'] for s in STORY['shots']].index('c8-just-one'))
        self.assertEqual(k['refs'][0], 'last:c4-tokens-offer')
        self.assertIn('Resume exactly from it', k['prompt'])
        self.assertIn('layout:c8-just-one', k['refs'])

    def test_build_keyframes_use_the_previous_last_frame_first(self):
        k = keyframe_request(STORY, [s['id'] for s in STORY['shots']].index('c5-thank'))
        self.assertEqual(k['refs'][0], 'previous_last_frame')
        self.assertIn('real last frame of the previous shot', k['prompt'])

    def test_same_angle_same_people_continues_without_an_image_job(self):
        s = copy.deepcopy(STORY)
        s['plan']['shots']['c8-just-one'] = copy.deepcopy(s['plan']['shots']['c4-tokens-offer'])
        s['shots'].insert(4, copy.deepcopy(s['shots'][3]) | {'id': 'c4b'})
        s['plan']['shots']['c4b'] = copy.deepcopy(s['plan']['shots']['c4-tokens-offer'])
        plan = {p['id']: p for p in first_frame_plan(s)}
        self.assertEqual(plan['c4b']['mode'], 'continue')
        self.assertIsNone(keyframe_request(s, 4))

    def test_without_the_chain_rule_nothing_changes(self):
        s = copy.deepcopy(STORY)
        del s['rules']['chain']
        k = keyframe_request(s, [x['id'] for x in s['shots']].index('c8-just-one'))
        self.assertNotIn('Resume exactly', k['prompt'])

    def test_camera_setup_matches_for_the_same_angle(self):
        self.assertEqual(camera_setup(STORY['plan'], 'c4-tokens-offer'), camera_setup(STORY['plan'], 'c8-just-one'))
        self.assertNotEqual(camera_setup(STORY['plan'], 'c4-tokens-offer'), camera_setup(STORY['plan'], 'c5-thank'))


class MotivatedActionTests(unittest.TestCase):
    def test_the_cold_cycle_script_passes_the_activity_rules(self):
        self.assertEqual(check_activity(STORY), [])
        self.assertTrue(validate_directed(STORY))

    def test_a_person_with_nothing_to_do_is_caught(self):
        s = copy.deepcopy(STORY)
        s['shots'][3]['activity']['Nora'] = 'standing there'
        self.assertTrue(any('give them a task' in p for p in check_activity(s)))
        del s['shots'][3]['activity']['Nora']
        self.assertTrue(any('nothing to do' in p for p in check_activity(s)))

    def test_someone_who_appears_in_a_new_place_needs_a_reason_and_a_first_task(self):
        s = copy.deepcopy(STORY)
        del s['shots'][2]['arrival']
        self.assertTrue(any('c3-enter: Dev appears in a new place' in p for p in check_activity(s)))
        s = copy.deepcopy(STORY)
        s['shots'][2]['arrival']['Dev']['why'] = ''
        self.assertTrue(any('Dev appears in a new place' in p for p in check_activity(s)))
        s = copy.deepcopy(STORY)
        s['shots'][2]['arrival']['Dev']['then'] = 'waits'
        self.assertTrue(any('must be a task' in p for p in check_activity(s)))

    def test_the_prompt_says_what_each_person_is_doing_and_why_they_arrived(self):
        p = directed_prompt(STORY, 2)
        self.assertIn('WHAT EACH PERSON IS DOING (never idle)', p)
        self.assertIn('ARRIVAL: Dev comes from the front door', p)
        self.assertLessEqual(len(p), 2500)

    def test_every_prompt_still_fits_the_service_limit(self):
        for i in range(len(STORY['shots'])):
            self.assertLessEqual(len(directed_prompt(STORY, i)), 2500)

    def test_older_scripts_without_the_rule_are_not_affected(self):
        old = json.loads((ROOT / 'examples' / 'late-night' / 'directed-story.json').read_text(encoding='utf-8'))
        self.assertNotIn('rules', old)
        self.assertTrue(validate_directed(old))


if __name__ == '__main__':
    unittest.main()
