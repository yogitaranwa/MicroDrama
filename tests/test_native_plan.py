"""Native-audio planner: priced jobs, sound-design gates, chaining and the Uninvited Guest benchmark."""
import copy
import json
import unittest

from magicdrama.audiofirst.core import load_brief
from magicdrama.audiofirst.native_plan import tighten_seconds, build_frame_requests, compile_scene_take, compile_native_plan, compile_native_shots, snap_duration
from tests.helpers import ROOT

BENCH = json.loads((ROOT / 'examples' / 'uninvited-guest' / 'native-benchmark.json').read_text(encoding='utf-8'))['shots']
VOICE = 'quiet low female voice, soft neutral accent'


class BenchmarkTests(unittest.TestCase):
    def test_prices_the_whole_film_before_any_spend(self):
        plan = compile_native_shots(BENCH, 'veo3.1-lite', '720p')
        self.assertEqual(plan['total_credits'], sum(j['quote']['amount'] for j in plan['jobs']))
        self.assertEqual(plan['total_credits'], 4608)
        self.assertEqual(plan['paid_requests'], 0)
        self.assertEqual(plan['status'], 'compiled_not_rendered')
        self.assertTrue(plan['jobs'][0]['audio'])

    def test_credit_cap_is_enforced(self):
        with self.assertRaisesRegex(ValueError, 'over the 1000 cap'):compile_native_shots(BENCH, 'veo3.1-lite', '720p', credit_cap=1000)

    def test_every_impact_shot_carries_a_written_sound_effect(self):
        plan = compile_native_shots(BENCH, 'seedance-2.0-mini', '480p')
        by_id = {j['shot_id']: j['prompt'] for j in plan['jobs']}
        for sid, word in (('s06-impact', 'boom'), ('s08-collapse', 'stone crash'), ('s09-foot', 'thud')):
            self.assertIn(word, by_id[sid])
        self.assertTrue(all('No music' in p and 'SOUND' in p for p in by_id.values()))

    def test_removing_the_crash_sound_is_rejected(self):
        shots = copy.deepcopy(BENCH)
        next(s for s in shots if s['id'] == 's08-collapse')['sound']['effects'] = []
        with self.assertRaisesRegex(ValueError, 'no sound effect'):compile_native_shots(shots, 'veo3.1-lite', '720p')

    def test_dissolves_only_at_scene_changes(self):
        plan = compile_native_shots(BENCH, 'veo3.1-lite', '720p')
        self.assertEqual([j['overlap_frames'] for j in plan['jobs']], [0, 0, 0, 0, 8, 0, 0, 8, 0, 0, 8, 0, 0, 0])

    def test_speakers_needing_voice_checks_are_listed(self):
        plan = compile_native_shots(BENCH, 'veo3.1-lite', '720p')
        self.assertEqual(plan['voice_consistency_checks'], {'Hermione': ['s02-hermione', 's07-warning'], 'Ron': ['s03-ron', 's06-impact']})


class DurationAndChainingTests(unittest.TestCase):
    shot = {'id': 'a1', 'scene_id': 'sc', 'location': 'library', 'visual': 'A woman in a library.', 'seconds': 4,
            'sound': {'ambience': 'quiet room', 'dialogue': [{'speaker': 'Mara', 'voice': VOICE, 'line': 'You told me the door was locked.'}]}}

    def test_duration_snaps_up_to_what_the_model_accepts(self):
        self.assertEqual(snap_duration('veo3.1-lite', 5), 6)
        self.assertEqual(snap_duration('veo3.1-lite', 9), 16)
        self.assertEqual(snap_duration('kling-3.0', 5), 5)
        with self.assertRaises(ValueError):snap_duration('veo3.1-lite', 60)

    def test_long_lines_stretch_the_shot(self):
        shot = copy.deepcopy(self.shot)
        shot['seconds'] = 1
        shot['sound']['dialogue'][0]['line'] = 'You told me the door was locked and you told me you had the only key to it.'
        self.assertGreater(compile_native_shots([shot], 'kling-3.0', '720p')['jobs'][0]['seconds'], 6)

    def test_continuation_chains_from_previous_frame(self):
        second = {**self.shot, 'id': 'a2', 'continues_previous': True}
        plan = compile_native_shots([self.shot, second], 'veo3.1-lite', '720p')
        self.assertEqual(plan['jobs'][1]['first_frame'], {'source': 'previous_last_frame', 'shot_id': 'a1'})
        self.assertEqual(plan['jobs'][1]['depends_on'], ['native-a1'])
        self.assertEqual(plan['jobs'][0]['first_frame'], {'source': 'reference', 'image_id': 'frame-a1'})

    def test_continuation_across_scenes_or_at_start_is_rejected(self):
        with self.assertRaises(ValueError):compile_native_shots([{**self.shot, 'continues_previous': True}], 'veo3.1-lite', '720p')
        other = {**self.shot, 'id': 'a2', 'scene_id': 'other', 'continues_previous': True}
        with self.assertRaises(ValueError):compile_native_shots([self.shot, other], 'veo3.1-lite', '720p')

    def test_three_speakers_or_duplicate_ids_are_rejected(self):
        crowded = copy.deepcopy(self.shot)
        crowded['sound']['dialogue'] = [{'speaker': n, 'voice': VOICE, 'line': 'Hi.'} for n in 'ABC']
        with self.assertRaises(ValueError):compile_native_shots([crowded], 'veo3.1-lite', '720p')
        with self.assertRaises(ValueError):compile_native_shots([self.shot, self.shot], 'veo3.1-lite', '720p')


