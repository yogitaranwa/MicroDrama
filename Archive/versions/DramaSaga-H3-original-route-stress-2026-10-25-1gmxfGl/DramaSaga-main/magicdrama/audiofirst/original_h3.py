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
        normalized_pins.append({'seconds': t, 'asset': asset})
        previous = t
    clip = {'seconds': seconds, 'audio_asset': audio_asset, 'width': width, 'height': height, 'pins': normalized_pins}
    compiled = compile_workflow(graph, BINDINGS, clip)
    return {
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
        ],
    }
