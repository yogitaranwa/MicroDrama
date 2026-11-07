"""Prepared VACE/PuLID jobs with fresh still gates at execution.

These functions prepare or execute local processes only. They do not provision
compute, approve licenses/spending or certify image quality. Existing builders
and upstream source are unchanged.
"""
import json
import math
from pathlib import Path

from forge.gates.common import GateLocked, sha256_file
from forge.gates.enforce import enforce_render_allowed
from forge.gates.still_first import require_still_lock
from .jobs import vace_cli, pulid_sdxl_driver
from .registry import IntegrationError
from .runner import preflight, run_streamed as run


def _file(path):
    p = Path(path).resolve()
    if not p.is_file():
        raise IntegrationError(f'input file missing: {p}')
    return str(p)


def _output(path):
    p = Path(path).resolve()
    if p.exists():
        raise IntegrationError('output already exists; review it instead of silently rerunning')
    if not p.parent.is_dir():
        raise IntegrationError('output parent must exist')
    return str(p)


def _prepared(backend, output, parameters, inputs):
    hashes = {_file(p): sha256_file(_file(p)) for p in inputs}
    if output in hashes:
        raise IntegrationError('output cannot replace an input')
    return {'backend': backend, 'expected_output': output,
            'parameters': parameters, 'input_sha256_expected': hashes,
            'status': 'prepared_not_executed', 'quality_status': 'unreviewed'}


def prepare_vace_job(*, prompt, output, references=(), source_video=None,
                     source_mask=None, model='vace-1.3B', frames=17,
                     steps=50, seed=42, size='480p', runtime_profile='upstream'):
    if not prompt or not prompt.strip():
        raise IntegrationError('prompt must be non-empty')
    if model not in ('vace-1.3B', 'vace-14B'):
        raise IntegrationError('unsupported VACE model')
    if runtime_profile not in ('upstream','t4_dual_staged'):
        raise IntegrationError('unsupported VACE runtime profile')
    if runtime_profile=='t4_dual_staged' and model!='vace-1.3B':
        raise IntegrationError('staged T4 profile only supports1.3B')
    if size not in ('480p', '480*832', '832*480'):
        raise IntegrationError('prepared VACE proof route is 480p only')
    if type(frames) is not int or not 5 <= frames <= 81 or (frames-1) % 4:
        raise IntegrationError('VACE proof frames must be 4n+1, from5 to81')
    if type(steps) is not int or not 1 <= steps <= 100:
        raise IntegrationError('steps must be an integer from1 to100')
    if type(seed) is not int or seed < 0:
        raise IntegrationError('seed must be a non-negative integer')
    refs = [_file(p) for p in references]
    video = _file(source_video) if source_video else None
    mask = _file(source_mask) if source_mask else None
    if mask and not video:
        raise IntegrationError('a source mask requires a source video')
    if not refs and not video:
        raise IntegrationError('VACE conditioning needs a reference or source video')
    params = dict(prompt=prompt, references=refs, source_video=video,
                  source_mask=mask, model=model, frames=frames,
                  steps=steps, seed=seed, size=size, runtime_profile=runtime_profile)
    return _prepared('vace', _output(output), params,
                     refs + [p for p in (video, mask) if p])


def prepare_pulid_job(*, prompt, reference, output, seed=42, id_scale=1.0,
                      height=1024, width=1024):
    if not prompt or not prompt.strip():
        raise IntegrationError('prompt must be non-empty')
    if type(seed) is not int or seed < 0:
        raise IntegrationError('seed must be a non-negative integer')
    if not isinstance(id_scale, (float, int)) or not math.isfinite(id_scale) or id_scale < 0:
        raise IntegrationError('identity scale must be finite and non-negative')
    if any(type(n) is not int or n < 64 or n % 8 for n in (height, width)):
        raise IntegrationError('image dimensions must be multiples of8, at least64')
    ref = _file(reference)
    params = dict(prompt=prompt, reference=ref, seed=seed, id_scale=id_scale,
                  height=height, width=width)
    return _prepared('pulid', _output(output), params, [ref])


