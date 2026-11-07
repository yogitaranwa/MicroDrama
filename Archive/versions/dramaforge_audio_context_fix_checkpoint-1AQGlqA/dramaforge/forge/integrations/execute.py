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
from .weight_layout import check_weight_layout
from .runner import preflight, run_streamed as run


def execute_audio_job(job, *, project_dir, root, ckpt_dir, wav2vec_dir,
                      mode='proof', host_reviewed=False, timeout_s=3600,
                      infinitetalk_ckpt=None, python='python3', sample_steps=None,
                      num_persistent_param_in_dit=None, t5_cpu=False,
                      runtime_profile='upstream', quant=None, quant_dir=None):
    """Execute a prepared job with fresh inputs/gates, never arbitrary argv.

    host_reviewed is an explicit caller check, not proof of payment authority.
    The operator must separately establish any required spending permission.
    Paid/cloud provisioning is outside this function.
    """
    if host_reviewed is not True:
        raise IntegrationError('GPU environment and model licenses must be reviewed first')
    # Explicit validation controls. No arbitrary flags from prepared manifests.
    if sample_steps is not None and (type(sample_steps) is not int or not 1 <= sample_steps <= 100):
        raise IntegrationError('sample_steps must be an integer from1 to100')
    if num_persistent_param_in_dit is not None and (type(num_persistent_param_in_dit) is not int or num_persistent_param_in_dit < 0):
        raise IntegrationError('persistent parameter count must be a non-negative integer')
    if type(t5_cpu) is not bool:
        raise IntegrationError('t5_cpu must be a bool')
    if runtime_profile not in ('upstream','t4_dual_quantized'):
        raise IntegrationError('unsupported audio runtime profile')
    if quant is not None and quant not in ('int8','fp8'):
        raise IntegrationError('unsupported quantization')
    if (quant is None)!=(quant_dir is None):
        raise IntegrationError('quant and quant_dir must be supplied together')
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
    if backend == 'infinitetalk':
        if not data.get('cond_video') or Path(data['cond_video']).resolve() != Path(data['cond_image']).resolve():
            raise IntegrationError('InfiniteTalk cond_video must match gated cond_image')
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
    # Upstream save_video_ffmpeg appends .mp4 itself; manifests name final output.
    if output.suffix.lower()!='.mp4':raise IntegrationError('audio-driven output must end in .mp4')
    safe_argv[safe_argv.index('--save_file')+1]=str(output.with_suffix(''))
    if sample_steps is not None:
        safe_argv += ['--sample_steps',str(sample_steps)]
    if num_persistent_param_in_dit is not None:
        safe_argv += ['--num_persistent_param_in_dit',str(num_persistent_param_in_dit)]
    if t5_cpu:
        safe_argv += ['--t5_cpu']
    if quant is not None:
        safe_argv += ['--quant',quant,'--quant_dir',str(Path(quant_dir).resolve())]
    layout=check_weight_layout(backend,ckpt_dir,wav2vec_dir=wav2vec_dir,infinitetalk_ckpt=infinitetalk_ckpt,quant=quant,quant_dir=quant_dir)
    if not layout['layout_ok']:
        raise IntegrationError('; '.join(layout['errors']))
    env_extra=None
    if runtime_profile=='t4_dual_quantized':
        from .audio_t4_driver import validate_audio_t4_argv
        try:validate_audio_t4_argv(safe_argv)
        except (ValueError,IndexError) as e:raise IntegrationError(str(e)) from e
        manifest=Path(str(output)+'.argv.json')
        if manifest.exists():raise IntegrationError('existing runtime manifest; inspect before retry')
        manifest.write_text(json.dumps(safe_argv,indent=2))
        safe_argv=[python,str(Path(__file__).with_name('audio_t4_driver.py')),
            '--argv-json',str(manifest),'--project-dir',str(Path(project_dir).resolve())]
        env_extra={'PYTHONPATH':str(Path(root).resolve())}
    preflight(safe_argv, required_paths=required, need_cuda=True)
    result = run(safe_argv, cwd=str(Path(root).resolve() / 'third_party' / backend),
                 log_path=str(output) + '.log', timeout_s=timeout_s,env_extra=env_extra)
    result['output_present'] = output.is_file() and output.stat().st_size > 0
    result['ok'] = result['ok'] and result['output_present']
    result['quality_status'] = 'unreviewed' if result['ok'] else 'failed'
    return result
