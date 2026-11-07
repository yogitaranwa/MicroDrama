import json
import tempfile
import unittest
import wave
from pathlib import Path

from magicdrama.audiofirst.h3film_baseline import (
    EXPECTED_COMFY_R2V_SHA256,
    EXPECTED_R2V_V1_SHA256,
    build_h3film_clip,
    compile_with_original_runner_offline,
    original_runner_command,
)
from magicdrama.audiofirst.core import digest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'vendor/h3-film-reference/research/h3/runpod/comfy_r2v.py'
GRAPH = ROOT / 'vendor/h3-film-reference/research/h3/runpod/r2v_v1.json'


def wav(path: Path, seconds: float = 0.5) -> None:
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b'\0\0' * int(16000 * seconds))


class H3FilmBaselineTests(unittest.TestCase):
    def test_authoritative_source_hashes_are_pinned(self):
        self.assertEqual(digest(RUNNER), EXPECTED_COMFY_R2V_SHA256)
        self.assertEqual(digest(GRAPH), EXPECTED_R2V_V1_SHA256)

    def test_clip_schema_and_command_use_original_runner(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            prompt = root / 'prompt.txt'; prompt.write_text('Image 1 is the speaker. Perform the supplied soundtrack.')
            image = root / 'speaker.png'; image.write_bytes(b'\x89PNG\r\n\x1a\n')
            audio = root / 'dialogue.wav'; wav(audio)
            clip = build_h3film_clip(
                clip_id='baseline-test', prompt_path=prompt, seconds=0.5,
                image_paths=[image], audio_path=audio)
            self.assertEqual(clip['prompt'], str(prompt))
            self.assertEqual(clip['images'], [str(image)])
            self.assertEqual(clip['audio'], str(audio))
            self.assertNotIn('pins', clip)
            command = original_runner_command(
                clip_path=root / 'clip.json', output_path=root / 'out.mp4', seed=123)
            self.assertIn('--audio=inpaint', command)
            self.assertIn('--rows=576', command)
            self.assertIn('--ratio=9:16', command)
            self.assertIn('--seed=123', command)
            self.assertEqual(command[1], str(RUNNER))

    def test_exact_runner_dry_run_compiles_baseline_without_modal_or_guides(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            prompt = root / 'prompt.txt'; prompt.write_text(
                'Image 1 is the speaker. Perform the supplied soundtrack without inventing dialogue.')
            image = root / 'speaker.png'; image.write_bytes(b'\x89PNG\r\n\x1a\n')
            audio = root / 'dialogue.wav'; wav(audio, 0.5)
            clip = build_h3film_clip(
                clip_id='baseline-test', prompt_path=prompt, seconds=0.5,
                image_paths=[image], audio_path=audio)
            runner_before = digest(RUNNER)
            result = compile_with_original_runner_offline(
                clip=clip, rows=576, ratio='9:16', audio_mode='inpaint', seed=123,
                scratch_dir=root / 'scratch')
            self.assertEqual(digest(RUNNER), runner_before)
            g = result.graph
            self.assertEqual(result.runner_sha256, EXPECTED_COMFY_R2V_SHA256)
            self.assertEqual(len(g), 27)
            self.assertNotIn('MiniMaxH3AddGuide', {v.get('class_type') for v in g.values()})
            self.assertEqual(g['136']['inputs']['ref_image_size'], 'match')
            self.assertEqual(g['136']['inputs']['ref_audios.ref_audio_0'], ['aud1', 0])
            self.assertEqual(g['136']['inputs']['ref_images.ref_image_0'], ['img1', 0])
            self.assertEqual(g['151']['inputs']['value'], 576)
            self.assertEqual(g['152']['inputs']['value'], 1024)
            self.assertEqual(g['129']['inputs']['noise_seed'], 123)
            self.assertEqual(g['123']['inputs']['sampler_name'], 'res_multistep')
            self.assertEqual(g['124']['inputs']['scheduler'], 'simple')
            self.assertEqual(g['124']['inputs']['steps'], 25)
            self.assertEqual(g['124']['inputs']['denoise'], 1)
            self.assertEqual(g['125']['inputs']['latent_image'], ['av', 0])
            self.assertEqual(g['126']['inputs']['conditioning'], ['136', 0])
            self.assertEqual(g['amask']['inputs']['value'], 0.0)
            self.assertEqual(len(result.files_manifest), 2)
            self.assertEqual((root / 'scratch/baseline-test.dry-run.mp4').stat().st_size, 0)
            self.assertTrue(any(name.endswith('-speaker.png') for name in result.files_manifest))
            self.assertTrue(any('fit0.5s-' in name and name.endswith('.wav') for name in result.files_manifest))
            self.assertNotEqual(result.workflow_sha256, '')


    def test_nine_reference_harry_baseline_shape_matches_original_runner(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            prompt = root / 'prompt.txt'; prompt.write_text(
                'Images 1-9 lock the cast, wardrobe and location. Perform the supplied soundtrack.')
            images = []
            for i in range(9):
                image = root / f'ref{i}.png'; image.write_bytes(b'\x89PNG\r\n\x1a\n' + bytes([i]))
                images.append(image)
            audio = root / 'dialogue.wav'; wav(audio, 13.12)
            clip = build_h3film_clip(
                clip_id='baseline-9-ref-test', prompt_path=prompt, seconds=13.12,
                image_paths=images, audio_path=audio)
            result = compile_with_original_runner_offline(
                clip=clip, rows=576, ratio='9:16', audio_mode='inpaint', seed=419433329744414,
                scratch_dir=root / 'scratch')
            g = result.graph
            self.assertEqual(len(g), 35)
            self.assertEqual(sum(v.get('class_type') == 'LoadImage' for v in g.values()), 9)
            self.assertEqual(sum(v.get('class_type') == 'LoadAudio' for v in g.values()), 1)
            self.assertEqual(sum(v.get('class_type') == 'MiniMaxH3AddGuide' for v in g.values()), 0)
            self.assertEqual(g['136']['inputs']['ref_audios.ref_audio_0'], ['aud1', 0])
            self.assertEqual(g['136']['inputs']['ref_image_size'], 'match')
            self.assertEqual(g['129']['inputs']['noise_seed'], 419433329744414)

    def test_baseline_rejects_missing_or_excess_inputs_before_compiling(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            prompt = root / 'prompt.txt'; prompt.write_text('prompt')
            image = root / 'speaker.png'; image.write_bytes(b'\x89PNG\r\n\x1a\n')
            audio = root / 'dialogue.wav'; wav(audio)
            with self.assertRaisesRegex(ValueError, 'reference image'):
                build_h3film_clip(
                    clip_id='x', prompt_path=prompt, seconds=1,
                    image_paths=[root / 'missing.png'], audio_path=audio)
            with self.assertRaisesRegex(ValueError, '1-9'):
                build_h3film_clip(
                    clip_id='x', prompt_path=prompt, seconds=1,
                    image_paths=[image] * 10, audio_path=audio)
            with self.assertRaisesRegex(ValueError, 'clip seconds'):
                build_h3film_clip(
                    clip_id='x', prompt_path=prompt, seconds=0,
                    image_paths=[image], audio_path=audio)


if __name__ == '__main__':
    unittest.main()
