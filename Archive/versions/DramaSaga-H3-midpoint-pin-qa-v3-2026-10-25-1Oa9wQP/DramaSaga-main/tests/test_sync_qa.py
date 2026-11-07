import json
import math
import tempfile
import unittest
import wave
from pathlib import Path

from magicdrama.audiofirst.core import digest
from magicdrama.audiofirst.sync_qa import _envelope, _pcm16, evaluate_render_sync, evaluate_whole_line_mouth_motion


def wav(path, seconds=1.0, delay=0.0, freq=440):
    rate = 16000
    frames = []
    total = round((seconds + delay) * rate)
    for i in range(total):
        t = i / rate - delay
        value = math.sin(2 * math.pi * freq * t) * 12000 if 0 <= t < seconds else 0
        frames.append(int(value).to_bytes(2, 'little', signed=True))
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(b''.join(frames))


class SyncQATests(unittest.TestCase):
    def test_exact_audio_passes_with_visible_speaker_track(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source.wav'; out = root/'out.wav'; wav(source); wav(out)
            track = {'video_sha256': digest(out), 'entries': [
                {'t': .25, 'speaker_id': 'a', 'face_visible': True, 'mouth_visible': True},
                {'t': .75, 'speaker_id': 'b', 'face_visible': True, 'mouth_visible': True},
            ]}; track_path = root/'track.json'; track_path.write_text(json.dumps(track))
            lines = [{'speaker':'a','start':0,'end':.5},{'speaker':'b','start':.5,'end':1}]
            result = evaluate_render_sync(source,out,lines,mouth_track_path=track_path,rendered_video_sha256=digest(out))
            self.assertEqual(result['status'],'pass');self.assertEqual(result['visible_speaker_lines'],2)

    def test_lag_and_hidden_speaker_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source.wav'; out = root/'out.wav'; wav(source); wav(out, delay=.24)
            track = {'video_sha256': digest(out), 'entries': [
                {'t': .49, 'speaker_id': 'a', 'face_visible': False, 'mouth_visible': False},
                {'t': .99, 'speaker_id': 'b', 'face_visible': False, 'mouth_visible': False},
            ]}; track_path = root/'track.json'; track_path.write_text(json.dumps(track))
            lines = [{'speaker':'a','start':0,'end':.5},{'speaker':'b','start':.5,'end':1}]
            result = evaluate_render_sync(source,out,lines,mouth_track_path=track_path,rendered_video_sha256=digest(out))
            self.assertEqual(result['status'],'fail')
            self.assertTrue(any('offset' in f for f in result['failures']))
            self.assertTrue(any('0/2' in f for f in result['failures']))

    def test_missing_track_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source.wav'; out = root/'out.wav'; wav(source); wav(out)
            result = evaluate_render_sync(source,out,[{'speaker':'a','start':0,'end':1}])
            self.assertEqual(result['status'],'fail')
            self.assertTrue(any('0/1' in f for f in result['failures']))

    def test_silent_render_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source.wav'; out = root/'out.wav'; wav(source)
            with wave.open(str(out), 'wb') as f:
                f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000); f.writeframes(b'\0\0' * 16000)
            with self.assertRaisesRegex(ValueError, 'Silent audio'):
                evaluate_render_sync(source,out,[{'speaker':'a','start':0,'end':1}])

    def test_wrong_track_media_hash_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source.wav'; out = root/'out.wav'; wav(source); wav(out)
            track_path = root/'track.json'; track_path.write_text(json.dumps({'video_sha256':'wrong','entries':[]}))
            with self.assertRaisesRegex(ValueError, 'different video'):
                evaluate_render_sync(source,out,[{'speaker':'a','start':0,'end':1}],mouth_track_path=track_path,rendered_video_sha256=digest(out))

    def test_invalid_dialogue_timing_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source.wav'; out = root/'out.wav'; wav(source); wav(out)
            with self.assertRaisesRegex(ValueError, 'timing invalid'):
                evaluate_render_sync(source,out,[{'speaker':'a','start':.8,'end':.2}])

    def test_track_entry_wrong_speaker_does_not_count(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source.wav'; out = root/'out.wav'; wav(source); wav(out)
            track = {'video_sha256': digest(out), 'entries': [{'t': .5, 'speaker_id': 'other', 'face_visible': True, 'mouth_visible': True}]}
            track_path = root/'track.json'; track_path.write_text(json.dumps(track))
            result = evaluate_render_sync(source,out,[{'speaker':'a','start':0,'end':1}],mouth_track_path=track_path,rendered_video_sha256=digest(out))
            self.assertEqual(result['status'],'fail');self.assertEqual(result['visible_speaker_lines'],0)

    def test_whole_line_mouth_motion_pass_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source.wav'; out = root/'out.wav'; wav(source); wav(out)
            samples, rate, seconds = _pcm16(source)
            env = _envelope(samples, rate, step=.04)
            entries = []
            for n, value in enumerate(env[:25]):
                entries.append({'t': n * .04, 'speaker_id': 'a', 'face_visible': True, 'mouth_visible': True, 'mouth_open': value + .01})
            track = {'video_sha256': digest(out), 'entries': entries}
            track_path = root/'dense.json'; track_path.write_text(json.dumps(track))
            lines = [{'id':'L1','speaker':'a','start':0,'end':1}]
            result = evaluate_whole_line_mouth_motion(source,out,lines,dense_mouth_track_path=track_path,rendered_video_sha256=digest(out))
            self.assertEqual(result['status'],'pass')
            self.assertEqual(result['lines'][0]['visible_samples'],25)
            self.assertGreaterEqual(result['lines'][0]['mouth_motion_correlation'],.7)

            for i, item in enumerate(entries):
                if i % 2:
                    item['face_visible'] = False
            track_path.write_text(json.dumps(track))
            result = evaluate_whole_line_mouth_motion(source,out,lines,dense_mouth_track_path=track_path,rendered_video_sha256=digest(out))
            self.assertEqual(result['status'],'fail')
            self.assertTrue(any('coverage' in f for f in result['failures']))

    def test_whole_line_mouth_motion_rejects_lagged_motion(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source.wav'; out = root/'out.wav'; wav(source); wav(out)
            samples, rate, seconds = _pcm16(source)
            env = _envelope(samples, rate, step=.04)
            lagged = [0.01] * 4 + [v + .01 for v in env[:21]]
            track = {'video_sha256': digest(out), 'entries': [
                {'t': n * .04, 'speaker_id': 'a', 'face_visible': True, 'mouth_visible': True, 'mouth_open': v}
                for n, v in enumerate(lagged)
            ]}
            track_path = root/'dense.json'; track_path.write_text(json.dumps(track))
            result = evaluate_whole_line_mouth_motion(
                source,out,[{'id':'L1','speaker':'a','start':0,'end':1}],
                dense_mouth_track_path=track_path,rendered_video_sha256=digest(out))
            self.assertEqual(result['status'],'fail')
            self.assertTrue(any('mouth-motion correlation' in f or 'No speech/mouth variation' in f for f in result['failures']))


if __name__ == '__main__':
    unittest.main()
