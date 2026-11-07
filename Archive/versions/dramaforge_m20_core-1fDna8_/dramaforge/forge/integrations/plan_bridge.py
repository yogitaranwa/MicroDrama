"""Additive bridge from existing render-plan jobs to local model commands.

Nothing executes here. Explicit shot selection, existing reference paths and
per-person audio are required. Paid routes, still locks and old behavior are
not replaced. Review generated manifests before GPU execution.
"""
from pathlib import Path
import json
import math
import hashlib

from .jobs import build_multitalk_input, multitalk_cli, infinitetalk_cli
from .registry import IntegrationError


def prepare_audio_driven_jobs(render_jobs, audio_by_plan_n, *, root, out_dir,
                              backend, ckpt_dir, wav2vec_dir, fps=25, seed=42):
    """Bind selected build_render_jobs() output to upstream per-person audio.

    audio_by_plan_n maps plan_n -> {person1: wav[, person2: wav]}. The
    caller owns correct speaker-to-person assignment and checks the image's
    left/right identity layout before inference. Single-speaker jobs remain
    single-speaker; no automatic mixing or invented audio.
    """
    if backend not in ('multitalk', 'infinitetalk'):
        raise IntegrationError('backend must be multitalk or infinitetalk')
    if fps != 25:
        raise IntegrationError('pinned audio-driven models use 25fps')
    selected = [j for j in render_jobs if j.get('plan_n') in audio_by_plan_n]
    if len(selected) != len(audio_by_plan_n):
        raise IntegrationError('audio selection contains missing or duplicate shot IDs')
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for job in selected:
        n = job['plan_n']
        if job.get('silent'):
            raise IntegrationError(f'shot {n} is silent; audio-driven backend not selected')
        ref = job.get('reference_still_path')
        if not job.get('still_present') or not ref or not Path(ref).is_file():
            raise IntegrationError(f'shot {n} has no locked conditioning still')
        expected = job.get('reference_still_sha256')
        actual = hashlib.sha256(Path(ref).read_bytes()).hexdigest()
        if not expected or expected != actual:
            raise IntegrationError(f'shot {n} conditioning still changed since lock')
        seconds = float(job.get('seconds', 0))
        if not math.isfinite(seconds) or not 0 < seconds <= 15:
            raise IntegrationError(f'shot {n}: choose a proof clip of 0-15 seconds')
        frames = 4 * math.ceil(max(1, (seconds * fps - 1) / 4)) + 1
        stem = out_dir / f'shot_{int(n):03d}_{backend}'
        input_path = str(stem) + '.json'
        build_multitalk_input(job['prompt'], str(Path(ref).resolve()),
            {k: str(Path(v).resolve()) for k, v in audio_by_plan_n[n].items()}, input_path)
        builder = multitalk_cli if backend == 'multitalk' else infinitetalk_cli
        argv = builder(str(Path(root).resolve()), input_path,
                       str(Path(ckpt_dir).resolve()), str(Path(wav2vec_dir).resolve()),
                       str(stem) + '.mp4', frame_num=frames, base_seed=seed)
        manifest.append({'plan_n': n, 'backend': backend, 'argv': argv,
                         'cwd': str(Path(root).resolve() / 'third_party' / backend),
                         'expected_output': str(stem) + '.mp4',
                         'reference_sha256_expected': job.get('reference_still_sha256'),
                         'frame_num': frames, 'source_seconds': seconds,
                         'status': 'prepared_not_executed',
                         'requires_review': ['reference identity and left/right assignment',
                            'audio timing and speaker mapping', 'licenses, weights and GPU host']})
    (out_dir / 'local_model_manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest
