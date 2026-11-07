"""Production state machine from an approved studio script, with a fake provider: nothing is spent and no media is made."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from magicdrama.audiofirst.produce import Blocked, Producer, accept_frame, reject_frame, status
from magicdrama.audiofirst.studio import ScriptedLLM, approve, draft
from tests.test_studio import BRIEF, PACK


class FakeRunner:
    def __init__(self):
        self.calls = []

    def image(self, ident, prompt, refs, output):
        self.calls.append(('image', ident, [Path(r).name for r in refs]))
        Image.new('RGB', (32, 18), (len(self.calls) * 7 % 255, 40, 90)).save(output)

    def video(self, ident, prompt, frame, seconds, model, output, evidence):
        self.calls.append(('video', ident, model, evidence['accepted']['frame-' + ident.split('-t')[0]]['reviewer']))
        Path(output).write_bytes(b'fake mp4 ' + ident.encode())

    def music(self, ident, seconds, prompt, output):
        self.calls.append(('music', ident, seconds))
        Path(output).write_bytes(b'fake mp3')


def fake_extract(video, output):
    Image.new('RGB', (32, 18), (200, 100, len(Path(video).name))).save(output)


def make_gate(fail=()):
    def gate(video, lines):
        stem = Path(video).stem
        if stem in fail:
            return {'kind': 'dialogue' if lines else 'silent', 'wer': 1.0, 'extra_words': 3, 'heard': 'wrong words', 'expected': ' '.join(lines), 'pass': False}
        return {'kind': 'dialogue' if lines else 'silent', 'wer': 0.0, 'extra_words': 0, 'heard': ' '.join(lines), 'expected': ' '.join(lines), 'pass': True}
    return gate


def approved_dir(pack=PACK):
    d = tempfile.mkdtemp()
    r = draft(BRIEF, ScriptedLLM([pack]), d)
    approve(d, r['quote']['total_credits'] + 1000)
    return d


def run_all(d, runner, gate=None, allow=(), assembled=None):
    def asm(prod, muted):
        (prod.film()).write_bytes(b'film')
        if assembled is not None:assembled.extend(muted)
    prod = Producer(d, runner, gate=gate or make_gate(), extract=fake_extract, assemble=asm, allow_rerender=allow)
    while True:
        a = prod.run()
        if a['action'] == 'review':
            accept_frame(d, a['shot'], 'tester')
            continue
        return prod, a


class ProductionTests(unittest.TestCase):
    def test_a_script_that_was_not_approved_or_was_edited_cannot_be_produced(self):
        d = tempfile.mkdtemp()
        draft(BRIEF, ScriptedLLM([PACK]), d)
        with self.assertRaisesRegex(ValueError, 'not approved yet'):Producer(d, FakeRunner())
        approve(d, 99999)
        story = json.loads((Path(d) / 'story.json').read_text(encoding='utf-8'))
        story['title'] = 'Edited'
        (Path(d) / 'story.json').write_text(json.dumps(story), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'changed after it was approved'):Producer(d, FakeRunner())

    def test_it_stops_at_the_first_start_frame_and_pays_for_no_video_before_a_review(self):
        d, runner = approved_dir(), FakeRunner()
        prod = Producer(d, runner, gate=make_gate(), extract=fake_extract)
        a = prod.run()
        self.assertEqual(a['action'], 'review')
        self.assertEqual([c[0] for c in runner.calls].count('video'), 0)
        self.assertEqual([c[0] for c in runner.calls].count('image'), 3 + 1)  # plate, two portraits, the first start frame
        self.assertIn('room-plate.png', runner.calls[-1][2])

    def test_the_whole_film_runs_with_a_review_per_frame_and_each_video_carries_its_reviewer(self):
        d, runner = approved_dir(), FakeRunner()
        prod, last = run_all(d, runner)
        self.assertEqual(last['action'], 'done')
        kinds = [c[0] for c in runner.calls]
        self.assertEqual(kinds.count('video'), 12)
        self.assertEqual(kinds.count('music'), 1)
        self.assertTrue(all(c[3] == 'tester' for c in runner.calls if c[0] == 'video'))
        self.assertTrue(all(r['gate'] == 'pass' for r in status(d)))

    def test_a_resumed_run_does_not_pay_twice(self):
        d, runner = approved_dir(), FakeRunner()
        run_all(d, runner)
        n = len(runner.calls)
        prod, last = run_all(d, runner)
        self.assertEqual((last['action'], len(runner.calls)), ('done', n))

    def test_a_dialogue_shot_that_fails_its_speech_check_stops_the_run_until_a_rerender_is_authorised(self):
        d, runner = approved_dir(), FakeRunner()
        story = json.loads((Path(d) / 'story.json').read_text(encoding='utf-8'))
        bad = next(s['id'] for s in story['shots'] if s['sound']['dialogue'])
        prod, last = run_all(d, runner, gate=make_gate(fail={bad}))
        self.assertEqual((last['action'], last['shot']), ('blocked', bad))
        self.assertIn('--allow-rerender ' + bad, last['why'])
        before = [c[0] for c in runner.calls].count('video')
        prod, last = run_all(d, runner, gate=make_gate(fail={bad}))   # still refused: nothing re-rendered without authorisation
        self.assertEqual([c[0] for c in runner.calls].count('video'), before)
        prod, last = run_all(d, runner, gate=make_gate(), allow=[bad])  # authorised once, and this take passes
        self.assertEqual(last['action'], 'done')
        self.assertTrue(any(c[0] == 'video' and c[1].startswith(bad + '-t') for c in runner.calls))
        self.assertTrue(list((Path(d) / 'clips').glob(bad + '-take1.mp4')))

    def test_one_authorisation_buys_one_rerender_only(self):
        d, runner = approved_dir(), FakeRunner()
        story = json.loads((Path(d) / 'story.json').read_text(encoding='utf-8'))
        bad = next(s['id'] for s in story['shots'] if s['sound']['dialogue'])
        prod, last = run_all(d, runner, gate=make_gate(fail={bad}), allow=[bad])
        self.assertEqual(last['action'], 'blocked')  # the re-take failed too (same gate), and a second paid take was not made
        self.assertEqual(len([c for c in runner.calls if c[0] == 'video' and c[1].split('-t')[0] == bad]), 2)

    def test_invented_speech_in_a_silent_shot_does_not_stop_the_run_but_is_muted_in_assembly(self):
        d, runner, muted = approved_dir(), FakeRunner(), []
        story = json.loads((Path(d) / 'story.json').read_text(encoding='utf-8'))
        silent = next(s['id'] for s in story['shots'] if not s['sound']['dialogue'])
        prod, last = run_all(d, runner, gate=make_gate(fail={silent}), assembled=muted)
        self.assertEqual(last['action'], 'done')
        self.assertEqual(muted, [silent])

    def test_a_frame_edited_after_review_is_refused(self):
        d, runner = approved_dir(), FakeRunner()
        prod = Producer(d, runner, gate=make_gate(), extract=fake_extract)
        a = prod.run()
        accept_frame(d, a['shot'], 'tester')
        Image.new('RGB', (32, 18), (1, 2, 3)).save(prod.frame(a['shot']))
        self.assertEqual(prod.run()['action'], 'blocked')
        self.assertEqual([c[0] for c in runner.calls].count('video'), 0)

    def test_review_needs_a_name_and_every_check(self):
        d, runner = approved_dir(), FakeRunner()
        prod = Producer(d, runner, gate=make_gate(), extract=fake_extract)
        a = prod.run()
        with self.assertRaisesRegex(ValueError, 'reviewer name'):accept_frame(d, a['shot'], ' ')
        with self.assertRaisesRegex(ValueError, 'failed check'):accept_frame(d, a['shot'], 'x', checks={'identity': False})
        reject_frame(d, a['shot'])
        self.assertFalse(prod.frame(a['shot']).exists())
        self.assertTrue(list(prod.frame(a['shot']).parent.glob(a['shot'] + '.rejected1.png')))
        prod.run()
        self.assertEqual(runner.calls[-1][1], 'frame-' + a['shot'] + '-v2')  # regenerated under a new job id

    def test_same_angle_same_people_reuses_the_previous_last_frame_without_an_image_job(self):
        p = copy.deepcopy(PACK)
        p['beats'][4]['speaker'] = 'Ines'  # Ines speaks twice in a row from the same angle
        p['beats'][4]['doing'] = {'Ines': 'warming her hands on the oven door'}
        d, runner = approved_dir(p), FakeRunner()
        prod, last = run_all(d, runner)
        self.assertEqual(last['action'], 'done')
        story = json.loads((Path(d) / 'story.json').read_text(encoding='utf-8'))
        modes = {x['id']: x['mode'] for x in __import__('magicdrama.audiofirst.directed', fromlist=['x']).first_frame_plan(story)}
        cont = [k for k, v in modes.items() if v == 'continue']
        self.assertTrue(cont)
        for sid in cont:
            self.assertFalse(any(c[0] == 'image' and c[1] == 'frame-' + sid for c in runner.calls))

    def test_later_frames_are_built_from_the_previous_real_last_frame(self):
        d, runner = approved_dir(), FakeRunner()
        run_all(d, runner)
        frames = [c for c in runner.calls if c[0] == 'image' and c[1].startswith('frame-')]
        self.assertTrue(any(any(n.endswith('-last.png') for n in c[2]) for c in frames[1:]))


if __name__ == '__main__':
    unittest.main()
