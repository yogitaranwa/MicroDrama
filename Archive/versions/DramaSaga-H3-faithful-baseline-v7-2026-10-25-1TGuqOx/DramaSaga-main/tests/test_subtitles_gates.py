import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave
from magicdrama.audiofirst.core import digest, timeline, validate_timeline
from magicdrama.audiofirst.subtitles import write_subtitles, burn_subtitles
from magicdrama.audiofirst.gates import CHECKS, STAGES, object_hash, require_stage


class SubtitleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); p = self.root / 'speech.wav'
        with wave.open(str(p), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b'\0' * 128000)
        text = 'The letter was here. Who moved it?'
        line = {'id': 'a', 'speaker': 'lead', 'text': text, 'audio_path': str(p),
                'approval': {'sha256': digest(p), 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                             'speaker_id': 'lead', 'words': True, 'speaker': True, 'emotion': True, 'pronunciation': True}}
        self.track = timeline([line], ['lead'])

    def test_srt_exact_text(self):
        result = write_subtitles(self.track, self.root / 'sub')
        self.assertIn('00:00:00,000 --> 00:00:04,000', (self.root / 'sub/captions.srt').read_text())
        self.assertEqual(result['cues'][0]['text'], self.track['lines'][0]['text'])

    def test_tamper_fields(self):
        for field, value in [('seconds', 10), ('frames', 97)]:
            t = copy.deepcopy(self.track); t[field] = value
            with self.assertRaises(ValueError): validate_timeline(t)
        for field, value in [('start_frame', 2), ('end_frame', 94), ('measured_seconds', 3), ('text', 'changed'), ('speaker', 'other')]:
            t = copy.deepcopy(self.track); t['lines'][0][field] = value
            with self.assertRaises(ValueError): validate_timeline(t)

    def test_audio_change(self):
        Path(self.track['lines'][0]['audio_path']).write_bytes(b'changed')
        with self.assertRaises((ValueError, subprocess.CalledProcessError)): write_subtitles(self.track, self.root / 'sub')

    def test_overlong_cue_fails(self):
        t = copy.deepcopy(self.track); text = 'longword ' * 20
        t['lines'][0]['text'] = text
        t['lines'][0]['approval']['text_sha256'] = hashlib.sha256(text.encode()).hexdigest()
        with self.assertRaises(ValueError): write_subtitles(t, self.root / 'sub')

    def test_markup_fails(self):
        t = copy.deepcopy(self.track); text = '{override}Hello'
        t['lines'][0]['text'] = text; t['lines'][0]['approval']['text_sha256'] = hashlib.sha256(text.encode()).hexdigest()
        with self.assertRaises(ValueError): write_subtitles(t, self.root / 'sub')

    def test_language_fails(self):
        with self.assertRaises(ValueError): write_subtitles(self.track, self.root / 'sub', 'hi')

    def test_overlap_fails(self):
        t = copy.deepcopy(self.track); t['lines'].append({**t['lines'][0], 'id': 'b'})
        with self.assertRaises(ValueError): validate_timeline(t)

    def test_burn_real_video_and_tampering(self):
        source = self.root / 'source.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=0x17324d:s=360x640:r=24:d=4',
                        '-i', self.track['lines'][0]['audio_path'], '-c:v', 'libx264', '-c:a', 'aac', str(source)], check=True)
        write_subtitles(self.track, self.root / 'sub')
        result = burn_subtitles(self.track, source, self.root / 'sub', self.root / 'burned.mp4')
        self.assertEqual(result['sha256'], digest(self.root / 'burned.mp4'))
        (self.root / 'sub/captions.ass').write_text('changed')
        with self.assertRaises(ValueError): burn_subtitles(self.track, source, self.root / 'sub', self.root / 'bad.mp4')

    def test_review_chain(self):
        p = self.root / 'artifact.json'; p.write_text('{}')
        bundle = {}; previous = None
        for name in STAGES:
            r = {'stage': name, 'previous_receipt_sha256': previous, 'reviewer': 'test fixture',
                 'reviewed_at': '2026-10-20T00:00:00Z', 'artifacts': {str(p): digest(p)},
                 'checks': dict.fromkeys(CHECKS[name], True)}
            bundle[name] = r; previous = object_hash(r)
        require_stage(bundle, 'final')
        bundle['story']['checks']['continuity'] = False
        with self.assertRaises(ValueError): require_stage(bundle, 'final')

    def test_missing_chain(self):
        with self.assertRaises(ValueError): require_stage({}, 'audio')

    def test_input_binding(self):
        from magicdrama.audiofirst.gates import require_inputs
        p = self.root / 'reviewed.json'; p.write_text('{}')
        r = {'stage': 'story', 'previous_receipt_sha256': None, 'reviewer': 'fixture',
             'reviewed_at': '2026-10-20T00:00:00Z', 'artifacts': {str(p): digest(p)},
             'checks': dict.fromkeys(CHECKS['story'], True)}
        require_inputs({'story': r}, 'story', [p])
        other = self.root / 'other.json'; other.write_text('{}')
        with self.assertRaises(ValueError): require_inputs({'story': r}, 'story', [other])
        p.write_text('changed')
        with self.assertRaises(ValueError): require_stage({'story': r}, 'story')

    def test_bad_boolean_and_nonfinite(self):
        for field, value in [('fps', True), ('seconds', float('nan')), ('frames', -1)]:
            t = copy.deepcopy(self.track); t[field] = value
            with self.assertRaises(ValueError): validate_timeline(t)

    def test_reading_speed(self):
        with self.assertRaises(ValueError): write_subtitles(self.track, self.root / 'sub', max_cps=1)

    def test_h3_audio_padded_to_actual_grid(self):
        from magicdrama.audiofirst.core import padded_clip_timing
        result = padded_clip_timing(11)
        self.assertEqual(result['frames'], 277)
        self.assertGreater(result['pad_audio_to_seconds'], 11)
        with self.assertRaises(ValueError): padded_clip_timing(16)

    def test_missing_approval_and_tail(self):
        t = copy.deepcopy(self.track); t['lines'][0].pop('approval')
        with self.assertRaises(ValueError): validate_timeline(t)
        t = copy.deepcopy(self.track); t['frames'] += 1; t['seconds'] = t['frames'] / 24
        with self.assertRaises(ValueError): validate_timeline(t)

    def test_cli_missing_timeline_fails_without_reviews(self):
        cli = Path(__file__).parents[1] / 'audiofirst.py'
        result = subprocess.run(['python3', str(cli), 'subtitles', '--timeline', 'missing.json',
                                 '--out', str(self.root / 'captions')], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'the following arguments are required: --reviews', result.stderr)
        self.assertFalse((self.root / 'captions').exists())

    def test_failed_stage_does_not_accept_unzoned_timestamp(self):
        p = self.root / 'artifact'; p.write_text('sample')
        r = {'stage': 'story', 'previous_receipt_sha256': None, 'reviewer': 'fixture',
             'reviewed_at': '2026-10-20T00:00:00', 'artifacts': {str(p): digest(p)},
             'checks': dict.fromkeys(CHECKS['story'], True)}
        with self.assertRaises(ValueError): require_stage({'story': r}, 'story')

    def test_speaker_and_introduction_bars(self):
        write_subtitles(self.track, self.root / 'sub', character_names={'lead': 'Maya'},
                        introductions=[{'speaker': 'lead', 'start_frame': 0, 'end_frame': 48}])
        ass = (self.root / 'sub/captions.ass').read_text()
        self.assertIn('Speaker,,0,0,0,,Maya', ass)
        self.assertIn('Introduction,,0,0,0,,Maya', ass)
        self.assertNotIn('Maya', (self.root / 'sub/captions.srt').read_text())

    def test_missing_speaker_display_name(self):
        with self.assertRaises(ValueError): write_subtitles(self.track, self.root / 'sub', character_names={})

    def test_name_markup_and_intro_bounds(self):
        with self.assertRaises(ValueError): write_subtitles(self.track, self.root / 'bad', character_names={'lead': '{override}'})
        with self.assertRaises(ValueError): write_subtitles(self.track, self.root / 'bad2', character_names={'lead': 'Maya'}, introductions=[{'speaker': 'lead', 'start_frame': 0, 'end_frame': 1000}])
