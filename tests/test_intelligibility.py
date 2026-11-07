"""Script-vs-speech scoring and ASR-timed captions, on hand-made word lists (no model needed)."""
import copy
import json
import unittest

from magicdrama.audiofirst.intelligibility import caption_cues_from_words, word_error_rate
from magicdrama.audiofirst.native_plan import compile_native_shots

VOICE = 'quiet low female voice, soft neutral accent'


class WerTests(unittest.TestCase):
    def test_identical_text_ignores_case_and_punctuation(self):
        self.assertEqual(word_error_rate("Really, it's only training!", "really its only training"), 0.25)  # "its" is a different word
        self.assertEqual(word_error_rate('Father! Really, it is.', 'father really it is'), 0.0)

    def test_missing_wrong_and_extra_words_all_count(self):
        self.assertEqual(word_error_rate('one two three four', 'one two three'), 0.25)
        self.assertEqual(word_error_rate('one two three four', 'one two banana four'), 0.25)
        self.assertEqual(word_error_rate('one two', 'one two three four'), 1.0)
        self.assertEqual(word_error_rate('', ''), 0.0)


class CaptionCueTests(unittest.TestCase):
    words = [{'start': 0.0, 'end': 0.4, 'text': 'Father.'}, {'start': 2.8, 'end': 3.1, 'text': 'Really,'}, {'start': 3.2, 'end': 3.5, 'text': "it's"},
             {'start': 4.0, 'end': 4.2, 'text': 'only'}, {'start': 4.3, 'end': 5.0, 'text': 'training.'}]

    def test_cues_use_script_text_and_the_recognisers_word_times(self):
        cues = caption_cues_from_words(self.words, ['Father!', "Really, it's only training!"])
        self.assertEqual([c['text'] for c in cues], ['Father!', "Really, it's only training!"])
        self.assertEqual((cues[1]['start'], cues[1]['end']), (2.8, 5.25))
        self.assertLess(cues[0]['end'], cues[1]['start'])

    def test_lines_without_words_are_skipped_not_invented(self):
        self.assertEqual(len(caption_cues_from_words(self.words[:1], ['Father!', 'Never heard.'])), 1)


class OneSpeakerPerShotTests(unittest.TestCase):
    def shot(self, *speakers, offscreen=()):
        return {'id': 'a1', 'scene_id': 'sc', 'location': 'street', 'visual': 'Two people talk.', 'seconds': 6,
                'sound': {'ambience': 'wind', 'dialogue': [{'speaker': n, 'voice': VOICE, 'line': 'Hello there.', 'offscreen': n in offscreen} for n in speakers]}}

    def test_two_on_screen_speakers_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'one shot per speaker'):compile_native_shots([self.shot('A', 'B')], 'veo3.1-lite', '720p')

    def test_an_off_screen_second_speaker_is_fine(self):
        plan = compile_native_shots([self.shot('A', 'B', offscreen=('B',))], 'veo3.1-lite', '720p')
        self.assertEqual(plan['jobs'][0]['speakers'], ['A', 'B'])

    def test_explicit_override_is_possible_and_visible(self):
        shot = {**self.shot('A', 'B'), 'allow_multi_speaker': True}
        self.assertEqual(len(compile_native_shots([shot], 'veo3.1-lite', '720p')['jobs']), 1)

    def test_the_anime_story_and_benchmarks_obey_the_rule(self):
        for name in ('snow-street', 'last-ferry', 'uninvited-guest'):
            path = f'examples/{name}/' + ('native-benchmark.json' if name == 'uninvited-guest' else 'native-story.json')
            story = json.load(open(path, encoding='utf-8'))
            compile_native_shots(copy.deepcopy(story['shots']), 'veo3.1-lite', '720p', scenes=story.get('scenes'))


if __name__ == '__main__':
    unittest.main()
