"""Reference-to-video planning tests. Synthetic only: no network, keys or spend.

Passing these tests establishes that the planner, validator and quote math
behave as coded against the verified 2026-10-26 catalog. They do not
establish that Magic Hour accepts the request, that any model honors the
references, or that generated media is good.
"""
import unittest

from magicdrama.audiofirst import r2v
from magicdrama.audiofirst.execution import signature
from magicdrama.audiofirst.live import validate_job
from magicdrama.audiofirst.magichour_catalog import quote_credits

HASH = 'a' * 64
HASH2 = 'b' * 64
HASH3 = 'c' * 64


def bank():
    return {'references': [
        {'id': 'harry', 'name': 'Harry', 'kind': 'character', 'views': ['front', 'close', 'full_body'], 'sha256': HASH, 'version': 1},
        {'id': 'draconia', 'name': 'Draconia', 'kind': 'character', 'views': ['front', 'close', 'profile'], 'sha256': HASH2, 'version': 1},
        {'id': 'location-great_hall', 'name': 'GreatHall', 'kind': 'location', 'views': ['wide'], 'sha256': HASH3, 'version': 1},
    ]}


def uploads():
    return {
        'harry': {'file_path': 'api-assets/id/harry.png', 'sha256': HASH},
        'draconia': {'file_path': 'api-assets/id/draconia.png', 'sha256': HASH2},
        'location-great_hall': {'file_path': 'api-assets/id/hall.png', 'sha256': HASH3},
    }


def shot(**overrides):
    base = {'id': 'e01s02', 'seconds': 6, 'location': 'great_hall', 'framing': 'front',
            'visible_characters': ['harry', 'draconia'], 'line_ids': [], 'speakers': [],
            'action': 'Draconia pulls Harry onto the dance floor as ice arrows strike',
            'camera': 'locked wide, no push-in'}
    base.update(overrides)
    return base


def episode():
    return {'id': 'e01', 'shots': [shot(), shot(id='e01s03', seconds=5, framing='close',
            visible_characters=['draconia'], action='Draconia grins despite the chaos')]}


class CatalogTests(unittest.TestCase):
    def test_seedance_quote_matches_verified_rate(self):
        self.assertEqual(quote_credits('seedance-2.0', 8, '720p'), 2304)
        self.assertEqual(quote_credits('seedance-2.0', 8, '480p'), 1152)

    def test_minimax_h3_is_cheaper_verified_route(self):
        self.assertEqual(quote_credits('minimax-h3', 8, '720p'), 384)

    def test_unverified_rate_refused_not_guessed(self):
        with self.assertRaises(ValueError):
            quote_credits('seedance-2.0-fast', 8, '720p')

    def test_unknown_model_refused(self):
        with self.assertRaises(ValueError):
            quote_credits('nano-banana-2.1', 8, '720p')

    def test_duration_outside_model_set_refused(self):
        with self.assertRaises(ValueError):
            quote_credits('seedance-2.0', 20, '720p')


class SelectionTests(unittest.TestCase):
    def test_selects_visible_characters_and_location(self):
        refs = r2v.select_shot_references(shot(), bank(), uploads())
        self.assertEqual([r['name'] for r in refs], ['Harry', 'Draconia', 'GreatHall'])
        self.assertTrue(all(r['file_path'].startswith('api-assets/') for r in refs))

    def test_missing_view_is_gap_not_substitution(self):
        with self.assertRaises(ValueError) as ctx:
            r2v.select_shot_references(shot(framing='profile'), bank(), uploads())
        self.assertIn('explicit gap', str(ctx.exception))

    def test_unbanked_character_is_gap(self):
        with self.assertRaises(ValueError):
            r2v.select_shot_references(shot(visible_characters=['harry', 'voldemort']), bank(), uploads())

    def test_unuploaded_reference_refused(self):
        with self.assertRaises(ValueError):
            r2v.select_shot_references(shot(visible_characters=['harry'], location=None), bank(), {})

    def test_hash_mismatch_refused(self):
        bad = uploads(); bad['harry'] = {'file_path': 'api-assets/id/harry.png', 'sha256': HASH2}
        with self.assertRaises(ValueError):
            r2v.select_shot_references(shot(visible_characters=['harry'], location=None), bank(), bad)

    def test_over_limit_refused_not_trimmed(self):
        big = {'references': [{'id': 'c%d' % i, 'name': 'C%d' % i, 'kind': 'character',
                               'views': ['front'], 'sha256': HASH} for i in range(11)]}
        up = {'c%d' % i: {'file_path': 'api-assets/id/c%d.png' % i, 'sha256': HASH} for i in range(11)}
        with self.assertRaises(ValueError) as ctx:
            r2v.select_shot_references(shot(visible_characters=['c%d' % i for i in range(11)], location=None), big, up)
        self.assertIn('never drop silently', str(ctx.exception))

    def test_reference_name_rules(self):
        for bad in ('', '@Harry', 'Harry Potter', 'x' * 65):
            with self.assertRaises(ValueError):
                r2v.validate_reference_name(bad)
        self.assertEqual(r2v.validate_reference_name(' Harry '), 'Harry')


