import asyncio,json,wave
import pytest
from forge.gates.common import GateLocked
from forge.guard.ledger import SpendLocked
from forge.render_plan import execute_plan
from forge.integrations.plan_execution import prepare_local_plan,require_backend_acceptance

def test_actual_render_plan_dispatches_to_local_orchestrator(monkeypatch,tmp_path):
    seen={}
    def local(project,**kwargs):seen.update(kwargs);return ['ROUTED NO GPU']
    monkeypatch.setattr('forge.integrations.plan_execution.execute_local_plan',local)
    assert asyncio.run(execute_plan(tmp_path,None,local_backend='infinitetalk',local_options={'root':str(tmp_path)}))==['ROUTED NO GPU']
    assert seen['backend']=='infinitetalk'

def test_selected_local_path_checks_repo_hold_before_preparation(tmp_path,monkeypatch):
    monkeypatch.setattr('forge.integrations.plan_execution.REPOSITORY_ROOT',tmp_path)
    root=tmp_path/'repo';(root/'.forge').mkdir(parents=True)
    (root/'.forge/generation_hold.json').write_text(json.dumps({'held':True,'reason':'production stopped'}))
    def fail(*a,**k):raise AssertionError('must not prepare/launch')
    monkeypatch.setattr('forge.integrations.plan_execution.prepare_local_plan',fail)
    with pytest.raises(SpendLocked,match='production stopped'):
        asyncio.run(execute_plan(tmp_path,None,local_backend='infinitetalk',local_options={'root':root,'ckpt_dir':root,'wav2vec_dir':root,'audio_by_plan_n':{1:{}}}))

def test_local_backend_never_falls_back_to_paid_generator(tmp_path):
    with pytest.raises(GateLocked,match='cannot mix'):
        asyncio.run(execute_plan(tmp_path,object(),local_backend='multitalk',local_options={}))

def test_backend_acceptance_missing_even_with_gate_bypass(tmp_path,monkeypatch):
    monkeypatch.setenv('FORGE_GATES','0')
    with pytest.raises(GateLocked):require_backend_acceptance(tmp_path,'infinitetalk')

def test_preparation_uses_actual_plan_and_checks_full_audio_under_hold(tmp_path):
    from forge.gates.still_first import lock_stills
    from PIL import Image
    (tmp_path/'out').mkdir();ref=tmp_path/'ref.png';Image.new('RGB',(16,16)).save(ref)
    audio=tmp_path/'voice.wav'
    with wave.open(str(audio),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0\0'*19200)
    plan=[{'plan_n':1,'kind':'speaker','speaker':'Harry','camera':'single:Harry','seconds':1.2,'line':{'text':'Test.'}}]
    (tmp_path/'out/e01_plan.json').write_text(json.dumps(plan));lock_stills(tmp_path,{'character:Harry:angle:front':str(ref)})
    (tmp_path/'.forge/generation_hold.json').write_text(json.dumps({'held':True}))
    prepared=prepare_local_plan(tmp_path,backend='infinitetalk',root=tmp_path,ckpt_dir=tmp_path,wav2vec_dir=tmp_path,audio_by_plan_n={1:{'person1':str(audio)}})
    assert prepared['jobs'][0]['frame_num']==33 and prepared['jobs'][0]['audio_timing']['speech_preserved']
    assert prepared['status']=='prepared_not_generated' and not prepared['episode_complete']

def test_orchestrator_calls_duration_safe_executor_once_then_stops_for_review(tmp_path,monkeypatch):
    from forge.integrations.plan_execution import execute_local_plan
    monkeypatch.setattr('forge.integrations.plan_execution.REPOSITORY_ROOT',tmp_path)
    monkeypatch.setattr('forge.gates.angle_stills.require_angle_stills',lambda *a:None)
    monkeypatch.setattr('forge.render_plan._load_plan',lambda *a:[])
    job={'plan_n':1,'frame_num':33}
    monkeypatch.setattr('forge.integrations.plan_execution.enforce_render_allowed',lambda *a:None)
    monkeypatch.setattr('forge.integrations.plan_execution.prepare_local_plan',lambda *a,**k:{'jobs':[job,{'plan_n':2}]})
    calls=[]
    def safe(j,**kwargs):calls.append((j,kwargs));return {'ok':True,'audio_timing':{'speech_preserved':True}}
    monkeypatch.setattr('forge.integrations.audio_timing.execute_audio_job_preserving_speech',safe)
    with pytest.raises(GateLocked,match='review required'):
        execute_local_plan(tmp_path,backend='infinitetalk',root=tmp_path,ckpt_dir=tmp_path,wav2vec_dir=tmp_path,audio_by_plan_n={},mode='proof')
    assert len(calls)==1 and 'allow_test_truncation' not in calls[0][1]
    state=json.loads((tmp_path/'.forge/local_infinitetalk_execution.json').read_text())
    assert state['jobs']['1']['status']=='pending_review'
    with pytest.raises(GateLocked,match='already attempted'):
        execute_local_plan(tmp_path,backend='infinitetalk',root=tmp_path,ckpt_dir=tmp_path,wav2vec_dir=tmp_path,audio_by_plan_n={},mode='proof')
    assert len(calls)==1

def test_disabled_gates_cannot_launch_local_plan(tmp_path,monkeypatch):
    from forge.integrations.plan_execution import execute_local_plan
    monkeypatch.setattr('forge.integrations.plan_execution.REPOSITORY_ROOT',tmp_path)
    monkeypatch.setenv('FORGE_GATES','0')
    with pytest.raises(GateLocked,match='disabled review gates'):
        execute_local_plan(tmp_path,backend='multitalk',root=tmp_path,ckpt_dir=tmp_path,wav2vec_dir=tmp_path,audio_by_plan_n={},mode='proof')


def test_actual_repository_hold_cannot_be_evaded_by_root_argument(tmp_path,monkeypatch):
    real_repo=tmp_path/'real_repo';(real_repo/'.forge').mkdir(parents=True)
    (real_repo/'.forge/generation_hold.json').write_text(json.dumps({'held':True,'reason':'repository hold'}))
    monkeypatch.setattr('forge.integrations.plan_execution.REPOSITORY_ROOT',real_repo)
    with pytest.raises(SpendLocked,match='repository hold'):
        asyncio.run(execute_plan(tmp_path,None,local_backend='multitalk',local_options={'root':tmp_path,'ckpt_dir':tmp_path,'wav2vec_dir':tmp_path,'audio_by_plan_n':{}}))

def test_local_route_refuses_silently_ignored_intent_options(tmp_path):
    for options in ({'director_bible':{}},{'prompt_for':lambda _:''},{'audio':True},{'resolution':'480p'},{'credit_cap':1}):
        with pytest.raises(GateLocked,match='cannot mix'):
            asyncio.run(execute_plan(tmp_path,None,local_backend='multitalk',local_options={},**options))
