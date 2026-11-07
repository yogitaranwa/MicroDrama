"""Studio: brief -> LLM draft -> repair loop -> compiled, validated, priced review pack. The LLM is scripted; no network, no credits."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from magicdrama.audiofirst.directed import directed_prompt, validate_directed
from magicdrama.audiofirst.studio import (shorten_long_lines, snap_insert_subjects, normalise_pack, OllamaLLM, ScriptedLLM, approve, check_approval, check_brief, check_pack, compile_story, draft, draft_pack,
                                          parse_json, shots_wanted)

BRIEF = {'idea': 'A baker working through the night is visited by the brother she has not spoken to for years.', 'environment': '', 'characters': 2, 'seconds': 48,
         'tone': 'quiet, naturalistic drama'}


def _dlg(sp, line, doing, emotion='quietly'):
    return {'type': 'dialogue', 'speaker': sp, 'line': line, 'doing': {sp: doing}, 'emotion': emotion}


PACK = {
    'title': 'Proving Time', 'logline': 'A baker kneading at 3 a.m. is visited by the brother she has not spoken to for six years.',
    'hook_title': 'At 3 a.m. he came back...', 'end_card': 'Some bread takes years to rise.',
    'characters': [{'name': 'Ines', 'look': 'a woman in her early thirties with dark hair under a bandana', 'wardrobe': 'white apron over a grey t-shirt, rolled sleeves', 'voice': 'low, warm woman, tired, speaking softly'},
                   {'name': 'Omar', 'look': 'a man in his mid thirties, short beard, tired eyes', 'wardrobe': 'dark green parka over a navy sweater', 'voice': 'quiet, hoarse man, careful, slow'}],
    'environment': {'name': 'night bakery', 'description': 'A small bakery kitchen at 3 a.m.: tiled walls, a flour-dusted steel counter in the middle, warm light.',
                    'lighting': 'warm overhead light with cool blue night light from the shop window',
                    'features': [{'name': 'bread oven', 'wall': 'west', 'position': 'centre', 'kind': 'appliance', 'colour': '#b8b8c0'},
                                 {'name': 'rack of loaves', 'wall': 'west', 'position': 'right', 'kind': 'shelf', 'colour': '#8a7a60'},
                                 {'name': 'shop window', 'wall': 'east', 'position': 'centre', 'kind': 'window', 'colour': '#5f7fa8'},
                                 {'name': 'chalkboard menu', 'wall': 'east', 'position': 'right', 'kind': 'sign', 'colour': '#222222'},
                                 {'name': 'back door', 'wall': 'south', 'position': 'left', 'kind': 'door', 'colour': '#7a5a3a'},
                                 {'name': 'dough mixer', 'wall': 'north', 'position': 'centre', 'kind': 'machine', 'colour': '#d0d0d0'}],
                    'center_piece': {'name': 'flour-dusted steel counter', 'kind': 'furniture', 'colour': '#a0a0a8'}},
    'beats': [
        {'type': 'wide', 'text': 'The bakery at night: Ines kneads dough on the steel counter under the warm light.', 'doing': {'Ines': 'kneading a big round of dough'}},
        {'type': 'insert', 'subject': 'dough mixer', 'text': 'The mixer arm turns a slow lump of dough.'},
        {'type': 'entrance', 'who': 'Omar', 'from': 'the back door', 'why': 'he saw the light on and could not stay away', 'then': 'he brushes the snow off his parka and looks at the loaves'},
        _dlg('Ines', 'You still know where the key is.', 'shaping a loaf with floured hands', 'startled, then guarded'),
        _dlg('Omar', 'Under the third brick. Like always.', 'warming his hands on the oven door', 'gentle, nervous'),
        {'type': 'insert', 'subject': 'rack of loaves', 'text': 'Loaves cooling on the rack, steam rising.'},
        _dlg('Ines', 'Six years, Omar.', 'slapping the dough down on the counter', 'hurt, quiet'),
        _dlg('Omar', 'I know. I brought Dad\'s starter.', 'unwrapping a jar from his parka', 'careful, hopeful'),
        {'type': 'insert', 'subject': 'center_piece', 'text': 'The jar of old starter set down in the flour.'},
        _dlg('Ines', 'It survived him better than we did.', 'wiping flour from her hands', 'dry, aching'),
        _dlg('Omar', 'Teach me again how to feed it.', 'rolling up his sleeves', 'soft, pleading'),
        {'type': 'wide', 'text': 'They stand side by side at the counter, the jar between them, the night outside the window.', 'doing': {'Ines': 'measuring flour into a bowl', 'Omar': 'stirring the starter'}},
    ]}


class BriefTests(unittest.TestCase):
    def test_a_good_brief_is_normalised(self):
        b = check_brief(BRIEF)
        self.assertEqual((b['characters'], b['seconds'], shots_wanted(b)), (2, 48, 12))

    def test_bad_briefs_are_refused_with_reasons(self):
        for bad, text in (({**BRIEF, 'idea': ' '}, 'idea'), ({**BRIEF, 'characters': 3}, 'exactly 2'), ({**BRIEF, 'seconds': 5}, 'between 20 and 120')):
            with self.assertRaisesRegex(ValueError, text):check_brief(bad)


class PackCheckTests(unittest.TestCase):
    def setUp(self):
        self.brief = check_brief(BRIEF)

    def test_the_example_pack_is_valid(self):
        self.assertEqual(check_pack(PACK, self.brief), [])

    def test_the_pack_checker_catches_what_weak_models_get_wrong(self):
        cases = [(lambda p: p['beats'][3].__setitem__('line', 'one two three four five six seven eight nine ten'), 'at most 9'),
                 (lambda p: p['beats'][3].__setitem__('line', 'Wait... what'), 'no ellipses'),
                 (lambda p: p['beats'][3]['doing'].__setitem__('Ines', 'standing there'), 'not a task'),
                 (lambda p: p['beats'][3].__setitem__('speaker', 'Nobody'), 'speaker must be'),
                 (lambda p: p['beats'][1].__setitem__('subject', 'the moon'), 'insert subject'),
                 (lambda p: p['environment']['features'][0].__setitem__('wall', 'ceiling'), 'wall must be'),
                 (lambda p: p['beats'].pop(), 'were asked for'),
                 (lambda p: p['beats'][2].pop('why'), 'entrance needs why')]
        for mutate, text in cases:
            p = copy.deepcopy(PACK)
            mutate(p)
            if 'were asked for' in text:p['beats'] = p['beats'][:8]
            self.assertTrue(any(text in x for x in check_pack(p, self.brief)), (text, check_pack(p, self.brief)))

    def test_json_in_chatter_and_code_fences_is_found(self):
        self.assertEqual(parse_json('Sure! ```json\n{"a": 1}\n``` hope it helps'), {'a': 1})
        with self.assertRaises(ValueError):parse_json('no json here')


class NormaliseTests(unittest.TestCase):
    def test_mechanical_slips_are_fixed_before_checking(self):
        p = copy.deepcopy(PACK)
        p['environment']['features'][0]['kind'] = 'Desk'
        p['environment']['features'][1]['kind'] = 'lamp'
        p['environment']['features'][2]['wall'] = 'EAST'
        p['beats'][3]['line'] = 'Wait... you came back'
        normalise_pack(p)
        self.assertEqual((p['environment']['features'][0]['kind'], p['environment']['features'][1]['kind'], p['environment']['features'][2]['wall']), ('appliance', 'shelf', 'east'))  # mapped from the feature's name: a bread oven, a rack of loaves
        self.assertEqual(p['beats'][3]['line'], 'Wait. you came back')
        self.assertEqual(check_pack(p, check_brief(BRIEF)), [])


class MicroRepairTests(unittest.TestCase):
    def test_a_made_up_insert_subject_snaps_to_a_real_feature_or_the_centre_piece(self):
        p = copy.deepcopy(PACK)
        p['beats'][1]['subject'] = 'old dough mixer arm'
        p['beats'][5]['subject'] = 'the moon'
        snap_insert_subjects(p)
        self.assertEqual((p['beats'][1]['subject'], p['beats'][5]['subject']), ('dough mixer', 'center_piece'))
        self.assertEqual(check_pack(p, check_brief(BRIEF)), [])

    def test_an_overlong_line_is_rewritten_by_a_small_focused_request(self):
        p = copy.deepcopy(PACK)
        p['beats'][3]['line'] = 'Yes but the lighthouse needs to move with the times now'
        llm = ScriptedLLM([{'line': 'The lighthouse must move with the times.'}])
        shorten_long_lines(p, llm)
        self.assertEqual(p['beats'][3]['line'], 'The lighthouse must move with the times.')
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(check_pack(p, check_brief(BRIEF)), [])

    def test_a_rewrite_that_is_still_too_long_is_retried_once_then_left_for_the_repair_loop(self):
        p = copy.deepcopy(PACK)
        long = 'one two three four five six seven eight nine ten eleven'
        p['beats'][3]['line'] = long
        llm = ScriptedLLM([{'line': long}, 'not json at all'])
        shorten_long_lines(p, llm)
        self.assertEqual(len(llm.calls), 2)
        self.assertTrue(any('at most 9' in x for x in check_pack(p, check_brief(BRIEF))))


class DraftLoopTests(unittest.TestCase):
    def test_the_llm_is_shown_the_problems_and_repairs_its_answer(self):
        bad = copy.deepcopy(PACK)
        bad['beats'][3]['doing']['Ines'] = 'waiting'
        llm = ScriptedLLM([bad, PACK])
        pack, history = draft_pack(BRIEF, llm)
        self.assertEqual(pack['title'], 'Proving Time')
        self.assertEqual([len(h['problems']) > 0 for h in history], [True, False])
        self.assertIn('not a task', llm.calls[1][1])

    def test_it_gives_up_after_the_repair_budget_with_the_last_problems(self):
        bad = copy.deepcopy(PACK)
        bad['beats'][3]['doing']['Ines'] = 'waiting'
        with self.assertRaisesRegex(ValueError, 'could not produce a valid story pack'):draft_pack(BRIEF, ScriptedLLM([bad] * 3), max_repairs=2)

    def test_the_request_asks_for_an_invented_room_only_when_none_was_given(self):
        llm = ScriptedLLM([PACK])
        draft_pack(BRIEF, llm)
        self.assertIn('invent one small closed room', llm.calls[0][1])
        llm = ScriptedLLM([PACK])
        draft_pack({**BRIEF, 'environment': 'a lighthouse kitchen'}, llm)
        self.assertIn('a lighthouse kitchen', llm.calls[0][1])


class CompileTests(unittest.TestCase):
    def setUp(self):
        self.brief = check_brief(BRIEF)
        self.story = compile_story(PACK, self.brief)

    def test_the_compiled_story_passes_every_pipeline_check(self):
        self.assertTrue(validate_directed(self.story))
        self.assertEqual(len(self.story['shots']), 12)

    def test_speakers_are_framed_from_the_side_that_puts_the_right_wall_behind_them(self):
        ines = next(s for s in self.story['shots'] if s['cast'] == ['Ines'] and s['sound']['dialogue'])
        omar = next(s for s in self.story['shots'] if s['cast'] == ['Omar'] and s['sound']['dialogue'])
        self.assertIn('west wall', directed_prompt(self.story, self.story['shots'].index(ines)).lower() + self.story['bible']['geography'].lower())
        self.assertNotEqual(self.story['plan']['shots'][ines['id']]['camera']['start']['pos'], self.story['plan']['shots'][omar['id']]['camera']['start']['pos'])

    def test_everyone_has_a_task_and_the_entrance_has_a_reason(self):
        ent = next(s for s in self.story['shots'] if 'arrival' in s)
        self.assertEqual(ent['arrival']['Omar']['why'], 'he saw the light on and could not stay away')
        self.assertTrue(all(s['activity'].get(n) for s in self.story['shots'] for n in s['cast']))

    def test_same_person_same_angle_resumes_from_their_last_frame(self):
        from magicdrama.audiofirst.directed import first_frame_plan
        plan = {p['id']: p for p in first_frame_plan(self.story)}
        ines = [s['id'] for s in self.story['shots'] if s['cast'] == ['Ines'] and s['sound']['dialogue']]
        self.assertEqual(plan[ines[1]]['mode'], 'resume')
        self.assertEqual(plan[ines[1]]['from_shot'], ines[0])


class ReviewAndApprovalTests(unittest.TestCase):
    def test_draft_writes_the_review_pack_and_the_price(self):
        with tempfile.TemporaryDirectory() as d:
            r = draft(BRIEF, ScriptedLLM([PACK]), d)
            for name in ('REVIEW.md', 'story.json', 'pack.json', 'quote.json', 'draft-history.json', 'views/floor-plan.png'):
                self.assertTrue((Path(d) / name).exists(), name)
            text = (Path(d) / 'REVIEW.md').read_text(encoding='utf-8')
            for needle in ('Proving Time', 'You still know where the key is.', 'First-frame chain', 'room-plate', 'ines-master', 'Price'):
                self.assertIn(needle, text)
            self.assertEqual(r['quote']['video_credits'], 12 * 288)
            self.assertEqual(r['repairs'], 0)

    def test_approval_is_bound_to_the_exact_script_and_cap(self):
        with tempfile.TemporaryDirectory() as d:
            r = draft(BRIEF, ScriptedLLM([PACK]), d)
            with self.assertRaisesRegex(ValueError, 'below the quote'):approve(d, 100)
            rec = approve(d, r['quote']['total_credits'] + 500)
            self.assertEqual(check_approval(d)['story_sha256'], rec['story_sha256'])
            story = json.loads((Path(d) / 'story.json').read_text(encoding='utf-8'))
            story['title'] = 'Changed'
            (Path(d) / 'story.json').write_text(json.dumps(story), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'changed after it was approved'):check_approval(d)


class OllamaTests(unittest.TestCase):
    def test_the_request_to_ollama_is_a_json_mode_chat(self):
        sent = {}

        class Http:
            def post(self, url, json=None, timeout=None):
                sent.update(url=url, body=json)
                return type('R', (), {'raise_for_status': lambda s: None, 'json': lambda s: {'message': {'content': '{"ok": true}'}}})()

            def get(self, url, timeout=None):
                return type('R', (), {'raise_for_status': lambda s: None, 'json': lambda s: {'models': [{'name': 'qwen2.5:7b'}]}})()

        llm = OllamaLLM('qwen2.5:7b', http=Http())
        self.assertEqual(llm.chat('sys', 'user'), '{"ok": true}')
        self.assertEqual((sent['url'], sent['body']['format'], sent['body']['stream']), ('http://127.0.0.1:11434/api/chat', 'json', False))
        self.assertEqual(llm.installed(), ['qwen2.5:7b'])


if __name__ == '__main__':
    unittest.main()
