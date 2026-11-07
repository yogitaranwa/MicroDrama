import json
import pytest
from forge.gates.common import GateLocked,sha256_file
from forge.integrations.plan_review import require_record,job_fingerprint,CHECKS

def record(job,output):
    return {'status':'approved','reviewer':'fixture','review_source':'synthetic test only',
        'job_sha256':job_fingerprint(job),'output_sha256':sha256_file(output),
        'checks':dict.fromkeys(CHECKS,True)}

def test_review_binds_output_job_and_every_check(tmp_path):
    p=tmp_path/'clip';p.write_bytes(b'synthetic')
    job={'plan_n':1,'audio_sha256_expected':{'person1':'a'}};review=record(job,p)
    assert require_record(review,expected_job=job,output=p)
    with pytest.raises(GateLocked,match='different'):require_record(review,expected_job={**job,'plan_n':2},output=p)
    review['checks']['full_speech']=False
    with pytest.raises(GateLocked,match='incomplete'):require_record(review,expected_job=job,output=p)
    review['checks']['full_speech']=True;p.write_bytes(b'changed')
    with pytest.raises(GateLocked,match='changed'):require_record(review,expected_job=job,output=p)

def test_missing_silent_or_dialogue_clip_blocks_assembly_handoff(tmp_path,monkeypatch):
    from forge.integrations.plan_review import reviewed_plan_outputs
    monkeypatch.setattr('forge.render_plan.build_render_jobs',lambda *a:[{'plan_n':1,'silent':False}])
    with pytest.raises(GateLocked,match='dialogue shot missing'):
        reviewed_plan_outputs(tmp_path,backend='infinitetalk',audio_jobs=[])
    monkeypatch.setattr('forge.render_plan.build_render_jobs',lambda *a:[{'plan_n':2,'silent':True}])
    with pytest.raises(GateLocked,match='explicit clip review'):
        reviewed_plan_outputs(tmp_path,backend='infinitetalk',audio_jobs=[])

def test_hash_reviewed_audio_and_silent_handoff_preserves_plan_order(tmp_path,monkeypatch):
    from forge.integrations.plan_review import reviewed_plan_outputs
    a=tmp_path/'dialogue';a.write_bytes(b'a');b=tmp_path/'silent';b.write_bytes(b'b')
    job={'plan_n':1,'expected_output':str(a)};silent={'plan_n':2,'silent':True}
    monkeypatch.setattr('forge.render_plan.build_render_jobs',lambda *a:[{'plan_n':1,'silent':False},silent])
    state=tmp_path/'.forge';state.mkdir()
    (state/'local_infinitetalk_execution.json').write_text(json.dumps({'jobs':{'1':{'job':job,'result':{'ok':True,'output_timing':{'duration_verified':True}}}}}))
    (state/'local_infinitetalk_reviews.json').write_text(json.dumps({'1':record(job,a)}))
    (state/'local_infinitetalk_silent_reviews.json').write_text(json.dumps({'2':{**record(silent,b),'output_path':str(b)}}))
    assert reviewed_plan_outputs(tmp_path,backend='infinitetalk',audio_jobs=[job])==[str(a),str(b)]

def test_actual_compositor_uses_reviewed_muxed_audio_and_never_marks_accepted(tmp_path,monkeypatch):
    import subprocess
    from forge.integrations.plan_review import assemble_reviewed_local_plan
    monkeypatch.setattr('forge.integrations.plan_execution.REPOSITORY_ROOT',tmp_path)
    clips=[]
    for color,hz in [('red',300),('blue',500)]:
        p=tmp_path/(color+'.mp4')
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c={color}:s=32x48:d=0.4:r=25',
            '-f','lavfi','-i',f'sine=frequency={hz}:duration=0.4:sample_rate=16000','-c:v','libx264','-c:a','aac',str(p)],check=True)
        clips.append(str(p))
    monkeypatch.setattr('forge.integrations.plan_review.reviewed_plan_outputs',lambda *a,**k:clips)
    out=tmp_path/'assembly.mp4'
    receipt=assemble_reviewed_local_plan(tmp_path,backend='infinitetalk',audio_jobs=[],out=out)
    assert out.is_file() and not receipt['episode_accepted']
    assert receipt['status']=='assembled_pending_final_review'
    from forge.integrations.audio_timing import probe_audio_duration
    assert probe_audio_duration(out)>=0.79
    with pytest.raises(GateLocked,match='never overwrite'):
        assemble_reviewed_local_plan(tmp_path,backend='infinitetalk',audio_jobs=[],out=out)

def test_reviewed_first_clip_is_skipped_without_regeneration(tmp_path,monkeypatch):
    from forge.integrations.plan_execution import execute_local_plan
    monkeypatch.setattr('forge.integrations.plan_execution.REPOSITORY_ROOT',tmp_path)
    monkeypatch.setattr('forge.integrations.plan_execution.enforce_render_allowed',lambda *a:None)
    monkeypatch.setattr('forge.gates.angle_stills.require_angle_stills',lambda *a:None)
    monkeypatch.setattr('forge.render_plan._load_plan',lambda *a:[])
    output=tmp_path/'first';output.write_bytes(b'synthetic')
    first={'plan_n':1,'expected_output':str(output),'runtime_contract':{'mode':'proof','runtime_profile':'upstream','quant':None,'quant_dir':None,'sample_steps':None,'persistent_dit':None,'t5_cpu':False,'python':'python3','infinitetalk_ckpt':None}};second={'plan_n':2}
    monkeypatch.setattr('forge.integrations.plan_execution.prepare_local_plan',lambda *a,**k:{'jobs':[first,second]})
    state=tmp_path/'.forge';state.mkdir()
    (state/'local_infinitetalk_execution.json').write_text(json.dumps({'jobs':{'1':{'job':first,'result':{'ok':True,'output_timing':{'duration_verified':True}}}}}))
    (state/'local_infinitetalk_reviews.json').write_text(json.dumps({'1':record(first,output)}))
    seen=[]
    def safe(job,**kwargs):seen.append(job['plan_n']);return {'ok':True}
    monkeypatch.setattr('forge.integrations.audio_timing.execute_audio_job_preserving_speech',safe)
    with pytest.raises(GateLocked,match='review required'):
        execute_local_plan(tmp_path,backend='infinitetalk',root=tmp_path,ckpt_dir=tmp_path,wav2vec_dir=tmp_path,audio_by_plan_n={},mode='proof')
    assert seen==[2]

def test_review_cannot_cover_changed_runtime_controls(tmp_path):
    p=tmp_path/'clip';p.write_bytes(b'synthetic')
    job={'plan_n':1,'runtime_contract':{'sample_steps':4}}
    reviewed=record(job,p)
    changed={**job,'runtime_contract':{'sample_steps':20}}
    with pytest.raises(GateLocked,match='different plan/input/runtime'):
        require_record(reviewed,expected_job=changed,output=p)
