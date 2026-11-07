"""Voice-consistency checks on synthetic harmonic 'voices' with known pitch."""
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from magicdrama.audiofirst import native_mix as nm
from magicdrama.audiofirst.voice_check import consistency_report, plan_pitch_match, semitones, speech_profile

try:
    nm.ffmpeg_exe()
    HAVE_FFMPEG = True
except RuntimeError:
    HAVE_FFMPEG = False
SR = 16000


def voice(path, f0, seconds=2.0, noise=0.0, seed=0):
    t = np.arange(int(SR * seconds)) / SR
    x = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 12))
    x = x * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t) ** 2)  # syllable-like envelope
    x = x / np.abs(x).max() * 0.5 + noise * np.random.default_rng(seed).standard_normal(len(t))
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    return str(path)


@unittest.skipUnless(HAVE_FFMPEG, 'ffmpeg unavailable')
class VoiceCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def profile(self, name, f0, **kw):
        return speech_profile(voice(self.tmp / (name + '.wav'), f0, **kw))

    def test_measures_known_pitch(self):
        self.assertAlmostEqual(self.profile('a', 140)['median_f0'], 140, delta=6)
        self.assertAlmostEqual(self.profile('b', 220)['median_f0'], 220, delta=9)

    def test_same_voice_is_consistent_and_a_shifted_one_drifts(self):
        steady = {'Mara': {'s1': self.profile('m1', 210), 's2': self.profile('m2', 214)}}
        self.assertEqual(consistency_report(steady)['speakers']['Mara']['status'], 'consistent_by_signal')
        drifting = {'Mara': {'s1': self.profile('m3', 150), 's2': self.profile('m4', 235)}}
        report = consistency_report(drifting)
        self.assertEqual(report['speakers']['Mara']['status'], 'drifts')
        self.assertEqual(report['defects'][0]['type'], 'voice_drift')

    def test_two_speakers_are_told_apart_by_pitch_gap(self):
        profiles = {'Mara': {'a': self.profile('p1', 230), 'b': self.profile('p2', 232)},
                    'Jonas': {'a': self.profile('p3', 120), 'b': self.profile('p4', 122)}}
        gap = consistency_report(profiles)['speakers']['_between_speakers']['Mara vs Jonas']
        self.assertTrue(gap['distinct_by_pitch'])
        self.assertAlmostEqual(gap['pitch_gap_semitones'], semitones(231, 121), delta=0.8)

    def test_noise_dominated_audio_is_not_trusted(self):
        with self.assertRaises(ValueError):self.profile('n', 150, noise=0.5)

    def test_pitch_match_shifts_small_gaps_and_flags_large_ones(self):
        profiles = {'Jonas': {'a': self.profile('j1', 130), 'b': self.profile('j2', 146), 'c': self.profile('j3', 135), 'd': self.profile('j4', 230)}}
        plan = plan_pitch_match(profiles, max_shift_st=3.0)
        self.assertIn('b', plan['shifts'])
        self.assertLess(plan['shifts']['b'], 0)  # too high -> shift down
        self.assertEqual([r['shot'] for r in plan['regenerate']], ['d'])


if __name__ == '__main__':
    unittest.main()
