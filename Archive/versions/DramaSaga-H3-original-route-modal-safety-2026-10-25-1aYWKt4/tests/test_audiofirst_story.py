import copy
import tempfile
from pathlib import Path
import unittest

from tests.test_audiofirst import brief
from magicdrama.audiofirst.story import validate_story
from magicdrama.audiofirst.planning import reference_plan, threejs_request
from magicdrama.audiofirst.core import schedule_shots, assembly_commands


def story():
    episodes = []
    for n in range(10):
        lid = 'line' + str(n)
        episodes.append({'id': 'ep' + str(n), 'title': 'A letter', 'draft_seconds': 90,
                         'setup': 'A letter arrives', 'turn': 'It is dated tomorrow', 'cliffhanger': 'The door opens',
                         'lines': [{'id': lid, 'speaker': 'lead', 'text': 'Who sent this?', 'performance': 'quiet suspicion'}],
                         'shots': [{'id': 'shot' + str(n), 'line_ids': [lid], 'location': 'office',
                                    'location_description': 'A cramped postal office', 'visible_characters': ['lead'],
                                    'camera': 'medium', 'action': 'opens letter', 'wardrobe': 'navy coat',
                                    'props': ['letter']} ]})
    return {'series_id': 'sample', 'season': 1, 'episodes': episodes}


class StoryTests(unittest.TestCase):
    def test_valid_structure(self):
        self.assertEqual(validate_story(brief(), story())['draft_seconds'], 900)

    def test_bad_coverage(self):
        s = story(); s['episodes'][0]['shots'][0]['line_ids'] = ['invented']
        with self.assertRaises(ValueError): validate_story(brief(), s)

    def test_wrong_season(self):
        s = story(); s['season'] = 2
        with self.assertRaises(ValueError): validate_story(brief(), s)

    def test_long_episode(self):
        s = story(); s['episodes'][0]['draft_seconds'] = 181
        with self.assertRaises(ValueError): validate_story(brief(), s)

    def test_bad_total(self):
        s = story(); s['episodes'][0]['draft_seconds'] = 1
        with self.assertRaises(ValueError): validate_story(brief(), s)

    def test_no_arbitrary_line_cap(self):
        s = story(); s['episodes'][0]['lines'][0]['text'] = 'word ' * 80
        validate_story(brief(), s)

    def test_reference_plan(self):
        p = reference_plan(brief(), story()['episodes'])
        self.assertEqual(sum(a['kind'] == 'shot_frame' for a in p['assets']), 10)
        self.assertEqual(sum(a['kind'] == 'location' for a in p['assets']), 1)
        self.assertEqual(p['paid_requests'], 0)

    def test_duplicate_shot_refs(self):
        s = story(); s['episodes'][1]['shots'][0]['id'] = 'shot0'
        with self.assertRaises(ValueError): reference_plan(brief(), s['episodes'])

    def test_threejs_rejects_fake_image(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'a.png'; p.write_text('not an image')
            with self.assertRaises(ValueError): threejs_request('desk', p, 'prop', temp)

    def test_threejs_handoff_not_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'a.png'; p.write_bytes(b'\x89PNG\r\n\x1a\n')
            result = threejs_request('desk', p, 'prop', temp)
            self.assertEqual(result['paid_requests'], 0)
            self.assertEqual(result['status'], 'handoff_only_not_reconstructed')

    def test_shot_coverage(self):
        track = {'fps': 24, 'frames': 48, 'seconds': 2, 'lines': [{'id': 'a', 'start_frame': 0, 'end_frame': 24}, {'id': 'b', 'start_frame': 29, 'end_frame': 48}]}
        fields = {'location': 'office', 'visible_characters': ['lead'], 'wardrobe': 'coat', 'action': 'reads', 'props': ['letter']}
        shots = schedule_shots(track, [{'id': 'one', 'line_ids': ['a'], **fields}, {'id': 'two', 'line_ids': ['b'], **fields}])
        self.assertEqual(shots[1]['start_frame'], 24)
        commands = assembly_commands(track, shots, ['a.mp4', 'b.mp4'], 'master.wav', 'final.mp4')
        self.assertIn('-an', commands['trim_commands'][0])
        self.assertEqual(commands['mux_command'].count('-i'), 2)

    def test_output_path_attack(self):
        with self.assertRaises(ValueError): assembly_commands({'fps': 24}, [{'id': '../evil'}], ['a.mp4'], 'master.wav', 'final.mp4')

class ApprovalBindingTests(unittest.TestCase):
    def test_text_change_invalidates_review(self):
        from tests.test_audiofirst import AudioFirstTests
        from magicdrama.audiofirst.core import timeline
        case = AudioFirstTests(); case.setUp()
        try:
            case.line['text'] = 'Different words'
            with self.assertRaises(ValueError): timeline([case.line], ['lead'])
        finally:
            case.doCleanups()

    def test_speaker_change_invalidates_review(self):
        from tests.test_audiofirst import AudioFirstTests
        from magicdrama.audiofirst.core import timeline
        case = AudioFirstTests(); case.setUp()
        try:
            case.line['speaker'] = 'narrator'
            with self.assertRaises(ValueError): timeline([case.line], ['lead'])
        finally:
            case.doCleanups()