class SpeechRulesTests(unittest.TestCase):
    def test_dialogue_prompts_forbid_extra_vocal_noise_and_turned_backs(self):
        story = json.loads((ROOT / 'examples' / 'snow-street' / 'native-story.json').read_text(encoding='utf-8'))
        plan = compile_native_shots(story['shots'], 'kling-3.0', '720p', scenes=story['scenes'])
        talking = [j for j in plan['jobs'] if j['speakers']]
        self.assertTrue(talking and all('SPEECH RULES' in j['prompt'] and 'mouth visible' in j['prompt'] for j in talking))
        silent = next(j for j in plan['jobs'] if j['shot_id'] == 's06-kai')
        self.assertNotIn('SPEECH RULES', silent['prompt'])


class TightenTests(unittest.TestCase):
    def test_dialogue_shots_get_only_the_time_their_lines_need(self):
        story = json.loads((ROOT / 'examples' / 'snow-street' / 'native-story.json').read_text(encoding='utf-8'))
        tight = tighten_seconds(story['shots'])
        by = {s['id']: s['seconds'] for s in tight}
        self.assertEqual((by['s01-father'], by['s10-hello'], by['s12-connection']), (3, 5, 5))
        self.assertEqual(by['s06-kai'], 4)  # silent shot keeps its length
        plan = compile_native_shots(tight, 'kling-3.0', '720p', scenes=story['scenes'])
        self.assertEqual((plan['total_seconds'], plan['total_credits']), (47, 3384))
        self.assertGreater(compile_native_shots(story['shots'], 'veo3.1-lite', '720p', scenes=story['scenes'])['total_credits'], plan['total_credits'])


class SceneLockTests(unittest.TestCase):
    def story(self):
        return {'scenes': {'office': {'set': 'a wooden ticket office with a brass grille and a wall clock', 'plate': 'office-plate',
                                      'plate_prompt': 'Empty wooden ticket office, brass grille, wall clock, warm lamp.'}},
                'references': {'masters': {'mara-master': 'Mara portrait'},
                               'frames': {'f1': {'scene': 'office', 'refs': ['mara-master'], 'prompt': 'Mara at the counter.'},
                                          'f2': {'scene': 'office', 'refs': ['mara-master'], 'prompt': 'Mara close-up.'}}}}

    def test_plate_first_then_frames_reference_plate_and_previous_frame(self):
        reqs = build_frame_requests(self.story())
        self.assertEqual([r['id'] for r in reqs], ['office-plate', 'f1', 'f2'])
        self.assertEqual(reqs[1]['refs'], ['office-plate', 'mara-master'])
        self.assertEqual(reqs[2]['refs'], ['office-plate', 'mara-master', 'f1'])
        self.assertTrue(all('SET LOCK' in r['prompt'] and 'brass grille' in r['prompt'] for r in reqs[1:]))
        self.assertFalse(reqs[0]['edit'])

    def test_previous_frame_is_not_passed_when_no_character_carries_over(self):
        story = self.story()
        story['references']['masters']['jonas-master'] = 'Jonas portrait'
        story['references']['frames']['f3'] = {'scene': 'office', 'refs': ['jonas-master'], 'prompt': 'Jonas close-up.'}
        reqs = {r['id']: r['refs'] for r in build_frame_requests(story)}
        self.assertEqual(reqs['f3'], ['office-plate', 'jonas-master'])

    def test_unknown_references_or_scenes_are_rejected(self):
        bad = self.story();bad['references']['frames']['f1']['refs'] = ['nobody']
        with self.assertRaises(ValueError):build_frame_requests(bad)
        bad = self.story();bad['references']['frames']['f1']['scene'] = 'nowhere'
        with self.assertRaises(ValueError):build_frame_requests(bad)

    def test_every_shot_of_a_scene_carries_the_identical_set_line(self):
        shots = [{'id': f'a{i}', 'scene_id': 'office', 'location': 'ticket-office', 'visual': f'Beat {i}.', 'seconds': 4,
                  'sound': {'ambience': 'rain'}} for i in range(3)]
        plan = compile_native_shots(shots, 'veo3.1-lite', '720p', scenes=self.story()['scenes'])
        lines = {j['prompt'].split('Beat')[0] for j in plan['jobs']}
        self.assertEqual(len(lines), 1)
        self.assertIn('wooden ticket office', lines.pop())
        with self.assertRaises(ValueError):compile_native_shots([{**shots[0], 'scene_id': 'lobby'}], 'veo3.1-lite', '720p', scenes=self.story()['scenes'])


