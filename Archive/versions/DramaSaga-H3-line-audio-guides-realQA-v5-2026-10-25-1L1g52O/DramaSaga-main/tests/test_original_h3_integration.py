import ast
import json
import tempfile
import unittest
from pathlib import Path

from magicdrama.audiofirst.original_h3 import EXPECTED_R2V_V1_SHA256, EXPECTED_H3_WEIGHT_METADATA, REQUIRED_H3_WEIGHTS, build_original_h3_plan, dialogue_midpoint_pins, validate_dialogue_midpoint_pin_coverage, validate_h3_weight_manifest

ROOT = Path(__file__).parents[1]
GRAPH = ROOT/'vendor/h3-film-reference/research/h3/runpod/r2v_v1.json'
REFS = ['harry-front.png','harry-speaking.png','harry-full.png','draconia-front.png','draconia-speaking.png','draconia-full.png','two-dialogue.png','two-action.png','location.png']
PINS = [
    {'seconds':0,'asset':'two-dialogue.png'},
    {'seconds':1.68,'asset':'draconia-speaking.png'},
    {'seconds':4.24,'asset':'harry-speaking.png'},
    {'seconds':6.8,'asset':'draconia-speaking.png'},
    {'seconds':8.88,'asset':'harry-speaking.png'},
    {'seconds':11.2,'asset':'two-action.png'},
]
PROMPT = 'Vertical cinematic photorealistic Yule Ball dialogue action shot with exact supplied soundtrack timing and clear active-speaker mouths.'


