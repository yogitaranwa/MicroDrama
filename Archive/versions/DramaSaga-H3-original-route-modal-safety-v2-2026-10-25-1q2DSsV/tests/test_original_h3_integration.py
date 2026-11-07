import ast
import json
import tempfile
import unittest
from pathlib import Path

from magicdrama.audiofirst.original_h3 import EXPECTED_R2V_V1_SHA256, EXPECTED_H3_WEIGHT_METADATA, REQUIRED_H3_WEIGHTS, build_original_h3_plan, validate_h3_weight_manifest

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


if __name__ == '__main__':
    unittest.main()
