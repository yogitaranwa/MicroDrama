"""Gate-enforcing local audio-driven execution. No provisioning or billing.

A prepared local GPU host and a caller-reviewed environment are prerequisites.
This entrypoint does not rent compute, download weights, grant a budget, or
approve a result. Upstream dependency/model licenses still apply.
"""
import json
from pathlib import Path

from forge.gates.common import GateLocked, sha256_file
from forge.gates.enforce import enforce_render_allowed
from forge.gates.still_first import require_still_lock
from .jobs import multitalk_cli, infinitetalk_cli
from .registry import IntegrationError
from .runner import preflight, run


def execute_audio_job(job, *, project_dir, root, ckpt_dir, wav2vec_dir,
                      mode='proof', host_reviewed=False, timeout_s=3600,
                      infinitetalk_ckpt=None, python='python3'):
    """Execute a prepared job with fresh inputs/gates, never arbitrary argv.

    host_reviewed is an explicit caller check, not proof of payment authority.
    The operator must separately establish any required spending permission.
    Paid/cloud provisioning is outside this function.
    """
    if host_reviewed is not True:
        raise IntegrationError('GPU environment and model licenses must be reviewed first')
    backend = job.get('backend')
    if backend not in ('multitalk', 'infinitetalk'):
        raise IntegrationError('unsupported backend')
    argv = job.get('argv', [])
    try:
        input_json = argv[argv.index('--input_json') + 1]
        seed = int(argv[argv.index('--base_seed') + 1])
        size = argv[argv.index('--size') + 1]
        frames = int(job['frame_num'])
        output = Path(job['expected_output']).resolve()
        data = json.loads(Path(input_json).read_text())
    except (ValueError, IndexError, KeyError, OSError) as e:
        raise IntegrationError(f'malformed prepared job: {e}') from e
    if not 5 <= frames <= 377 or (frames - 1) % 4:
        raise IntegrationError('local proof clip must be 4n+1 frames, at most about 15 seconds')
    if output.exists():
        raise IntegrationError('output already exists; review it instead of silently rerunning')
    # No filename claiming approval can bypass current project gates.
    enforce_render_allowed(project_dir, mode)
    ref = Path(data['cond_image'])
    expected = job.get('reference_sha256_expected')
    if not expected or sha256_file(ref) != expected:
        raise GateLocked('conditioning still changed after preparation')
    lock = require_still_lock(project_dir)
    if not any(Path(e['path']).resolve() == ref.resolve() and e['sha256'] == expected
               for e in lock.get('stills', {}).values()):
        raise GateLocked('conditioning still is not in the current project lock')
    voices = data.get('cond_audio', {})
    if set(voices) not in ({'person1'}, {'person1', 'person2'}):
        raise IntegrationError('invalid speaker mapping')
    for speaker, audio in voices.items():
        if sha256_file(audio) != job.get('audio_sha256_expected', {}).get(speaker):
            raise IntegrationError('speaker audio changed after preparation')
    required = [ref, input_json, ckpt_dir, wav2vec_dir, *voices.values()]
    for folder in (ckpt_dir, wav2vec_dir):
        path = Path(folder)
        if not path.is_dir() or not any(path.iterdir()):
            raise IntegrationError(f'weights directory missing or empty: {folder}')
    if not output.parent.is_dir():
        raise IntegrationError('output parent must exist')
    extra = {}
    if backend == 'infinitetalk':
        if not infinitetalk_ckpt or not Path(infinitetalk_ckpt).is_file():
            raise IntegrationError('explicit InfiniteTalk checkpoint file required')
        required.append(infinitetalk_ckpt)
        extra['infinitetalk_ckpt'] = str(Path(infinitetalk_ckpt).resolve())
    builder = multitalk_cli if backend == 'multitalk' else infinitetalk_cli
    safe_argv = builder(str(Path(root).resolve()), str(Path(input_json).resolve()),
        str(Path(ckpt_dir).resolve()), str(Path(wav2vec_dir).resolve()), str(output),
        size=size, frame_num=frames, base_seed=seed, python=python, **extra)
    preflight(safe_argv, required_paths=required, need_cuda=True)
    result = run(safe_argv, cwd=str(Path(root).resolve() / 'third_party' / backend),
                 log_path=str(output) + '.log', timeout_s=timeout_s)
    result['output_present'] = output.is_file() and output.stat().st_size > 0
    result['ok'] = result['ok'] and result['output_present']
    result['quality_status'] = 'unreviewed' if result['ok'] else 'failed'
    return result
