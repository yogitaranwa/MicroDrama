"""Selectable plan orchestration for local audio backends, with no paid fallback.

Preparation works under a production hold. Execution always rechecks both
repository and project holds, existing gates, duration and backend acceptance.
Runtime outputs are pending review, never silently accepted as episode clips.
"""
from pathlib import Path
from forge.gates.common import GateLocked, read_json, write_json, sha256_file
from forge.guard.generation_hold import require_generation_open
from forge.gates.enforce import enforce_render_allowed
from .registry import IntegrationError

REPOSITORY_ROOT=Path(__file__).resolve().parents[2]


def prepare_local_plan(project_dir, *, backend, root, ckpt_dir, wav2vec_dir,
                       audio_by_plan_n, plan_path=None, out_dir=None):
    from forge.render_plan import build_render_jobs
    from .plan_bridge import prepare_audio_driven_jobs
    from .audio_timing import probe_audio_duration, check_speech_duration
    jobs=build_render_jobs(project_dir, plan_path)
    prepared=prepare_audio_driven_jobs(jobs, audio_by_plan_n, root=root,
        out_dir=out_dir or Path(project_dir)/'out'/'local_audio'/backend,
        backend=backend, ckpt_dir=ckpt_dir, wav2vec_dir=wav2vec_dir)
    for job in prepared:
        data=read_json(job['argv'][job['argv'].index('--input_json')+1])
        durations={name:probe_audio_duration(path) for name,path in data['cond_audio'].items()}
        job['audio_timing']=check_speech_duration(job['frame_num'],durations)
    return {'backend':backend,'jobs':prepared,'selected_plan_n':[j['plan_n'] for j in prepared],
        'unselected_plan_n':[j['plan_n'] for j in jobs if j['plan_n'] not in audio_by_plan_n],
        'status':'prepared_not_generated','episode_complete':False}


def require_backend_acceptance(project_dir, backend):
    # No bypass flag: a one-person cropped technical sample cannot unlock E01.
    record=read_json(Path(project_dir)/'.forge'/('local_'+backend+'_acceptance.json'))
    required=('identity','full_speech','av_sync','speaker_mapping','multi_shot_continuity')
    if not isinstance(record,dict) or record.get('status')!='approved' or not record.get('reviewer'):
        raise GateLocked('local backend needs explicit reviewed dialogue proof before episode use')
    if record.get('backend')!=backend or not all(record.get('checks',{}).get(k) is True for k in required):
        raise GateLocked('local backend acceptance checks incomplete')
    if not record.get('proof_path') or sha256_file(record['proof_path'])!=record.get('proof_sha256'):
        raise GateLocked('local backend proof missing or changed')
    return record


def execute_local_plan(project_dir, *, backend, root, ckpt_dir, wav2vec_dir,
                       audio_by_plan_n, plan_path=None, mode='episode',
                       host_reviewed=False, timeout_s=3600, infinitetalk_ckpt=None,
                       runtime_profile='upstream', quant=None, quant_dir=None,
                       sample_steps=None, num_persistent_param_in_dit=None,
                       t5_cpu=False, python='python3'):
    if backend not in ('multitalk','infinitetalk'):
        raise IntegrationError('explicit supported local backend required')
    # Holds cannot be dodged by placing the output in a fresh isolated folder.
    require_generation_open(project_dir=REPOSITORY_ROOT)
    require_generation_open(project_dir=root)
    require_generation_open(project_dir=project_dir)
    from forge.gates.common import enabled
    if not enabled():raise GateLocked('local orchestration refuses disabled review gates')
    enforce_render_allowed(project_dir,mode)
    from forge.gates.angle_stills import require_angle_stills
    from forge.render_plan import _load_plan
    require_angle_stills(project_dir,_load_plan(project_dir,plan_path))
    if mode=='episode':require_backend_acceptance(project_dir,backend)
    manifest=prepare_local_plan(project_dir, backend=backend,root=root,ckpt_dir=ckpt_dir,
        wav2vec_dir=wav2vec_dir,audio_by_plan_n=audio_by_plan_n,plan_path=plan_path)
    from .audio_timing import execute_audio_job_preserving_speech
    state_path=Path(project_dir)/'.forge'/('local_'+backend+'_execution.json')
    state=read_json(state_path) or {'backend':backend,'jobs':{}}
    if not isinstance(state,dict) or not isinstance(state.get('jobs'),dict):
        raise GateLocked('malformed local execution state')
    for job in manifest['jobs']:
        key=str(job['plan_n'])
        if key in state['jobs']:
            from .plan_review import require_local_clip_review
            try:require_local_clip_review(project_dir,backend,job,state['jobs'][key])
            except GateLocked as exc:
                raise GateLocked('local shot already attempted; review/reconcile before continuing: '+str(exc)) from exc
            continue
        state['jobs'][key]={'status':'started','job':job}
        write_json(state_path,state)
        try:
            result=execute_audio_job_preserving_speech(job,project_dir=project_dir,root=root,
                ckpt_dir=ckpt_dir,wav2vec_dir=wav2vec_dir,mode=mode,
                host_reviewed=host_reviewed,timeout_s=timeout_s,
                infinitetalk_ckpt=infinitetalk_ckpt,runtime_profile=runtime_profile,
                quant=quant,quant_dir=quant_dir,sample_steps=sample_steps,
                num_persistent_param_in_dit=num_persistent_param_in_dit,
                t5_cpu=t5_cpu,python=python)
        except BaseException:
            state['jobs'][key]['status']='outcome_requires_reconciliation'
            write_json(state_path,state)
            raise
        state['jobs'][key].update({'status':'pending_review' if result['ok'] else 'failed','result':result})
        write_json(state_path,state)
        # One clip then review. Never generate the whole episode without looking.
        raise GateLocked('local clip execution recorded; identity/full speech/AV sync review required before continuation')
    state.update(status='selected_clips_reviewed',episode_complete=False,
        unselected_plan_n=manifest.get('unselected_plan_n',[]))
    return state


def main():
    import argparse,json,asyncio
    parser=argparse.ArgumentParser(description='Prepare or execute explicit local dialogue plan route')
    parser.add_argument('action',choices=('prepare','execute'))
    parser.add_argument('--project-dir',required=True)
    parser.add_argument('--backend',required=True,choices=('multitalk','infinitetalk'))
    parser.add_argument('--options-json',required=True)
    args=parser.parse_args(); options=json.loads(Path(args.options_json).read_text())
    if 'audio_by_plan_n' in options:
        options['audio_by_plan_n']={int(k):v for k,v in options['audio_by_plan_n'].items()}
    if args.action=='prepare':
        result=prepare_local_plan(args.project_dir,backend=args.backend,**options)
    else:
        from forge.render_plan import execute_plan
        result=asyncio.run(execute_plan(args.project_dir,None,
            local_backend=args.backend,local_options=options))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
