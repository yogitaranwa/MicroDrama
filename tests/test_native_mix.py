"""Native-audio assembly on synthetic media: planning, sound-design gates, seams and dead air."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from magicdrama.audiofirst import native_mix as nm
from magicdrama.audiofirst.core import digest

try:
    nm.ffmpeg_exe()
    HAVE_FFMPEG = True
except RuntimeError:
    HAVE_FFMPEG = False


def make_clip(path, seconds=3, audio='sine', freq=440, volume=0.3):
    src = {'sine': f'sine=frequency={freq}:duration={seconds}', 'silent': f'anullsrc=r=48000:cl=stereo:d={seconds}'}.get(audio)
    args = ['-f', 'lavfi', '-i', f'testsrc=size=320x568:rate=24:duration={seconds}']
    if src:args += ['-f', 'lavfi', '-i', src, '-af', f'volume={volume}', '-c:a', 'aac']
    nm._run(args + ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-shortest', path])
    return {'path': str(path), 'sha256': digest(path), 'frames': seconds * 24, 'pixel_checked': True}


class PlanningTests(unittest.TestCase):
    def test_overlap_shortens_total(self):
        t = nm.plan_timeline([{'frames': 96}, {'frames': 96, 'overlap_frames': 6}, {'frames': 96, 'overlap_frames': 6}])
        self.assertEqual(t['total_frames'], 276)
        self.assertEqual([r['start_frame'] for r in t['shots']], [0, 90, 180])

    def test_rejects_bad_overlaps(self):
        with self.assertRaises(ValueError):nm.plan_timeline([{'frames': 96, 'overlap_frames': 4}])
        with self.assertRaises(ValueError):nm.plan_timeline([{'frames': 8}, {'frames': 8, 'overlap_frames': 6}, {'frames': 8, 'overlap_frames': 6}])
        with self.assertRaises(ValueError):nm.plan_timeline([])

    def test_quotes_match_published_rates(self):
        self.assertEqual(nm.quote_native_video('veo3.1-lite', '720p', 4)['amount'], 288)
        self.assertEqual(nm.quote_native_video('seedance-2.0-mini', '480p', 4)['amount'], 192)
        self.assertFalse(nm.quote_native_video('kling-3.0', '720p', 4)['derived'])
        self.assertFalse(nm.quote_native_video('veo3.1-lite', '720p', 4)['derived'])
        with self.assertRaises(ValueError):nm.quote_native_video('unknown', '720p', 4)


class SoundDesignTests(unittest.TestCase):
    shot = {'id': 's8', 'seconds': 4, 'visual': 'The entrance masonry bursts inward and the lintel collapses.'}

    def test_impact_without_effect_is_rejected(self):
        with self.assertRaises(ValueError):nm.require_sound_design(self.shot)
        with self.assertRaises(ValueError):nm.require_sound_design({**self.shot, 'sound': {'effects': ['  ']}})

    def test_impact_with_effect_passes_and_prompt_asks_for_it(self):
        shot = {**self.shot, 'sound': {'ambience': 'echoing stone hall', 'effects': ['huge stone crash with scattering rubble']}}
        prompt = nm.native_prompt(shot)
        self.assertIn('huge stone crash', prompt)
        self.assertIn('echoing stone hall', prompt)
        self.assertIn('No music', prompt)

    def test_dialogue_needs_voice_description_and_fitting_length(self):
        base = {'id': 'd', 'seconds': 4, 'visual': 'A woman in a library.',
                'sound': {'dialogue': {'speaker': 'Mara', 'voice': '', 'line': 'You told me the door was locked.'}}}
        with self.assertRaises(ValueError):nm.require_sound_design(base)
        base['sound']['dialogue']['voice'] = 'quiet low female voice, soft neutral accent'
        self.assertIn('says exactly once', nm.native_prompt(base))
        base['sound']['dialogue']['line'] = ' '.join(['word'] * 30)
        with self.assertRaises(ValueError):nm.require_sound_design(base)


@unittest.skipUnless(HAVE_FFMPEG, 'ffmpeg unavailable')
class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_native_audio_is_kept_and_seams_have_sound(self):
        shots = [make_clip(self.tmp / 'a.mp4', freq=330), make_clip(self.tmp / 'b.mp4', freq=550, volume=0.05),
                 make_clip(self.tmp / 'c.mp4', freq=440)]
        for s, ov in zip(shots, (0, 6, 6)):s['overlap_frames'] = ov
        result = nm.assemble_native_episode({'shots': shots}, self.tmp / 'out')
        self.assertAlmostEqual(result['duration'], (216 - 12) / 24)
        self.assertEqual(result['mechanical']['defects'], [])
        self.assertGreater(result['gains_db'][1], result['gains_db'][0])  # the quiet clip is brought up, not left behind
        cuts = result['mechanical']['cut_audio']['cuts']
        self.assertEqual([r['at_seconds'] for r in cuts], [2.75, 5.5])
        self.assertEqual([r['overlap_frames'] for r in cuts], [6, 6])
        self.assertEqual([r['right_shot_index'] for r in cuts], [1, 2])

    def test_video_has_exactly_the_planned_frames_across_many_joins(self):
        """Regression: joining with the fps filter lost ~2 frames per join and pushed later dissolves past the end."""
        shots = [make_clip(self.tmp / f'{n}.mp4', freq=300 + 40 * n) for n in range(6)]
        for s, ov in zip(shots, (0, 0, 8, 0, 8, 0)):s['overlap_frames'] = ov
        result = nm.assemble_native_episode({'shots': shots}, self.tmp / 'out')
        self.assertEqual(nm.frame_count(result['path']), result['frames'])
        self.assertEqual(result['frames'], 6 * 72 - 16)

    def test_report_flags_a_film_whose_video_is_shorter_than_planned(self):
        clip = make_clip(self.tmp / 'a.mp4')
        report = nm.native_report(clip['path'], expected_frames=500)
        self.assertIn('video_frames_missing', [d['type'] for d in report['defects']])

    def test_clip_without_audio_is_rejected_not_dubbed(self):
        clip = make_clip(self.tmp / 'mute.mp4', audio=None)
        with self.assertRaisesRegex(ValueError, 'no audio stream'):nm.assemble_native_episode({'shots': [clip]}, self.tmp / 'out')

    def test_dead_air_fails_closed(self):
        clip = make_clip(self.tmp / 'silent.mp4', audio='silent')
        with self.assertRaisesRegex(ValueError, 'dead_air'):nm.assemble_native_episode({'shots': [clip]}, self.tmp / 'out')

    def test_ambience_bed_fills_a_silent_cut(self):
        clip = make_clip(self.tmp / 'silent.mp4', audio='silent')
        bed = make_clip(self.tmp / 'bed.mp4', seconds=2, freq=120)
        bed_wav = self.tmp / 'bed.wav'
        nm._run(['-i', bed['path'], '-vn', bed_wav])
        result = nm.assemble_native_episode({'shots': [clip], 'beds': [{'path': str(bed_wav), 'sha256': digest(bed_wav), 'gain': .4}]}, self.tmp / 'out')
        self.assertEqual(result['mechanical']['defects'], [])

    def test_landscape_output_and_pitch_shift_are_supported(self):
        a, b = make_clip(self.tmp / 'a.mp4', freq=200), make_clip(self.tmp / 'b.mp4', freq=300)
        b['pitch_semitones'] = -2.0
        result = nm.assemble_native_episode({'shots': [a, b]}, self.tmp / 'out', size=(640, 360))
        self.assertEqual(nm.frame_count(result['path']), 144)
        with self.assertRaises(ValueError):nm.assemble_native_episode({'shots': [{**a, 'pitch_semitones': 9}]}, self.tmp / 'out2')
        with self.assertRaises(ValueError):nm.assemble_native_episode({'shots': [a]}, self.tmp / 'out3', size=(500, 500))

    def test_room_tone_comes_from_the_quietest_stretch_and_refuses_silence(self):
        quiet = make_clip(self.tmp / 'q.mp4', volume=0.01)
        tone = nm.extract_room_tone([quiet['path']], self.tmp / 'tone.wav')
        self.assertTrue(Path(tone['path']).is_file())
        with self.assertRaisesRegex(ValueError, 'digital silence'):nm.extract_room_tone([make_clip(self.tmp / 's.mp4', audio='silent')['path']], self.tmp / 'none.wav')

    def test_captions_follow_measured_speech_and_keep_every_frame(self):
        speech = make_clip(self.tmp / 'say.mp4', seconds=3, freq=300, volume=0.5)
        result = nm.assemble_native_episode({'shots': [speech]}, self.tmp / 'out')
        cues = nm.caption_cues(result['timeline'], [speech], {0: [{'text': 'You told me the door was locked.'}]})
        self.assertEqual(len(cues), 1)
        self.assertGreaterEqual(cues[0]['start'], 0)
        self.assertLessEqual(cues[0]['end'], 3.05)
        burned = nm.burn_captions(result['path'], cues, self.tmp / 'out' / 'captioned.mp4', (540, 960))
        self.assertEqual(nm.frame_count(burned['path']), nm.frame_count(result['path']))
        self.assertIn('door was locked', Path(burned['ass']).read_text(encoding='utf-8').replace(chr(92) + 'N', ' '))

    def test_speech_span_finds_a_burst_above_the_noise_floor_not_the_whole_clip(self):
        import numpy as np, wave
        sr = 16000;t = np.arange(sr) / sr;rng = np.random.default_rng(1)
        noise = lambda: 0.02 * rng.standard_normal(sr)
        burst = 0.4 * np.sin(2 * np.pi * 180 * t) + noise()
        x = np.r_[noise(), burst, noise()]
        wav = self.tmp / 'burst.wav'
        with wave.open(str(wav), 'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
        first, last = nm.speech_span(wav, 0, 3.0)
        self.assertAlmostEqual(first, 1.0, delta=0.12)
        self.assertAlmostEqual(last, 2.0, delta=0.12)

    def test_wav_saved_as_mp3_is_converted_and_real_mp3_is_left_alone(self):
        wav = self.tmp / 'voice.mp3'
        nm._run(['-f', 'lavfi', '-i', 'sine=frequency=200:duration=1', '-c:a', 'pcm_s16le', '-f', 'wav', wav])
        self.assertEqual(wav.read_bytes()[:4], b'RIFF')
        fixed = nm.ensure_mp3(wav)
        self.assertNotEqual(fixed, wav)
        self.assertTrue(fixed.read_bytes()[:3] == b'ID3' or fixed.read_bytes()[0] == 0xFF)
        self.assertEqual(nm.ensure_mp3(fixed), fixed)

    def test_extract_last_frame_for_shot_chaining(self):
        clip = make_clip(self.tmp / 'a.mp4')
        frame = nm.extract_frame(clip['path'], self.tmp / 'last.png')
        self.assertTrue(Path(frame['path']).stat().st_size > 1000)


if __name__ == '__main__':
    unittest.main()
