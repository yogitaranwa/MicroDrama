"""Offline, single-identity SDXL FaceID route and deterministic prompt batches.
Code preparation does not load models. Execution is separately user-gated.
No hosted API can be claimed to run this adapter.
"""
import hashlib
import json
import math
from pathlib import Path
from .registry import IntegrationError


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for part in iter(lambda: f.read(1048576), b''): h.update(part)
    return h.hexdigest()


def prepare_faceid_batch(*, reference, prompts, output_dir, seed=42,
                         width=768, height=1344, steps=30, scale=1.0):
    ref = Path(reference).resolve()
    if not ref.is_file(): raise IntegrationError('FaceID reference missing')
    if type(seed) is not int or not 0 <= seed < 2**32: raise IntegrationError('invalid seed')
    if any(type(n) is not int or n < 64 or n > 2048 or n % 8 for n in (width, height)):
        raise IntegrationError('dimensions must be multiples of8 from64 to2048')
    if type(steps) is not int or not 1 <= steps <= 100: raise IntegrationError('invalid steps')
    if isinstance(scale, bool) or not isinstance(scale, (float, int)) or not math.isfinite(scale) or not 0 < scale <= 2:
        raise IntegrationError('invalid identity scale')
    if not isinstance(prompts, dict) or not 1 <= len(prompts) <= 24:
        raise IntegrationError('batch needs1-24 named prompts for ONE identity')
    jobs = []
    out = Path(output_dir).resolve()
    for label, prompt in prompts.items():
        if not isinstance(label, str) or not label or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in label):
            raise IntegrationError('unsafe output label')
        if not isinstance(prompt, str) or not prompt.strip(): raise IntegrationError('empty prompt')
        target = out / (label + '.png')
        if target.exists(): raise IntegrationError('refusing output overwrite: ' + str(target))
        jobs.append(dict(label=label, prompt=prompt, output=str(target), seed=seed,
                         width=width, height=height, steps=steps, scale=scale))
    return dict(backend='ip_adapter_faceid_sdxl', reference=str(ref),
                reference_sha256=digest(ref), jobs=jobs, status='prepared_not_executed',
                quality_status='unreviewed', scope='personal_noncommercial_research')


def validate_batch(batch):
    jobs = batch.get('jobs', [])
    if not jobs: raise IntegrationError('no batch jobs')
    fresh = prepare_faceid_batch(reference=batch['reference'],
        prompts={j['label']: j['prompt'] for j in jobs},
        output_dir=str(Path(jobs[0]['output']).parent),
        **{k: jobs[0][k] for k in ('seed','width','height','steps','scale')})
    if fresh != batch: raise IntegrationError('batch parameters/reference changed or malformed')
    return fresh


def execute_faceid_batch(batch, *, project_dir, root, base_model_dir,
                         adapter_checkpoint, insightface_root,
                         personal_research_reviewed=False, timeout_s=3600,
                         python='python3'):
    from forge.guard.generation_hold import require_generation_open
    from forge.gates.still_first import require_still_lock
    from forge.gates.common import GateLocked
    from .runner import preflight, run_streamed as run
    require_generation_open(project_dir=project_dir)
    if personal_research_reviewed is not True:
        raise IntegrationError('research-only face model terms require review; no commercial route')
    fresh = validate_batch(batch)
    lock = require_still_lock(project_dir)
    if not any(str(Path(v['path']).resolve()) == fresh['reference'] and v['sha256'] == fresh['reference_sha256'] for v in lock['stills'].values()):
        raise GateLocked('FaceID reference is not in current still lock')
    base = Path(base_model_dir).resolve(); adapter = Path(adapter_checkpoint).resolve()
    face = Path(insightface_root).resolve()
    if not (base/'model_index.json').is_file(): raise IntegrationError('local SDXL snapshot required')
    if adapter.name != 'ip-adapter-faceid_sdxl.bin' or not adapter.is_file():
        raise IntegrationError('explicit SDXL FaceID checkpoint required, not SD1.5/Plus')
    face_models = face/'models'/'buffalo_l'
    if len(list(face_models.glob('*.onnx'))) < 5: raise IntegrationError('complete cached buffalo_l model required')
    repo = Path(root).resolve()/'third_party'/'ip_adapter_faceid'
    driver = Path(__file__).with_name('faceid_driver.py')
    out = Path(fresh['jobs'][0]['output']).parent
    out.mkdir(parents=True, exist_ok=True)
    manifest = out/'faceid_prepared.json'
    if manifest.exists(): raise IntegrationError('existing execution manifest; inspect rather than retry')
    manifest.write_text(json.dumps(fresh, indent=2))
    argv = [python,str(driver),'--manifest',str(manifest),'--repo',str(repo),
            '--base-model',str(base),'--adapter',str(adapter),'--insightface-root',str(face),'--project-dir',str(Path(project_dir).resolve())]
    preflight(argv, required_paths=[base,adapter,face_models,repo], need_cuda=True)
    result = run(argv, log_path=str(out/'faceid.log'), timeout_s=timeout_s,
                 env_extra={'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PYTHONPATH':str(Path(root).resolve())})
    result['output_present'] = all(Path(j['output']).is_file() for j in fresh['jobs'])
    result['ok'] = result['ok'] and result['output_present']
    result['quality_status'] = 'unreviewed' if result['ok'] else 'failed'
    return result


def prepare_character_angle_batch(*, character, identifiers, outfit, reference,
                                  output_dir, existing=(), seed=42):
    """Connect the source-guide angle matrix to the real local FaceID batch route.
    Return a finished-coverage report without generation when all angles exist.
    """
    from .angle_matrix import build_angle_plan
    angle_plan=build_angle_plan(character,identifiers,outfit,existing=existing)
    if not angle_plan['missing']:
        return {'angle_plan':angle_plan,'batch':None,'status':'covered_no_generation'}
    batch=prepare_faceid_batch(reference=reference,prompts=angle_plan['prompts'],
                              output_dir=output_dir,seed=seed)
    return {'angle_plan':angle_plan,'batch':batch,'status':'prepared_not_executed'}