class OriginalH3IntegrationTests(unittest.TestCase):
    def test_audited_graph_builds_exact_audio_and_six_pins(self):
        result = build_original_h3_plan(GRAPH,prompt=PROMPT,seconds=13.12,audio_asset='dialogue.wav',reference_images=REFS,pins=PINS)
        self.assertFalse(result['live_enabled']);self.assertEqual(result['status'],'planned_not_runtime_validated')
        workflow = result['compiled']['workflow']
        self.assertEqual(workflow['136']['inputs']['width'],576);self.assertEqual(workflow['136']['inputs']['height'],1024)
        self.assertEqual(workflow['125']['inputs']['latent_image'],['md_av',0])
        self.assertEqual(workflow['md_mask']['inputs']['value'],0.0)
        self.assertEqual([workflow[f'md_pin{i}']['inputs']['frame_idx'] for i in range(6)],[0,40,102,163,213,269])
        self.assertEqual(workflow['126']['inputs']['conditioning'],['md_pin5',0])
        self.assertEqual(workflow['136']['inputs']['ref_images.ref_image_8'],['refimg9',0])
        self.assertEqual(result['compiled']['frames'],328)
        self.assertEqual(result['compiled']['padded_audio_seconds'],13.666666666666666)

    def test_reference_pin_and_graph_stress_fail_closed(self):
        base = dict(prompt=PROMPT,seconds=13.12,audio_asset='dialogue.wav',reference_images=REFS,pins=PINS)
        for refs in ([], REFS+['extra.png'], REFS[:-1]+['two-action.png']):
            with self.assertRaises(ValueError): build_original_h3_plan(GRAPH,**{**base,'reference_images':refs})
        for pins in ([], list(reversed(PINS)), [{**PINS[0],'asset':'not-staged.png'},*PINS[1:]], [*PINS[:-1],{'seconds':13.12,'asset':'two-action.png'}]):
            with self.assertRaises(ValueError): build_original_h3_plan(GRAPH,**{**base,'pins':pins})
        for seconds in (0,15.01):
            with self.assertRaises(ValueError): build_original_h3_plan(GRAPH,**{**base,'seconds':seconds})
        for size in ((832,480),(576,1000)):
            with self.assertRaises(ValueError): build_original_h3_plan(GRAPH,**{**base,'width':size[0],'height':size[1]})
        with tempfile.TemporaryDirectory() as d:
            changed = Path(d)/'graph.json';changed.write_text(json.dumps({'136':{'class_type':'MiniMaxH3ReferenceToVideo','inputs':{}}}))
            with self.assertRaisesRegex(ValueError,'requires fresh audit'): build_original_h3_plan(changed,**base)

    def test_expected_graph_hash_is_pinned(self):
        from magicdrama.audiofirst.core import digest
        self.assertEqual(digest(GRAPH),EXPECTED_R2V_V1_SHA256)

    def test_modal_download_manifest_is_minimal_and_whitelisted(self):
        modal_source = ROOT/'vendor/h3-film-reference/research/h3/modal_h3.py'
        tree = ast.parse(modal_source.read_text())
        meta = None
        weight_expr = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'WEIGHT_META' for target in node.targets):
                meta = ast.literal_eval(node.value)
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'WEIGHTS' for target in node.targets):
                weight_expr = node.value
        self.assertEqual(meta, EXPECTED_H3_WEIGHT_METADATA)
        self.assertIsInstance(weight_expr, ast.Call)
        weights = list(meta)
        self.assertEqual(validate_h3_weight_manifest(weights), REQUIRED_H3_WEIGHTS)
        self.assertEqual(len(weights), 4)
        self.assertFalse(any('bf16' in name.lower() for name in weights))

    def test_weight_manifest_rejects_unknown_or_bf16_additions(self):
        with self.assertRaisesRegex(ValueError, 'exactly'):
            validate_h3_weight_manifest([*REQUIRED_H3_WEIGHTS, 'diffusion_models/minimax_h3_ref2va_bf16.safetensors'])
        with self.assertRaisesRegex(ValueError, 'exactly'):
            validate_h3_weight_manifest(REQUIRED_H3_WEIGHTS[:-1])

    def test_boundary_pins_do_not_count_as_whole_line_speaker_coverage(self):
        lines = [
            {'id':'L1','speaker':'draconia','start':0,'end':1.68},
            {'id':'L2','speaker':'draconia','start':1.68,'end':4.24},
            {'id':'L3','speaker':'harry','start':4.24,'end':6.8},
        ]
        assets = {'draconia':'draconia-speaking.png','harry':'harry-speaking.png'}
        with self.assertRaisesRegex(ValueError, 'midpoint active-speaker pins missing'):
            validate_dialogue_midpoint_pin_coverage(PINS, lines, assets)
        midpoint_pins = dialogue_midpoint_pins(lines, assets)
        self.assertEqual([p['seconds'] for p in midpoint_pins],[.84,2.96,5.52])
        covered = sorted(PINS + midpoint_pins, key=lambda p: p['seconds'])
        result = build_original_h3_plan(
            GRAPH,prompt=PROMPT,seconds=13.12,audio_asset='dialogue.wav',reference_images=REFS,pins=covered,
            dialogue_lines=lines,speaker_pin_assets=assets)
        workflow = result['compiled']['workflow']
        self.assertEqual([workflow[f'md_pin{i}']['inputs']['frame_idx'] for i in range(9)],[0,20,40,71,102,132,163,213,269])
        self.assertEqual(len(result['dialogue_midpoint_pin_coverage']),3)

    def test_line_audio_guides_compile_and_fail_closed_on_bad_asset(self):
        lines = [{'id':'L1','speaker':'draconia','start':0,'end':1.68}]
        pins = [
            {'seconds':0,'asset':'draconia-speaking.png','audio_asset':'guide-L1-start.wav'},
            {'seconds':0.84,'asset':'draconia-speaking.png','audio_asset':'guide-L1-mid.wav'},
        ]
        result = build_original_h3_plan(
            GRAPH,prompt=PROMPT,seconds=13.12,audio_asset='dialogue.wav',reference_images=REFS,pins=pins,
            dialogue_lines=lines,speaker_pin_assets={'draconia':'draconia-speaking.png'})
        workflow = result['compiled']['workflow']
        self.assertEqual(workflow['md_pin0']['inputs']['audio'],['md_pin_audio0',0])
        self.assertEqual(workflow['md_pin1']['inputs']['audio'],['md_pin_audio1',0])
        self.assertEqual(workflow['md_pin_audio1']['inputs']['audio'],'guide-L1-mid.wav')
        for bad in ('../guide.wav','https://a.invalid/guide.wav','guide.mp3'):
            bad_pins = [{**pins[0],'audio_asset':bad},pins[1]]
            with self.assertRaisesRegex(ValueError,'Pin audio assets'):
                build_original_h3_plan(
                    GRAPH,prompt=PROMPT,seconds=13.12,audio_asset='dialogue.wav',reference_images=REFS,pins=bad_pins,
                    dialogue_lines=lines,speaker_pin_assets={'draconia':'draconia-speaking.png'})

    def test_midpoint_speaker_asset_must_be_staged(self):
        lines = [{'id':'L1','speaker':'draconia','start':0,'end':1.68}]
        with self.assertRaisesRegex(ValueError, 'staged references'):
            build_original_h3_plan(
                GRAPH,prompt=PROMPT,seconds=13.12,audio_asset='dialogue.wav',reference_images=REFS,pins=PINS,
                dialogue_lines=lines,speaker_pin_assets={'draconia':'not-staged.png'})


if __name__ == '__main__':
    unittest.main()
