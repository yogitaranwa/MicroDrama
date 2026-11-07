import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import wave
import zipfile

from magicdrama.audiofirst.core import digest, timeline, validate_brief, writing_request, schedule_shots
from magicdrama.audiofirst.budget import SpendLedger
from magicdrama.audiofirst.season import inspect_season_zip, extract_season_zip, pack_season
from magicdrama.audiofirst.providers import video_request, submit_live
from magicdrama.audiofirst.media import build_master


def brief():
    return {'series_id': 'sample', 'season': 1, 'character_count': 1, 'episodes_per_season': 10,
            'genres': ['drama', 'mystery'], 'setting': 'Modern city', 'language': 'en-IN',
            'characters': [{'id': 'lead', 'name': 'Lead', 'description': 'An observant clerk',
                            'image': {'mode': 'generate', 'model': 'nano-banana-2.1', 'prompt': 'portrait'}}]}


class AudioFirstTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.audio = self.root / 'line.wav'
        with wave.open(str(self.audio), 'wb') as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(16000); out.writeframes(b'\0' * 32000)
        self.line = {'id': 'line1', 'speaker': 'lead', 'text': 'This line has more than eight words without a forced cut.',
                     'audio_path': str(self.audio), 'approval': {'sha256': digest(self.audio),
                     'words': True, 'speaker': True, 'emotion': True, 'pronunciation': True}}
        self.line['approval'].update(text_sha256=hashlib.sha256(self.line['text'].encode()).hexdigest(), speaker_id='lead')

    def test_brief(self):
        validate_brief(brief())

    def test_unicode_limit(self):
        b = brief(); b['setting'] = 'क' * 1000; validate_brief(b); b['setting'] += 'क'
        with self.assertRaises(ValueError): validate_brief(b)

    def test_bad_episode_counts(self):
        for value in (0, 9, 51, True, 10.5):
            b = brief(); b['episodes_per_season'] = value
            with self.assertRaises(ValueError): validate_brief(b)

    def test_wrong_count(self):
        b = brief(); b['character_count'] = 2
        with self.assertRaises(ValueError): validate_brief(b)

    def test_duplicate_genres(self):
        b = brief(); b['genres'] *= 2
        with self.assertRaises(ValueError): validate_brief(b)

    def test_bad_model(self):
        b = brief(); b['characters'][0]['image']['model'] = 'guess'
        with self.assertRaises(ValueError): validate_brief(b)

    def test_unknown_field(self):
        b = brief(); b['execute'] = 'shell'
        with self.assertRaises(ValueError): validate_brief(b)

    def test_runtime(self):
        b = brief(); b['target_season_seconds'] = 2000
        with self.assertRaises(ValueError): validate_brief(b)
        b['target_season_seconds'] = 200
        self.assertIsNone(writing_request(b)['runtime']['episode_min_seconds'])

    def test_continuation(self):
        b = brief(); b['season'] = 2
        with self.assertRaises(ValueError): writing_request(b)
        with self.assertRaises(ValueError): writing_request(b, {'series_id': 'wrong', 'season': 1})
        self.assertEqual(writing_request(b, {'series_id': 'sample', 'season': 1, 'canon': {}})['paid_requests'], 0)

    def test_measured_audio(self):
        self.assertEqual(timeline([self.line], ['lead'])['frames'], 24)

    def test_changed_audio(self):
        self.audio.write_bytes(b'changed')
        with self.assertRaises(ValueError): timeline([self.line], ['lead'])

    def test_review(self):
        self.line['approval']['emotion'] = False
        with self.assertRaises(ValueError): timeline([self.line], ['lead'])

    def test_speaker(self):
        with self.assertRaises(ValueError): timeline([self.line], ['other'])

    def test_duplicate_line(self):
        with self.assertRaises(ValueError): timeline([self.line, self.line], ['lead'])

    def test_frame_grid(self):
        lines = [{**self.line, 'id': 'l' + str(n)} for n in range(30)]
        self.assertEqual(timeline(lines, ['lead'], probe=lambda p: 1.013)['frames'], 30 * 25 + 29 * 5)

    def test_pin_gate(self):
        with self.assertRaises(ValueError): schedule_shots(timeline([self.line], ['lead']), [{'id': 'shot1', 'line_ids': ['line1'], 'pins': [1]}])

    def test_real_master(self):
        result = build_master(timeline([self.line], ['lead']), self.root / 'master.wav')
        with wave.open(result['path']) as wav: self.assertEqual(wav.getnframes(), 48000)

    def test_live_off(self):
        with self.assertRaises(RuntimeError): submit_live()

    def test_provider_contract(self):
        shot = {'seconds': 10, 'prompt': 'conversation', 'visible_characters': ['lead', 'other'], 'speakers': ['lead', 'other']}
        self.assertFalse(video_request('magichour_audio_to_video', shot, 'a.wav')['live_enabled'])
        with self.assertRaises(ValueError): video_request('magichour_lip_sync', shot, 'a.wav', video_asset='v.mp4')
        with self.assertRaises(ValueError): video_request('magichour_image_to_video', shot, 'a.wav')


    def test_h3_reference_video_contract(self):
        shot = {'seconds': 13, 'prompt': 'urgent Yule Ball dance', 'visible_characters': ['lead', 'other'], 'speakers': ['lead', 'other']}
        r = video_request('magichour_h3_reference_to_video', shot, 'api-assets/id/voice.mp3', 'api-assets/id/scene.png')
        self.assertEqual(r['endpoint'], '/v1/text-to-video')
        self.assertEqual(r['body']['model'], 'minimax-h3')
        self.assertTrue(r['body']['audio'])
        self.assertEqual(r['body']['references'][-1], {'file_path': 'api-assets/id/voice.mp3', 'name': 'voice'})
        self.assertEqual(r['body']['aspect_ratio'], '9:16')
        with self.assertRaises(ValueError): video_request('magichour_h3_reference_to_video', shot, 'api-assets/id/voice.mp3')


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.assets = self.root / 'assets'; self.assets.mkdir()
        (self.assets / 'episode.txt').write_text('story'); self.archive = self.root / 'season.zip'
        self.canon = {'characters': [], 'facts': [], 'unresolved': [], 'ending': 'door opens'}

    def test_roundtrip(self):
        pack_season(self.assets, self.archive, 'series', 1, self.canon)
        self.assertEqual(inspect_season_zip(self.archive)['canon'], self.canon)
        extract_season_zip(self.archive, self.root / 'restored')
        self.assertEqual((self.root / 'restored/episode.txt').read_text(), 'story')

    def test_traversal(self):
        with zipfile.ZipFile(self.archive, 'w') as z: z.writestr('../evil', 'x')
        with self.assertRaises(ValueError): inspect_season_zip(self.archive)

    def test_collision(self):
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('a', 'x'); z.writestr('A', 'y')
        with self.assertRaises(ValueError): inspect_season_zip(self.archive)

    def test_requires_manifest(self):
        with zipfile.ZipFile(self.archive, 'w') as z: z.writestr('video.mp4', 'x')
        with self.assertRaises(ValueError): inspect_season_zip(self.archive)

    def test_tamper(self):
        m = pack_season(self.assets, self.archive, 'series', 1, self.canon); self.archive.unlink()
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('season.json', json.dumps(m)); z.writestr('episode.txt', 'alter')
        with self.assertRaises(ValueError): inspect_season_zip(self.archive)

    def test_limits(self):
        pack_season(self.assets, self.archive, 'series', 1, self.canon)
        with self.assertRaises(ValueError): inspect_season_zip(self.archive, max_files=1)

    def test_credentials(self):
        (self.assets / '.env').write_text('not-a-secret')
        with self.assertRaises(ValueError): pack_season(self.assets, self.archive, 'series', 1, self.canon)


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.ledger = SpendLedger(str(Path(self.temp.name) / 'spend.sqlite')); self.addCleanup(self.ledger.close)
        today = datetime.date.today().isoformat()
        self.quote = {'amount': 30, 'unit': 'credits', 'verified_at': today}
        self.approval = {'cap': 100, 'provider': 'video', 'unit': 'credits', 'valid_on': today, 'approval_reference': 'reviewed-test'}

    def reserve(self, key='one', payload=None):
        return self.ledger.reserve(key, 'video', 'credits', payload or {'scene': 1}, self.quote, self.approval)

    def test_unknown_never_retries(self):
        self.reserve(); self.ledger.mark_submitting('one'); self.ledger.unknown('one')
        with self.assertRaises(RuntimeError): self.reserve()

    def test_changed_payload(self):
        self.reserve()
        with self.assertRaises(ValueError): self.reserve(payload={'scene': 2})

    def test_caps(self):
        for key in ['a', 'b', 'c']: self.reserve(key)
        with self.assertRaises(ValueError): self.reserve('d')

    def test_overcharge(self):
        self.reserve(); self.ledger.mark_submitting('one'); self.ledger.submitted('one', 'id'); self.ledger.complete('one', 90)
        with self.assertRaises(ValueError): self.reserve('two')

    def test_expired(self):
        self.quote['verified_at'] = '2000-01-01'
        with self.assertRaises(ValueError): self.reserve()

    def test_wrong_unit(self):
        self.approval['unit'] = 'usd'
        with self.assertRaises(ValueError): self.reserve()

    def test_nan(self):
        self.quote['amount'] = float('nan')
        with self.assertRaises(ValueError): self.reserve()
