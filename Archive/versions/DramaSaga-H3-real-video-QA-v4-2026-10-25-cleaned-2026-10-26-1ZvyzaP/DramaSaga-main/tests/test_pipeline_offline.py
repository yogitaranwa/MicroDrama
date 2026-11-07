import hashlib
import tempfile
from pathlib import Path
import unittest
from tests.test_audiofirst import brief
from tests.test_audiofirst_story import story
from magicdrama.audiofirst.pipeline import offline_flow, voice_plan, validate_free_audio_asset
from magicdrama.audiofirst.core import digest


class FlowTests(unittest.TestCase):
    def test_offline_flow_no_stops_no_keys(self):
        result = offline_flow(brief(), story())
        self.assertEqual(result['paid_requests'], 0)
        self.assertFalse(result['human_stage_stops'])
        self.assertEqual(len(result['soundtrack']), 10)
        self.assertEqual(result['voices'][0]['provider_voice_id'], None)
        self.assertTrue(result['blocked'])

    def test_trait_profile_not_gender_guess(self):
        result = voice_plan([{'id': 'a', 'name': 'Unknown', 'description': 'Shy and nervous'}])[0]
        self.assertIn('soft hesitant delivery', result['delivery'])
        self.assertNotIn('gender', result)

    def test_language(self):
        b = brief(); b['language'] = 'hi'
        with self.assertRaises(ValueError): offline_flow(b, story())

    def test_no_automatic_free_claim(self):
        with self.assertRaises(ValueError): validate_free_audio_asset({'license': 'Epidemic Sound'})

    def test_free_audio_evidence_binding(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'track.wav'; p.write_bytes(b'synthetic test fixture only')
            terms = Path(t) / 'terms.txt'; terms.write_text('test evidence only, not a real grant')
            asset = {'license': 'CC-BY-4.0', 'path': str(p), 'sha256': digest(p),
                     'license_terms_path': str(terms), 'license_terms_sha256': digest(terms),
                     'source_url': 'https://example.invalid/track', 'license_url': 'https://example.invalid/terms',
                     'creator': 'Test fixture', 'title': 'Test', 'license_checked_at': '2026-10-20',
                     'commercial_use_verified': True, 'sync_use_verified': True, 'attribution': 'fixture'}
            self.assertIn('not_legal_certification', validate_free_audio_asset(asset)['status'])
            terms.write_text('changed')
            with self.assertRaises(ValueError): validate_free_audio_asset(asset)
