"""Hash-bound review checks and assembly handoff for explicit local routes.

These records describe technical review, not user spending/generation authority.
No function creates approval. User holds remain independently binding.
"""
import hashlib,json
from pathlib import Path
from forge.gates.common import GateLocked,read_json,sha256_file,write_json

CHECKS=('identity','wardrobe','location','full_speech','speech_text','av_sync','speaker_mapping')

def job_fingerprint(job):
    return hashlib.sha256(json.dumps(job,sort_keys=True,default=str).encode()).hexdigest()

def require_record(record, *, expected_job, output):
    if not isinstance(record,dict) or record.get('status')!='approved' or not record.get('reviewer') or not record.get('review_source'):
        raise GateLocked('explicit clip review with reviewer and source required')
    if record.get('job_sha256')!=job_fingerprint(expected_job):
        raise GateLocked('review describes a different plan/input/runtime job')
    if not all(record.get('checks',{}).get(k) is True for k in CHECKS):
        raise GateLocked('clip identity/audio/continuity review incomplete')
    if not Path(output).is_file() or sha256_file(output)!=record.get('output_sha256'):
        raise GateLocked('reviewed output missing or changed')
    return record

def require_local_clip_review(project_dir,backend,job,entry):
    if not entry.get('result',{}).get('ok'):
        raise GateLocked('failed or unknown prior attempt must be reconciled, never automatically retried')
    if entry.get('job')!=job:
        raise GateLocked('prior attempt describes a different prepared job')
    if not entry.get('result',{}).get('output_timing',{}).get('duration_verified'):
        raise GateLocked('actual muxed duration verification missing')
    reviews=read_json(Path(project_dir)/'.forge'/('local_'+backend+'_reviews.json')) or {}
    return require_record(reviews.get(str(job['plan_n'])),expected_job=job,output=job['expected_output'])

def reviewed_plan_outputs(project_dir,*,backend,plan_path=None,audio_jobs):
    """Require every planned clip, including silent shots, in original order."""
    from forge.render_plan import build_render_jobs
    plan=build_render_jobs(project_dir,plan_path)
    state=read_json(Path(project_dir)/'.forge'/('local_'+backend+'_execution.json')) or {}
    by_id={j['plan_n']:j for j in audio_jobs}
    if len(by_id)!=len(audio_jobs):raise GateLocked('duplicate selected audio job')
    external=read_json(Path(project_dir)/'.forge'/('local_'+backend+'_silent_reviews.json')) or {}
    outputs=[]
    for planned in plan:
        n=planned['plan_n']
        if planned['silent']:
            record=external.get(str(n)) or {};output=record.get('output_path','')
            require_record(record,expected_job=planned,output=output)
        else:
            if n not in by_id:raise GateLocked('dialogue shot missing from selected audio jobs')
            job=by_id[n];entry=state.get('jobs',{}).get(str(n),{})
            require_local_clip_review(project_dir,backend,job,entry);output=job['expected_output']
        outputs.append(output)
    if not outputs:raise GateLocked('empty plan cannot be assembled')
    return outputs

def assemble_reviewed_local_plan(project_dir,*,backend,audio_jobs,out,plan_path=None):
    """Call existing compositor only after complete hash-bound review coverage.

    No new voice, music, captions or timing edits are inferred. Original muxed
    shot audio stays with its shot. Result still requires final visual/audio review.
    """
    from .plan_execution import REPOSITORY_ROOT
    from forge.guard.generation_hold import require_generation_open
    require_generation_open(project_dir=REPOSITORY_ROOT)
    require_generation_open(project_dir=project_dir)
    if Path(out).exists():raise GateLocked('assembly output exists; never overwrite it')
    shots=reviewed_plan_outputs(project_dir,backend=backend,plan_path=plan_path,audio_jobs=audio_jobs)
    from forge.assemble.compose import compose
    output=compose(shots,None,None,str(out))
    receipt={'status':'assembled_pending_final_review','episode_accepted':False,
        'source_clips':[{'path':p,'sha256':sha256_file(p)} for p in shots],
        'output':output,'output_sha256':sha256_file(output)}
    write_json(str(out)+'.review_receipt.json',receipt)
    return receipt