def execute_visual_job(job, *, project_dir, root, ckpt_dir=None,
                       driver_dir=None, mode='proof', host_reviewed=False,
                       python='python3', timeout_s=3600):
    """Build fresh argv after validation. Never execute a manifest's argv.

    Every reference must be in the current still lock. Source video/mask bytes
    are hash-pinned, but not mislabeled as stills. PuLID's constructor may fetch
    uncached model files, so host/license/download review is mandatory.
    """
    if host_reviewed is not True:
        raise IntegrationError('GPU environment and model licenses must be reviewed first')
    backend = job.get('backend')
    p = job.get('parameters', {})
    output = _output(job['expected_output'])
    if backend == 'vace':
        fresh = prepare_vace_job(output=output, **p)
        references = fresh['parameters']['references']
    elif backend == 'pulid':
        fresh = prepare_pulid_job(output=output, **p)
        references = [fresh['parameters']['reference']]
    else:
        raise IntegrationError('unsupported visual backend')
    if fresh['input_sha256_expected'] != job.get('input_sha256_expected'):
        raise GateLocked('visual conditioning changed after preparation')
    enforce_render_allowed(project_dir, mode)
    lock = require_still_lock(project_dir)
    locked = {str(Path(e['path']).resolve()): e['sha256']
              for e in lock.get('stills', {}).values()}
    for ref in references:
        if locked.get(ref) != fresh['input_sha256_expected'][ref]:
            raise GateLocked('conditioning reference is not in the current still lock')
    root = str(Path(root).resolve())
    required = list(fresh['input_sha256_expected'])
    if backend == 'vace':
        if not ckpt_dir or not Path(ckpt_dir).is_dir() or not any(Path(ckpt_dir).iterdir()):
            raise IntegrationError('VACE checkpoint directory missing or empty')
        argv = vace_cli(root, p['prompt'], output, src_ref_images=references,
                        src_video=p['source_video'], src_mask=p['source_mask'],
                        model=p['model'], python=python)
        # Last supplied size is authoritative in argparse; avoid duplicate flags.
        argv[argv.index('--size') + 1] = p['size']
        argv += ['--ckpt_dir', str(Path(ckpt_dir).resolve()),
                 '--frame_num', str(p['frames']), '--sample_steps', str(p['steps']),
                 '--base_seed', str(p['seed']), '--offload_model', 'True', '--t5_cpu']
        required.append(ckpt_dir)
        if p.get('runtime_profile') == 't4_dual_staged':
            from .weight_layout import check_weight_layout
            layout=check_weight_layout('vace',ckpt_dir)
            if not layout['layout_ok']:
                raise IntegrationError('; '.join(layout['errors']))
            manifest=Path(output+'.prepared.json')
            if manifest.exists():
                raise IntegrationError('existing staged manifest; inspect before retry')
            manifest.write_text(json.dumps(fresh,indent=2))
            argv=[python,str(Path(__file__).with_name('vace_staged_driver.py')),
                  '--job',str(manifest),'--root',root,'--project-dir',str(Path(project_dir).resolve()),
                  '--checkpoint',str(Path(ckpt_dir).resolve()),'--mode',mode]

    else:
        if not driver_dir or not Path(driver_dir).is_dir():
            raise IntegrationError('PuLID driver directory must exist')
        argv = pulid_sdxl_driver(root, driver_dir, p['prompt'], p['reference'],
            output, id_scale=p['id_scale'], seed=p['seed'],
            height=p['height'], width=p['width'], python=python)
    preflight(argv, required_paths=required, need_cuda=True)
    result = run(argv, cwd=str(Path(root) / 'third_party' / backend),
                 log_path=output + '.log', timeout_s=timeout_s,
                 env_extra={'PYTHONPATH':root})
    result['output_present'] = Path(output).is_file() and Path(output).stat().st_size > 0
    result['ok'] = result['ok'] and result['output_present']
    result['quality_status'] = 'unreviewed' if result['ok'] else 'failed'
    return result
