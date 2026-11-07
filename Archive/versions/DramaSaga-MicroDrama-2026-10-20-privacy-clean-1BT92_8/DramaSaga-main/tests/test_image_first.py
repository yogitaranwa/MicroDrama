import copy
import unittest
from tests.test_audiofirst import brief
from tests.test_audiofirst_story import story
from magicdrama.audiofirst.images import image_first_plan, image_request, submit_image_live

class ImageFirstTests(unittest.TestCase):
    def plan(self, **kwargs):
        return image_first_plan(brief(), story(), **kwargs)

    def test_refs_props_before_shots(self):
        p = self.plan()
        self.assertEqual(p['planned_images'], 13)  # character, location, letter, ten frames
        self.assertEqual(p['episodes'][0]['new_images'], 4)
        self.assertEqual(p['episodes'][1]['new_images'], 1)
        self.assertEqual(p['planned_credits'], 650)
        self.assertEqual([a['kind'] for a in p['tasks'][:4]], ['character', 'location', 'prop', 'shot_frame'])
        self.assertTrue(p['budget_blockers'])
        self.assertFalse(p['live_enabled'])

    def test_explicit_request_no_auto_resolution(self):
        a = self.plan()['tasks'][0]; r = image_request(a)
        self.assertEqual(r['endpoint'], '/v1/ai-image-generator')
        self.assertEqual(r['body']['model'], 'nano-banana-2.1')
        self.assertEqual(r['body']['resolution'], '1k')
        self.assertEqual(r['body']['image_count'], 1)
        self.assertEqual(r['quoted_credits'], 50)

    def test_shot_cannot_drop_refs(self):
        a = self.plan()['tasks'][3]
        with self.assertRaises(ValueError): image_request(a)
        r = image_request(a, {x: 'api-assets/id/' + x + '.png' for x in a['references']})
        self.assertEqual(r['endpoint'], '/v1/ai-image-editor')
        self.assertEqual(len(r['body']['assets']['image_file_paths']), 3)

    def test_reference_limit(self):
        a = {'id': 'x', 'prompt': 'x', 'references': [str(i) for i in range(10)]}
        with self.assertRaises(ValueError): image_request(a, {str(i): 'api-assets/id/a.png' for i in range(10)})

    def test_uploaded_character_not_rerendered(self):
        b = brief(); b['characters'][0]['image'] = {'mode': 'upload', 'path': 'lead.png'}
        p = image_first_plan(b, story())
        self.assertEqual(p['planned_images'], 12)
        self.assertIn('character-lead', p['uploaded_local_references'])

    def test_image_cap_and_bad_types(self):
        self.assertTrue(any('image cap' in b for b in self.plan(image_cap=3)['budget_blockers']))
        for x in [True, 0, 61, 1.5]:
            with self.assertRaises(ValueError): self.plan(image_cap=x)

    def test_combined_episode_cap(self):
        e = {ep['id']: 0 for ep in story()['episodes']}; e['ep0'] = 2801
        self.assertTrue(any('episode cap' in b for b in self.plan(exposure=e)['budget_blockers']))
        e['ep0'] = 2800
        self.assertEqual(self.plan(exposure=e)['budget_blockers'], [])

    def test_combined_batch_cap_includes_other_episodes(self):
        e = {ep['id']: 0 for ep in story()['episodes']}; e['prior'] = 29351
        self.assertTrue(any('batch cap' in b for b in self.plan(exposure=e)['budget_blockers']))
        e['prior'] = 29350
        self.assertEqual(self.plan(exposure=e)['budget_blockers'], [])

    def test_unknown_exposure_is_not_zero(self):
        for e in [{}, {'ep0': -1}, {'ep0': True}]:
            with self.assertRaises(ValueError): self.plan(exposure=e)

    def test_conflicting_location(self):
        s = story(); s['episodes'][1]['shots'][0]['location_description'] = 'Different room'
        with self.assertRaises(ValueError): image_first_plan(brief(), s)

    def test_live_disabled_even_with_fake_approval(self):
        with self.assertRaises(RuntimeError): submit_image_live(approval=True)

    def test_video_gate_missing_or_changed_image(self):
        import tempfile
        from pathlib import Path
        from magicdrama.audiofirst.images import require_rendered_images
        from magicdrama.audiofirst.core import digest
        p=self.plan()
        with self.assertRaises(ValueError): require_rendered_images(p,{})
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'fixture.png';f.write_bytes(b'fixture')
            receipt={'path':str(f),'sha256':digest(f),'plan_sha256':p['plan_sha256'],
                     'reviewer':'test fixture','reviewed_at':'2026-10-20T00:00:00+00:00',
                     'checks':{k:True for k in ('identity','wardrobe','action','expression','prop_orientation','layout')}}
            a={x['id']:dict(receipt) for x in p['tasks']}
            self.assertEqual(require_rendered_images(p,a)['count'],13)
            f.write_bytes(b'changed')
            with self.assertRaises(ValueError): require_rendered_images(p,a)