class RequestTests(unittest.TestCase):
    def test_request_shape_and_quote(self):
        refs = r2v.select_shot_references(shot(), bank(), uploads())
        req = r2v.build_r2v_request(shot(), refs, 'minimax-h3', '720p', '9:16')
        self.assertEqual(req['endpoint'], '/v1/text-to-video')
        body = req['body']
        self.assertEqual(body['model'], 'minimax-h3')
        self.assertEqual(body['audio'], False)
        self.assertEqual(len(body['references']), 3)
        self.assertIn('@Harry', body['style']['prompt'])
        self.assertIn('@Draconia', body['style']['prompt'])
        self.assertEqual(req['quote']['amount'], 288)  # 6s * 48 credits at 720p
        self.assertEqual(req['quote']['unit'], 'credits')
        self.assertFalse(req['live_enabled'])

    def test_fractional_seconds_refused(self):
        refs = r2v.select_shot_references(shot(), bank(), uploads())
        with self.assertRaises(ValueError):
            r2v.build_r2v_request(shot(seconds=6.4), refs, 'minimax-h3', '720p', '9:16')

    def test_prompt_carries_continuity_state(self):
        refs = r2v.select_shot_references(shot(), bank(), uploads())
        s = shot(start_state={'characters': {'harry': {'position': 'door'}}})
        req = r2v.build_r2v_request(s, refs, 'minimax-h3', '720p', '9:16')
        self.assertIn('start state', req['body']['style']['prompt'])

    def test_identity_mentions_alone_form_valid_prompt(self):
        s = shot(action='', camera='')
        refs = r2v.select_shot_references(s, bank(), uploads())
        req = r2v.build_r2v_request(s, refs, 'minimax-h3', '720p', '9:16')
        self.assertIn('@Harry', req['body']['style']['prompt'])

    def test_no_references_refused(self):
        with self.assertRaises(ValueError):
            r2v.build_r2v_request(shot(), [], 'minimax-h3', '720p', '9:16')


class ManifestTests(unittest.TestCase):
    def test_manifest_plans_non_speaking_shots(self):
        manifest = r2v.reference_video_manifest(episode(), bank(), uploads(), 'run-1', 'batch-1',
                                                'minimax-h3', '720p')
        self.assertEqual(len(manifest['jobs']), 2)
        self.assertEqual(manifest['status'], 'planned_not_submitted')
        self.assertEqual(manifest['manifest_sha256'],
                         signature({k: v for k, v in manifest.items() if k != 'manifest_sha256'}))
        total = sum(j['quote']['amount'] for j in manifest['jobs'])
        self.assertEqual(total, 288 + 240)

    def test_speaking_shot_refused_not_reclassified(self):
        ep = {'id': 'e01', 'shots': [shot(line_ids=['l1'], speakers=['draconia'])]}
        with self.assertRaises(ValueError) as ctx:
            r2v.reference_video_manifest(ep, bank(), uploads(), 'run-1', 'batch-1', 'minimax-h3', '720p')
        self.assertIn('exact-audio', str(ctx.exception))

    def test_live_validation_accepts_compiled_job(self):
        manifest = r2v.reference_video_manifest(episode(), bank(), uploads(), 'run-1', 'batch-1',
                                                'minimax-h3', '720p')
        validate_job(manifest['jobs'][0])  # must not raise

    def test_live_validation_refuses_tampered_quote(self):
        manifest = r2v.reference_video_manifest(episode(), bank(), uploads(), 'run-1', 'batch-1',
                                                'minimax-h3', '720p')
        job = dict(manifest['jobs'][0])
        job['quote'] = dict(job['quote'], amount=1)
        with self.assertRaises(ValueError):
            validate_job(job)

    def test_live_validation_refuses_tampered_model(self):
        manifest = r2v.reference_video_manifest(episode(), bank(), uploads(), 'run-1', 'batch-1',
                                                'minimax-h3', '720p')
        import copy
        job = copy.deepcopy(manifest['jobs'][0])
        job['request']['body']['model'] = 'seedance-2.5'
        with self.assertRaises(ValueError):
            validate_job(job)

    def test_live_validation_refuses_bad_reference_path(self):
        manifest = r2v.reference_video_manifest(episode(), bank(), uploads(), 'run-1', 'batch-1',
                                                'minimax-h3', '720p')
        import copy
        job = copy.deepcopy(manifest['jobs'][0])
        job['request']['body']['references'][0]['file_path'] = 'https://evil.example/x.png'
        with self.assertRaises(ValueError):
            validate_job(job)


