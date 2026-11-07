"""Edit-feel measurements, free editor effects, story lint and the new price helpers, on synthetic media."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from magicdrama.audiofirst import native_mix as nm
from magicdrama.audiofirst.core import digest
from magicdrama.audiofirst.edit_profile import compare_profiles, cut_audio_levels, cut_audio_report, detect_cuts, edit_profile
from magicdrama.audiofirst.native_plan import compile_native_shots, lint_story
from tests.helpers import ROOT

try:
    nm.ffmpeg_exe()
    HAVE_FFMPEG = True
except RuntimeError:
    HAVE_FFMPEG = False


def grid_clip(path, seconds=3, volume=0.3):
    """A perfectly still picture (grid) with a steady tone: any motion in the result is added by the edit."""
    nm._run(['-f', 'lavfi', '-i', f'color=c=gray:s=320x568:r=24:d={seconds},drawgrid=w=40:h=40:t=2:c=white', '-f', 'lavfi', '-i', f'sine=frequency=300:duration={seconds}',
             '-af', f'volume={volume}', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', path])
    return {'path': str(path), 'sha256': digest(path), 'frames': seconds * 24, 'pixel_checked': True}


class PriceHelperTests(unittest.TestCase):
    def test_rates_match_the_published_table(self):
        self.assertEqual(nm.quote_audio_to_video(4, '720p')['amount'], 192)
        self.assertEqual(nm.quote_audio_to_video(4, '480p')['amount'], 96)
        self.assertEqual(nm.quote_audio_to_video(2.3, '720p')['amount'], 112)  # billed per whole frame: seen on a real job
        self.assertEqual(nm.quote_voice('x' * 101)['amount'], 11)
        self.assertEqual(nm.plan_music(47, 'warm winter orchestral score')['quote']['amount'], 47)
        self.assertEqual(nm.plan_music(5, 'tiny')['quote']['amount'], 15)  # the service takes 15 s minimum
        self.assertTrue(nm.plan_music(30, 'x')['body']['style']['instrumental'])

    def test_bad_inputs_are_rejected(self):
        with self.assertRaises(ValueError):nm.quote_audio_to_video(4, '4k')
        with self.assertRaises(ValueError):nm.quote_voice('')
        with self.assertRaises(ValueError):nm.quote_voice('x' * 1001)
        with self.assertRaises(ValueError):nm.plan_music(400, 'too long')
        with self.assertRaises(ValueError):nm.plan_music(30, '   ')


class CutAudioTests(unittest.TestCase):
    def test_known_jump_signed_levels_silence_and_edge_skips(self):
        audio = np.r_[np.full(16000, .1), np.full(16000, .01), np.zeros(16000)]
        report = cut_audio_levels(audio, [0, .1, 1, 2, 2.9, 3])
        self.assertEqual([r['status'] for r in report['cuts']], ['skipped', 'skipped', 'measured', 'measured', 'skipped', 'skipped'])
        row = report['cuts'][2]
        self.assertAlmostEqual(row['before_dbfs'], -20, delta=.1)
        self.assertAlmostEqual(row['after_dbfs'], -40, delta=.1)
        self.assertEqual(row['delta_db'], -20)
        self.assertEqual(row['jump_db'], 20)
        self.assertEqual(report['review_count'], 2)
        self.assertTrue(np.isfinite(report['cuts'][3]['after_dbfs']))
        self.assertEqual(cut_audio_levels(audio[::-1], [2])['cuts'][0]['delta_db'], 20)

    def test_equal_power_stereo_does_not_cancel_and_single_sample_click_is_not_level_jump(self):
        t = np.arange(32000) / 16000
        mono = .1 * np.sin(2 * np.pi * 300 * t)
        stereo = np.column_stack((mono, -mono))
        report = cut_audio_levels(stereo, [1])
        self.assertAlmostEqual(report['cuts'][0]['before_dbfs'], -23, delta=.1)
        self.assertEqual(report['review_count'], 0)
        mono[16000] = 1
        self.assertEqual(cut_audio_levels(mono, [1])['review_count'], 0)
        self.assertEqual(cut_audio_levels(np.zeros(32000), [1])['review_count'], 0)

    def test_no_cuts_and_invalid_configuration(self):
        self.assertEqual(cut_audio_levels(np.zeros(10), [])['cuts'], [])
        for kwargs in ({'warning_db': 0}, {'window_seconds': 0}, {'sample_rate': 0}):
            with self.assertRaises(ValueError):cut_audio_levels(np.zeros(10), [], **kwargs)
        with self.assertRaises(ValueError):cut_audio_levels(np.zeros(10), [float('nan')])


class LintTests(unittest.TestCase):
    def shot(self, i, camera='Close-up, locked.', talking=True, seconds=4, **extra):
        return {'id': f's{i}', 'seconds': seconds, 'camera': camera, 'sound': {'dialogue': [{'speaker': 'A', 'voice': 'v', 'line': 'Hi.'}] if talking else {}}, **extra}

    def test_a_stiff_all_talking_story_is_flagged(self):
        text = ' '.join(lint_story([self.shot(i) for i in range(6)]))
        for phrase in ('locked/static camera', 'someone talking', 'without dialogue', 'same camera setup', 'zoom'):
            self.assertIn(phrase, text)

    def test_a_lively_story_passes(self):
        shots = [self.shot(0, 'Slow push-in.', zoom=[1.0, 1.1]), self.shot(1, 'Handheld sway.', talking=False), self.shot(2, 'Wide pan.', talking=False),
                 self.shot(3, 'Close-up, pull-out.'), self.shot(4, 'Low angle.', flash_frames=3)]
        self.assertEqual(lint_story(shots), [])

    def test_our_anime_story_is_known_to_be_too_stiff(self):
        story = json.loads((ROOT / 'examples' / 'snow-street' / 'native-story.json').read_text(encoding='utf-8'))
        plan = compile_native_shots(story['shots'], 'kling-3.0', '720p', scenes=story['scenes'])
        self.assertTrue(plan['lint'])  # the measured reason the first film did not feel like the reference


@unittest.skipUnless(HAVE_FFMPEG, 'ffmpeg unavailable')
class EditEffectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_zoom_adds_motion_to_a_still_picture_and_keeps_every_frame(self):
        still = grid_clip(self.tmp / 'a.mp4')
        plain = nm.assemble_native_episode({'shots': [still]}, self.tmp / 'plain')
        moving = nm.assemble_native_episode({'shots': [{**still, 'zoom': [1.0, 1.2]}]}, self.tmp / 'zoomed')
        self.assertEqual(nm.frame_count(moving['path']), nm.frame_count(plain['path']))
        self.assertGreater(edit_profile(moving['path'], [])['motion_mean'], edit_profile(plain['path'], [])['motion_mean'] + 0.3)

    def test_grade_cools_a_warm_shot_to_match_its_neighbour_and_bad_grades_are_rejected(self):
        import subprocess, numpy as np
        still = grid_clip(self.tmp / 'warm.mp4')
        nm._run(['-f', 'lavfi', '-i', 'color=c=0xC89040:s=320x568:r=24:d=3', '-f', 'lavfi', '-i', 'sine=frequency=300:duration=3', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', self.tmp / 'amber.mp4'])
        amber = {'path': str(self.tmp / 'amber.mp4'), 'sha256': digest(self.tmp / 'amber.mp4'), 'frames': 72, 'pixel_checked': True}

        def red_over_blue(path):
            raw = subprocess.run([nm.ffmpeg_exe(), '-v', 'error', '-i', path, '-frames:v', '1', '-vf', 'scale=32:32', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
            a = np.frombuffer(raw, np.uint8).reshape(32, 32, 3).astype(float)
            return a[..., 0].mean() / a[..., 2].mean()
        plain = nm.assemble_native_episode({'shots': [amber]}, self.tmp / 'amber-plain')
        cooled = nm.assemble_native_episode({'shots': [{**amber, 'grade': {'r': 0.7, 'g': 0.9, 'b': 1.4}}]}, self.tmp / 'amber-cooled')
        self.assertLess(red_over_blue(cooled['path']), red_over_blue(plain['path']) * 0.7)
        self.assertEqual(nm.frame_count(cooled['path']), 72)
        with self.assertRaises(ValueError):nm.assemble_native_episode({'shots': [{**amber, 'grade': {'r': 3.0}}]}, self.tmp / 'amber-bad')

    def test_a_steady_music_bed_and_a_trimmed_lead_in_assemble_to_the_exact_frames(self):
        shot = grid_clip(self.tmp / 'lead.mp4', seconds=4)
        music = grid_clip(self.tmp / 'm.mp4', seconds=4)
        nm._run(['-i', music['path'], '-vn', self.tmp / 'm.wav'])
        wav = self.tmp / 'm.wav'
        result = nm.assemble_native_episode({'shots': [{**shot, 'source_start_frame': 24, 'frames': 70}],
                                             'music': [{'path': str(wav), 'sha256': digest(wav), 'gain': 0.5, 'steady': True}]}, self.tmp / 'steady')
        self.assertEqual(nm.frame_count(result['path']), 70)
        self.assertEqual(result['mechanical']['defects'], [])

    def test_flash_lights_the_first_frames_and_bad_zooms_are_rejected(self):
        still = grid_clip(self.tmp / 'b.mp4')
        flashed = nm.assemble_native_episode({'shots': [{**still, 'flash_frames': 6}]}, self.tmp / 'flash')
        self.assertEqual(nm.frame_count(flashed['path']), 72)
        with self.assertRaises(ValueError):nm.assemble_native_episode({'shots': [{**still, 'zoom': [1.0, 2.0]}]}, self.tmp / 'bad')

    def test_cuts_are_found_and_a_steady_bed_shrinks_the_jump_at_each_cut(self):
        loud, quiet = grid_clip(self.tmp / 'l.mp4', volume=0.5), grid_clip(self.tmp / 'q.mp4', volume=0.02)
        quiet_sheet = self.tmp / 'q2.mp4'
        nm._run(['-f', 'lavfi', '-i', 'color=c=blue:s=320x568:r=24:d=3', '-f', 'lavfi', '-i', 'sine=frequency=300:duration=3', '-af', 'volume=0.02', '-c:v', 'libx264',
                 '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', quiet_sheet])
        joined = nm.assemble_native_episode({'shots': [loud, {'path': str(quiet_sheet), 'sha256': digest(quiet_sheet), 'frames': 72, 'pixel_checked': True}]}, self.tmp / 'two')
        cuts = detect_cuts(joined['path'])
        self.assertEqual(len(cuts), 1)
        self.assertAlmostEqual(cuts[0], 3.0, delta=0.2)
        jump = edit_profile(joined['path'], cuts)['audio_jump_mean_db']
        self.assertGreater(jump, 10)  # loud shot into a quiet one: the sound lurches at the cut
        diagnostic = joined['mechanical']['cut_audio']
        self.assertEqual(diagnostic['review_count'], 1)
        row = diagnostic['cuts'][0]
        self.assertEqual((row['left_shot_index'], row['right_shot_index'], row['overlap_frames']), (0, 1, 0))
        self.assertAlmostEqual(row['at_seconds'], 3)
        self.assertLess(row['delta_db'], -12)
        self.assertTrue(joined['mechanical']['mechanical_pass'])  # warnings preserve intentional dynamics
        self.assertEqual(json.loads((self.tmp / 'two' / 'assembly.json').read_text())['mechanical']['cut_audio'], diagnostic)
        self.assertEqual(edit_profile(joined['path'], [3])['cut_audio'], cut_audio_report(joined['path'], [3]))

    def test_compare_names_the_gaps_between_a_stiff_film_and_a_lively_reference(self):
        ref = {'motion_mean': 2.5, 'motion_p90': 7.0, 'audio_jump_mean_db': 8.0, 'loudness_range_lu': 10.8, 'seconds_per_cut': 4.0}
        ours = {'motion_mean': 1.9, 'motion_p90': 4.7, 'audio_jump_mean_db': 19.0, 'loudness_range_lu': 5.2, 'seconds_per_cut': 4.1}
        names = [g['metric'] for g in compare_profiles(ref, ours)['gaps']]
        self.assertEqual(names, ['movement', 'sound jumps at cuts', 'flat dynamics'])
        self.assertEqual(compare_profiles(ref, ref)['gaps'], [])


if __name__ == '__main__':
    unittest.main()
