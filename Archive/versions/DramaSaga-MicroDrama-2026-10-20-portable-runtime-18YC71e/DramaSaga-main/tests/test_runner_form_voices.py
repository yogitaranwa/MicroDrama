import base64
import tempfile
from pathlib import Path
import unittest
from tests.test_audiofirst import brief
from tests.test_audiofirst_story import story
from magicdrama.audiofirst.runner import run, write_draft
from magicdrama.audiofirst.voices import dialogue_plan, submit_voice_live, AMELIA, PETER
from magicdrama.audiofirst.form import save_form
from magicdrama.audiofirst.season import pack_season

class UnifiedTests(unittest.TestCase):
    def test_missing_story_writes_request_not_fake_season(self):
        with tempfile.TemporaryDirectory() as t:
            r = run(brief(), Path(t)/'run')
            self.assertEqual(r['blocked'][0]['stage'], 'writing')
            self.assertFalse((Path(t)/'run/story.json').exists())

    def test_injected_writer_and_no_spend(self):
        with tempfile.TemporaryDirectory() as t:
            r = run(brief(), Path(t)/'run', writer=lambda request: story())
            self.assertEqual(r['paid_requests'], 0)
            self.assertEqual(r['image_count'], 13)
            self.assertTrue((Path(t)/'run/voice-requests.json').exists())
            self.assertTrue(any(b['stage']=='final_season_video' for b in r['blocked']))
            with self.assertRaises(ValueError): run(brief(), Path(t)/'run', story())

    def test_template_label_and_episode_count(self):
        b = brief(); b['episodes_per_season'] = 50
        s = write_draft(b)
        self.assertEqual(len(s['episodes']), 50)
        self.assertIn('TEMPLATE', s['writer_status'])
        self.assertTrue(s['limitations'])

    def test_continuation_needs_verified_archive(self):
        b = brief(); b['season'] = 2
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError): run(b, Path(t)/'run')
            source=Path(t)/'source';source.mkdir();(source/'story.json').write_text('{}')
            z=Path(t)/'s1.zip'
            pack_season(source,z,'sample',1,{'characters':[], 'facts':[], 'unresolved':['Who sent the note?'], 'ending':'Door opens'})
            r=run(b,Path(t)/'run',previous_zip=z)
            self.assertTrue((Path(t)/'run/previous-canon.json').exists())

    def test_named_default_and_tagged_count(self):
        b = brief(); b['characters'][0]['name'] = 'Clara Bennett'
        p = dialogue_plan(b, story()); ep=p['episodes'][0]
        self.assertEqual(p['cast']['lead']['voice_id'], AMELIA)
        self.assertGreater(ep['submitted_characters'], ep['spoken_characters'])
        b['characters'][0]['name']='Oliver Reed'
        self.assertEqual(dialogue_plan(b,story())['cast']['lead']['voice_id'],PETER)
        self.assertEqual(ep['request']['body']['model_id'],'eleven_v3')

    def test_unknown_cast_not_gender_guessed(self):
        p=dialogue_plan(brief(),story())
        self.assertIsNone(p['cast']['lead']['voice_id'])
        self.assertEqual(p['episodes'][0]['missing_voice_selections'], ['lead'])
        with self.assertRaises(RuntimeError): submit_voice_live(approved=True)

    def test_explicit_voice_override(self):
        p=dialogue_plan(brief(),story(),{'lead':'chosen'})
        self.assertEqual(p['episodes'][0]['request']['body']['inputs'][0]['voice_id'],'chosen')

    def test_form_validate_schema_and_upload(self):
        b=brief();b['characters'][0]['image']={'mode':'upload','path':'../../bad'}
        with tempfile.TemporaryDirectory() as t:
            # Container-header unit fixture only; image decoding still required before generation.
            r=save_form({'brief':b,'uploads':{'lead':base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()}},t)
            self.assertTrue(Path(r['brief_path']).exists())
            self.assertEqual(Path(b['characters'][0]['image']['path']).parent.name,'uploads')
            self.assertEqual(r['paid_requests'],0)

    def test_form_rejects_missing_upload_or_long_setting(self):
        b=brief();b['characters'][0]['image']={'mode':'upload','path':'x'}
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError): save_form({'brief':b},t)
            b=brief();b['setting']='a'*1001
            with self.assertRaises(ValueError): save_form({'brief':b},t)

    def test_soundtrack_license_not_bypassed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError): run(brief(),Path(t)/'run',story(),soundtrack=[{'license':'unlicensed'}])

class WriterTests(unittest.TestCase):
    def test_disabled_no_transport_call(self):
        from magicdrama.audiofirst.writer import write_season
        with self.assertRaises(RuntimeError): write_season(brief(), lambda p: self.fail('called'), 'test')

    def test_model_writer_strict_schema_and_one_attempt(self):
        from magicdrama.audiofirst.writer import write_season
        calls=[]
        def transport(p): calls.append(p); return story()
        s=write_season(brief(),transport,'test-fixture',enabled=True,approval_reference='fixture-not-real-permission')
        self.assertEqual(len(calls),1)
        self.assertIn('MODEL_DRAFT',s['writer_status'])
        self.assertEqual(calls[0]['model'],'test-fixture')
        with self.assertRaises(ValueError): write_season(brief(),lambda p:'not json','test',enabled=True,approval_reference='fixture')