class SceneTakeTests(unittest.TestCase):
    voices = {'Lyra': 'bright teenage girl, quick and clear', 'Aldric': 'deep cold slow man, quiet menace'}
    scene = {'set': 'a snowy cobblestone street with a brass kettle sign'}

    def beat(self, i, seconds, speaker, line):
        return {'id': f'b{i}', 'seconds': seconds, 'visual': f'Beat {i} visual.', 'sound': {'ambience': 'soft wind', 'dialogue': [{'speaker': speaker, 'voice': self.voices[speaker], 'line': line}]}}

    def test_beats_become_one_priced_generation_with_a_voice_bible(self):
        shots = [self.beat(0, 3, 'Lyra', 'Father!'), self.beat(1, 6, 'Aldric', 'In the snow. Coat open.'), self.beat(2, 4, 'Lyra', 'Impossible!'), self.beat(3, 3, 'Aldric', 'Is that so?')]
        take = compile_scene_take(shots, self.voices, self.scene)
        self.assertEqual((take['seconds'], take['quote']['amount']), (16, 1152))
        self.assertIn('0-3s:', take['prompt']);self.assertIn('13-16s:', take['prompt'])
        self.assertEqual(take['prompt'].count('VOICES (identical'), 1)
        self.assertIn('deep cold slow man', take['prompt'])

    def test_wasted_time_or_overlong_lines_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'no time is wasted'):compile_scene_take([self.beat(0, 3, 'Lyra', 'Hi.')], self.voices, self.scene)
        long = ' '.join(['word'] * 30)
        with self.assertRaisesRegex(ValueError, 'needs'):compile_scene_take([self.beat(0, 4, 'Lyra', long)] * 4, self.voices, self.scene)
        unvoiced = {'id': 'b9', 'seconds': 16, 'visual': 'A boy waves.', 'sound': {'dialogue': [{'speaker': 'Kai', 'voice': 'warm boy', 'line': 'Hi!'}]}}
        with self.assertRaisesRegex(ValueError, 'No written voice for Kai'):compile_scene_take([unvoiced], self.voices, self.scene)

    def test_cap_is_enforced(self):
        shots = [self.beat(0, 4, 'Lyra', 'Father!')] * 4
        with self.assertRaisesRegex(ValueError, 'over the 500 cap'):compile_scene_take(shots, self.voices, self.scene, credit_cap=500)


class StoryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.brief = load_brief(str(ROOT / 'examples' / 'pilot' / 'brief.json'))
        self.episode = json.loads((ROOT / 'examples' / 'pilot' / 'story.json').read_text(encoding='utf-8'))['episodes'][0]

    def test_voice_descriptions_are_required(self):
        with self.assertRaisesRegex(ValueError, 'No written voice description'):compile_native_plan(self.brief, self.episode)

    def test_pilot_story_compiles_with_written_voices(self):
        voices = {'mira': 'firm, quiet adult woman, warm low register', 'dev': 'guarded adult man, soft and tired'}
        plan = compile_native_plan(self.brief, self.episode, voices=voices, model='kling-3.0')
        self.assertEqual(len(plan['jobs']), len(self.episode['shots']))
        self.assertIn('Mira', plan['jobs'][0]['prompt'])
        self.assertIn(voices['mira'], plan['jobs'][0]['prompt'])


if __name__ == '__main__':
    unittest.main()
