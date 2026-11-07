"""Audited original H3Film Comfy graph planner.

Builds the exact-audio/timed-pin workflow without submitting it. Execution remains
outside this module and requires separately verified compute and spend authority.
"""
from __future__ import annotations

import json
from pathlib import Path

from .core import digest, finite
from .h3_local import compile_workflow

EXPECTED_R2V_V1_SHA256 = '1d927b51d05405fa0d2683593822882c7cf8a6d5f9742817863338e7efe069a3'

EXPECTED_H3_WEIGHT_METADATA = {
    'diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors': (20970379616, '9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779'),
    'text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors': (15687142551, '35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6'),
    'vae/minimax_h3_video_vae_fp16.safetensors': (5207808496, '7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522'),
    'vae/minimax_h3_audio_vae_fp32.safetensors': (605254808, '8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48'),
}
REQUIRED_H3_WEIGHTS = tuple(EXPECTED_H3_WEIGHT_METADATA)


def validate_h3_weight_manifest(weights: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Fail closed on non-minimal or unknown H3 weight downloads.

    The corrective route uses the pruned int8 diffusion checkpoint. The full
    BF16 checkpoint is intentionally excluded so setup cannot silently pull an
    extra 61GB into persistent storage.
    """
    values = tuple(weights)
    if values != REQUIRED_H3_WEIGHTS:
        raise ValueError(f'H3 weight manifest must be exactly {REQUIRED_H3_WEIGHTS}; got {values}')
    forbidden = [x for x in values if 'bf16' in x.lower()]
    if forbidden:
        raise ValueError(f'BF16 H3 weights are not part of the corrective manifest: {forbidden}')
    return values


def dialogue_midpoint_pins(dialogue_lines: list[dict], speaker_pin_assets: dict[str, str]) -> list[dict]:
    """Return one active-speaker guide pin at every dialogue-line midpoint.

    MiniMaxH3AddGuide anchors a frame position; it has no strength input and does
    not own the rest of the line. Boundary-only pins therefore cannot guarantee
    the active speaker stays framed through the spoken line.
    """
    if not dialogue_lines or not speaker_pin_assets:
        raise ValueError('Dialogue lines and speaker pin assets are required')
    pins = []
    previous_end = -1.0
    for i, line in enumerate(dialogue_lines, 1):
        speaker = line.get('speaker')
        if speaker not in speaker_pin_assets:
            raise ValueError(f'No active-speaker pin asset for dialogue speaker {speaker!r}')
        start = finite(line.get('start'), 'dialogue line start', 0.0)
        end = finite(line.get('end'), 'dialogue line end', 0.0)
        if not start < end or start < previous_end:
            raise ValueError('Dialogue lines must be strictly ordered with positive duration')
        previous_end = end
        midpoint = (start + end) / 2
        pins.append({
            'seconds': midpoint,
            'asset': speaker_pin_assets[speaker],
            'line_id': line.get('id', f'line-{i}'),
            'speaker': speaker,
            'role': 'dialogue_midpoint',
        })
    return pins


def validate_dialogue_midpoint_pin_coverage(
    pins: list[dict],
    dialogue_lines: list[dict],
    speaker_pin_assets: dict[str, str],
    *,
    tolerance_seconds: float = 0.08,
) -> list[dict]:
    """Fail closed unless every dialogue line has its speaker pinned at midpoint."""
    required = dialogue_midpoint_pins(dialogue_lines, speaker_pin_assets)
    tolerance = finite(tolerance_seconds, 'pin tolerance', 0.001)
    missing = []
    for want in required:
        t = want['seconds']
        asset = want['asset']
        matches = [p for p in pins if abs(float(p.get('seconds', -999)) - t) <= tolerance and p.get('asset') == asset]
        if not matches:
            missing.append({
                'line_id': want['line_id'],
                'speaker': want['speaker'],
                'midpoint_seconds': round(t, 4),
                'required_asset': asset,
            })
    if missing:
        raise ValueError('Dialogue midpoint active-speaker pins missing: ' + json.dumps(missing, sort_keys=True))
    return required


BINDINGS = {
    'positive': '136', 'video_latent': '136', 'video_latent_output': 1,
    'audio_vae': '120', 'video_vae': '119', 'sampler': '125', 'guider': '126',
    'frame_count_node': '136',
}


def load_audited_graph(path: str | Path) -> dict:
    p = Path(path)
    data = json.loads(p.read_text())
    actual = digest(p)
    if actual != EXPECTED_R2V_V1_SHA256:
        raise ValueError(f'Original H3 graph changed: {actual}; requires fresh audit')
    if data.get('136', {}).get('class_type') != 'MiniMaxH3ReferenceToVideo':
        raise ValueError('Audited H3 reference node missing')
    return data


def build_original_h3_plan(
    graph_path: str | Path,
    *,
    prompt: str,
    seconds: float,
    audio_asset: str,
    reference_images: list[str],
    pins: list[dict],
    width: int = 576,
    height: int = 1024,
    dialogue_lines: list[dict] | None = None,
    speaker_pin_assets: dict[str, str] | None = None,
) -> dict:
    """Build a compiled, hash-bound workflow plan without runtime submission."""
    graph = load_audited_graph(graph_path)
    if not isinstance(prompt, str) or len(prompt.strip()) < 40:
        raise ValueError('Specific original-H3 prompt required')
    seconds = finite(seconds, 'clip seconds', 0.01)
    if seconds > 15:
        raise ValueError('Conservative original-H3 clip cap 15 seconds')
    if (width, height) != (576, 1024):
        raise ValueError('Corrective route is pinned to audited 9:16 576x1024')
    if not isinstance(audio_asset, str) or '/' in audio_asset or '\\' in audio_asset or not audio_asset.endswith('.wav'):
        raise ValueError('Staged local WAV asset name required')
    if not 1 <= len(reference_images) <= 9:
        raise ValueError('Original H3 reference mode requires 1-9 images')
    if len(set(reference_images)) != len(reference_images) or any('/' in x or '\\' in x or not x.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) for x in reference_images):
        raise ValueError('Reference images must be unique staged local image names')
    if not pins:
        raise ValueError('Timed pins are required for dialogue/action timing')
    if (dialogue_lines is None) != (speaker_pin_assets is None):
        raise ValueError('Dialogue lines and speaker pin assets must be supplied together')
    if speaker_pin_assets:
        unknown_assets = set(speaker_pin_assets.values()) - set(reference_images)
        if unknown_assets:
            raise ValueError(f'Speaker pin assets must be staged references: {sorted(unknown_assets)}')
    graph['138']['inputs']['value'] = prompt
    ref = graph['136']['inputs']
    ref['ref_image_size'] = 'max'
    for i, name in enumerate(reference_images, 1):
        node = f'refimg{i}'
        graph[node] = {'class_type': 'LoadImage', 'inputs': {'image': name}}
        ref[f'ref_images.ref_image_{i - 1}'] = [node, 0]
    normalized_pins = []
    previous = -1.0
    for pin in pins:
        t = finite(pin['seconds'], 'pin seconds', 0.0)
        asset = pin['asset']
        if t <= previous or t >= seconds:
            raise ValueError('Pins must be strictly ordered within the clip')
        if not isinstance(asset, str) or '/' in asset or '\\' in asset or asset not in reference_images:
            raise ValueError('Each pin must use one of the staged reference images')
        normalized = {'seconds': t, 'asset': asset}
        for key in ('line_id', 'speaker', 'role', 'audio_asset'):
            if key in pin:
                if not isinstance(pin[key], str) or not pin[key]:
                    raise ValueError(f'Pin {key} must be a non-empty string when supplied')
                if key == 'audio_asset':
                    if '/' in pin[key] or '\\' in pin[key] or not pin[key].endswith('.wav'):
                        raise ValueError('Pin audio assets must be staged local WAV names')
                normalized[key] = pin[key]
        normalized_pins.append(normalized)
        previous = t
    midpoint_pins = None
    if dialogue_lines is not None:
        midpoint_pins = validate_dialogue_midpoint_pin_coverage(normalized_pins, dialogue_lines, speaker_pin_assets or {})
    clip = {'seconds': seconds, 'audio_asset': audio_asset, 'width': width, 'height': height, 'pins': normalized_pins}
    compiled = compile_workflow(graph, BINDINGS, clip)
    result = {
        'route': 'original_h3_comfy_modal',
        'status': 'planned_not_runtime_validated',
        'live_enabled': False,
        'prompt': prompt,
        'reference_images': reference_images,
        'clip': clip,
        'compiled': compiled,
        'required_before_execution': [
            'verified compute account and workspace role',
            'provider-side hard usage and spend limits',
            'explicit one-job spend approval',
            'staged input SHA verification',
            'post-render sync QA with visible-speaker mouth track',
            'whole-line mouth-motion QA for every dialogue line',
        ],
    }
    if midpoint_pins is not None:
        result['dialogue_midpoint_pin_coverage'] = midpoint_pins
    return result
