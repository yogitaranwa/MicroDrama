"""Performance detailing tests. Direction validation only; no audio is synthesized
and no tag is proof of emotional delivery."""
import unittest

from magicdrama.audiofirst import detailing


def line(**overrides):
    base = {'id': 'l1', 'speaker': 'draconia', 'text': 'Potter, don\'t turn around.',
            'performance': 'urgent'}
    base.update(overrides)
    return base


class DetailingValidationTests(unittest.TestCase):
    def test_full_detailing_accepted_free_vocabulary(self):
        d = detailing.validate_detailing({
            'emotion': 'terrified but forcing control',
            'delivery': 'fast, clipped, nearly breathless',
            'emphasis': 'don\'t',
            'pause_before': 'half beat after the spark crackles',
            'pause_after': 'none, she is already moving',
            'reaction': 'Harry freezes mid-turn'}, 'l1')
        self.assertEqual(d['emotion'], 'terrified but forcing control')

    def test_missing_required_field_refused(self):
        with self.assertRaises(ValueError):
            detailing.validate_detailing({'emotion': 'scared'}, 'l1')
        with self.assertRaises(ValueError):
            detailing.validate_detailing({'delivery': 'fast'}, 'l1')

    def test_unknown_field_refused(self):
        with self.assertRaises(ValueError):
            detailing.validate_detailing({'emotion': 'scared', 'delivery': 'fast', 'vibe': 'dark'}, 'l1')

    def test_empty_optional_field_refused(self):
        with self.assertRaises(ValueError):
            detailing.validate_detailing({'emotion': 'scared', 'delivery': 'fast', 'reaction': '  '}, 'l1')


class TagMappingTests(unittest.TestCase):
    def test_verified_tags_injected(self):
        text = detailing.tagged_text(line(detailing={
            'emotion': 'urgent fear', 'delivery': 'rushed and clipped'}))
        self.assertTrue(text.startswith('[urgent] [rushed]') or text.startswith('[rushed] [urgent]'))
        self.assertTrue(text.endswith('Potter, don\'t turn around.'))

    def test_unverified_wording_not_invented_as_tag(self):
        text = detailing.tagged_text(line(detailing={
            'emotion': 'melancholic regal defiance', 'delivery': 'measured'}))
        self.assertNotIn('[', text)

    def test_tag_cap_holds(self):
        text = detailing.tagged_text(line(detailing={
            'emotion': 'angry sad nervous excited', 'delivery': 'rushed urgent'}))
        self.assertLessEqual(text.count('['), 2)

    def test_legacy_performance_field_still_works(self):
        text = detailing.tagged_text(line())
        self.assertEqual(text, 'Potter, don\'t turn around.')

    def test_missing_text_refused(self):
        with self.assertRaises(ValueError):
            detailing.tagged_text(line(text='  '))


class SettingsTests(unittest.TestCase):
    def test_documented_settings_accepted(self):
        self.assertEqual(detailing.validate_voice_settings({'stability': 0.35}), {'stability': 0.35})

    def test_undocumented_speed_field_refused(self):
        # No verified per-line speed control on text-to-dialogue (2026-10-26 docs).
        with self.assertRaises(ValueError):
            detailing.validate_voice_settings({'speed': 1.4})

    def test_out_of_range_refused(self):
        with self.assertRaises(ValueError):
            detailing.validate_voice_settings({'stability': 1.5})


class ReportTests(unittest.TestCase):
    def test_missing_detailing_is_explicit_gap(self):
        ep = {'id': 'e01', 'lines': [line(), line(id='l2', detailing={
            'emotion': 'scared', 'delivery': 'fast'})]}
        report = detailing.episode_detailing_report(ep)
        self.assertEqual(report['status'], 'gaps')
        self.assertEqual(report['missing'], ['l1'])
        self.assertEqual(report['detailed'], 1)


class VoicePlanIntegrationTests(unittest.TestCase):
    def test_dialogue_plan_uses_detailing_and_settings(self):
        import sys
        sys.path.insert(0, 'tests')
        from helpers import pilot
        from magicdrama.audiofirst import voices
        brief, story = pilot()
        ep = story['episodes'][0]
        for l in ep['lines']:
            l['detailing'] = {'emotion': 'urgent', 'delivery': 'rushed'}
        plan = voices.dialogue_plan(brief, {'episodes': [ep], **{k: v for k, v in story.items() if k != 'episodes'}},
                                    selections={'dev': 'h', 'mira': 'd'},
                                    settings={'stability': 0.4})
        body = plan['episodes'][0]['request']['body']
        self.assertEqual(body.get('settings'), {'stability': 0.4})
        self.assertTrue(all(i['voice_id'] in ('h', 'd') for i in body['inputs']))


if __name__ == '__main__':
    unittest.main()