class ComparisonTests(unittest.TestCase):
    def test_compare_quotes_reports_each_model(self):
        report = r2v.compare_route_quotes(episode(), bank())
        self.assertEqual(report['status'], 'comparison_only_not_an_order')
        self.assertEqual(report['models']['minimax-h3']['credits'], 528)
        self.assertEqual(report['models']['seedance-2.0']['credits'], 3168)
        self.assertEqual(report['models']['seedance-2.0-mini']['credits'], 2112)

    def test_compare_skips_speaking_shots(self):
        ep = {'id': 'e01', 'shots': [shot(line_ids=['l1'], speakers=['draconia'])]}
        report = r2v.compare_route_quotes(ep, bank())
        self.assertEqual(report['models']['minimax-h3']['credits'], 0)


if __name__ == '__main__':
    unittest.main()


class MultiEntryBankTests(unittest.TestCase):
    """Real-bank shape: one file per character per view, plus pair and location refs."""

    def bank2(self):
        return {'references': [
            {'id': 'harry-close', 'name': 'Harry', 'kind': 'character', 'views': ['front', 'close'],
             'sha256': HASH, 'characters': ['harry'], 'primary': True},
            {'id': 'harry-full', 'name': 'HarryFull', 'kind': 'character', 'views': ['full_body', 'wide'],
             'sha256': HASH, 'characters': ['harry'], 'primary': True},
            {'id': 'draconia-close', 'name': 'Draconia', 'kind': 'character', 'views': ['front', 'close'],
             'sha256': HASH2, 'characters': ['draconia'], 'primary': True},
            {'id': 'draconia-full', 'name': 'DraconiaFull', 'kind': 'character', 'views': ['full_body', 'wide'],
             'sha256': HASH2, 'characters': ['draconia'], 'primary': True},
            {'id': 'pair-wide', 'name': 'PairWide', 'kind': 'character', 'views': ['wide'],
             'sha256': HASH3, 'characters': ['harry', 'draconia'], 'primary': True},
            {'id': 'hall', 'name': 'GreatHall', 'kind': 'location', 'views': ['wide'],
             'sha256': HASH3, 'location': 'great_hall', 'primary': True},
        ]}

    def uploads2(self):
        return {rid: {'file_path': 'api-assets/id/%s.png' % rid, 'sha256': h}
                for rid, h in (('harry-close', HASH), ('harry-full', HASH), ('draconia-close', HASH2),
                               ('draconia-full', HASH2), ('pair-wide', HASH3), ('hall', HASH3))}

    def test_close_shot_binds_close_views(self):
        refs = r2v.select_shot_references(
            shot(framing='close', visible_characters=['draconia'], location=None), self.bank2(), self.uploads2())
        self.assertEqual([r['id'] for r in refs], ['draconia-close'])

    def test_wide_two_person_shot_adds_pair_and_location(self):
        refs = r2v.select_shot_references(
            shot(framing='wide', visible_characters=['harry', 'draconia']), self.bank2(), self.uploads2())
        ids = [r['id'] for r in refs]
        self.assertEqual(ids, ['harry-full', 'draconia-full', 'pair-wide', 'hall'])

    def test_single_primary_wins_over_unmarked_duplicate(self):
        bank = self.bank2()
        bank['references'].append({'id': 'harry-close-2', 'name': 'Harry2', 'kind': 'character',
                                   'views': ['close'], 'sha256': HASH, 'characters': ['harry']})
        up = self.uploads2(); up['harry-close-2'] = {'file_path': 'api-assets/id/x.png', 'sha256': HASH}
        refs = r2v.select_shot_references(shot(framing='close', visible_characters=['harry'], location=None), bank, up)
        self.assertEqual([r['id'] for r in refs], ['harry-close'])

    def test_ambiguous_view_requires_primary(self):
        bank = self.bank2()
        bank['references'].append({'id': 'harry-close-2', 'name': 'Harry2', 'kind': 'character',
                                   'views': ['close'], 'sha256': HASH, 'characters': ['harry']})
        for r in bank['references']:
            r.pop('primary', None)
        with self.assertRaises(ValueError) as ctx:
            r2v.select_shot_references(shot(framing='close', visible_characters=['harry'], location=None), bank, self.uploads2())
        self.assertIn('ambiguous', str(ctx.exception))

    def test_framing_gap_explicit(self):
        with self.assertRaises(ValueError) as ctx:
            r2v.select_shot_references(shot(framing='back', visible_characters=['harry'], location=None),
                                       self.bank2(), self.uploads2())
        self.assertIn('explicit gap', str(ctx.exception))
