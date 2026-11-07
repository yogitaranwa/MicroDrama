import json
from pathlib import Path
import pytest
from forge.guard.generation_hold import require_generation_open
from forge.guard.ledger import Ledger, SpendLocked
from forge.gates.enforce import enforce_render_allowed
from forge.integrations.faceid import prepare_faceid_batch, validate_batch, execute_faceid_batch
from forge.integrations.registry import IntegrationError, repo


def held(tmp_path):
    p=tmp_path/'.forge';p.mkdir(exist_ok=True)
    (p/'generation_hold.json').write_text(json.dumps({'held':True,'reason':'code first'}))


def test_hold_even_when_gate_bypass(tmp_path,monkeypatch):
    held(tmp_path);monkeypatch.setenv('FORGE_GATES','0')
    with pytest.raises(SpendLocked,match='code first'):enforce_render_allowed(tmp_path,'proof')


def test_ledger_hold_before_any_reservation(tmp_path,monkeypatch):
    monkeypatch.setenv('FORGE_LIVE','1');p=tmp_path/'money.json'
    p.write_text(json.dumps({'approved':23000,'spent':650}))
    (tmp_path/'generation_hold.json').write_text(json.dumps({'held':True}))
    with pytest.raises(SpendLocked):Ledger(p).reserve(50)
    assert json.loads(p.read_text())['spent']==650


@pytest.mark.parametrize('content',['x','[]','{}','{"held":0}'])
def test_corrupt_hold_fails_closed(tmp_path,content):
    held(tmp_path);(tmp_path/'.forge/generation_hold.json').write_text(content)
    with pytest.raises(SpendLocked):require_generation_open(tmp_path)


def batch(tmp_path):
    f=tmp_path/'face.png';f.write_bytes(b'reference')
    return prepare_faceid_batch(reference=f,prompts={'front':'front face','left':'left profile'},output_dir=tmp_path/'out')


def test_batch_roundtrip(tmp_path):
    b=batch(tmp_path);assert validate_batch(b)==b
    assert len(b['jobs'])==2
    assert all(j['seed']==42 for j in b['jobs'])


def test_ref_drift(tmp_path):
    b=batch(tmp_path);Path(b['reference']).write_bytes(b'new')
    with pytest.raises(IntegrationError):validate_batch(b)


def test_manifest_output_injection(tmp_path):
    b=batch(tmp_path);b['jobs'][1]['output']=str(tmp_path/'surprise.png')
    with pytest.raises(IntegrationError):validate_batch(b)


def test_existing_output_not_overwritten(tmp_path):
    b=batch(tmp_path);Path(b['jobs'][0]['output']).parent.mkdir();Path(b['jobs'][0]['output']).write_bytes(b'old')
    with pytest.raises(IntegrationError):validate_batch(b)


def test_execute_stops_before_model_import(tmp_path):
    held(tmp_path)
    with pytest.raises(SpendLocked):execute_faceid_batch(batch(tmp_path),project_dir=tmp_path,root=tmp_path,base_model_dir='missing',adapter_checkpoint='missing',insightface_root='missing')


def test_registered_full_source():
    r=repo('ip_adapter_faceid');base=Path(__file__).resolve().parents[1]/r.path
    assert (base/r.entrypoint).is_file();assert (base/r.license_file).is_file()


@pytest.mark.parametrize('field,value',[('seed',True),('seed',-1),('width',67),('scale',True),('scale',float('nan')),('steps',0)])
def test_reject_bad_parameters(tmp_path,field,value):
    f=tmp_path/'r.png';f.write_bytes(b'x');args=dict(reference=f,prompts={'front':'a'},output_dir=tmp_path/'out');args[field]=value
    with pytest.raises(IntegrationError):prepare_faceid_batch(**args)


def test_core_streamed_runner_actual_subprocess(tmp_path):
    import sys
    from forge.integrations.runner import run_streamed
    r=run_streamed([sys.executable,'-c',"import os;print(os.environ['FIXTURE_ENV'])"],
                  log_path=tmp_path/'log',env_extra={'FIXTURE_ENV':'streamed_ok'})
    assert r['ok'] and 'streamed_ok' in r['log']
    assert Path(r['status_path']).is_file()


def test_core_streamed_runner_timeout(tmp_path):
    import sys
    from forge.integrations.runner import run_streamed
    r=run_streamed([sys.executable,'-c','import time;print(123,flush=True);time.sleep(30)'],
                  log_path=tmp_path/'log',timeout_s=.1)
    assert not r['ok'] and r['status']=='timed_out' and '123' in r['log']


def test_staged_vace_opt_in_not_default(tmp_path):
    from forge.integrations.visual_jobs import prepare_vace_job
    ref=tmp_path/'r.png';ref.write_bytes(b'fixture')
    args=dict(prompt='fixture',output=tmp_path/'o.mp4',references=[ref])
    assert prepare_vace_job(**args)['parameters']['runtime_profile']=='upstream'
    assert prepare_vace_job(**args,runtime_profile='t4_dual_staged')['parameters']['runtime_profile']=='t4_dual_staged'
    with pytest.raises(IntegrationError):prepare_vace_job(**args,model='vace-14B',runtime_profile='t4_dual_staged')


def test_vace_staged_builder_reaches_real_driver_not_legacy_cpu_half(tmp_path,monkeypatch):
    import forge.integrations.visual_jobs as v
    from forge.gates.still_first import lock_stills
    ref=tmp_path/'r.png';ref.write_bytes(b'fixture');lock_stills(tmp_path,{'ref':str(ref)})
    output=tmp_path/'o.mp4';ckpt=tmp_path/'weights'
    for name in ['config.json','models_t5_umt5-xxl-enc-bf16.pth','Wan2.1_VAE.pth',
                 'google/umt5-xxl/spiece.model','diffusion_pytorch_model.safetensors']:
        p=ckpt/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'layout fixture, not actual weights')
    job=v.prepare_vace_job(prompt='fixture',output=output,references=[ref],runtime_profile='t4_dual_staged')
    seen={};monkeypatch.setattr(v,'preflight',lambda argv,**kw:seen.update(argv=argv))
    def fake_run(argv,**kw):return {'ok':True,'returncode':0}
    monkeypatch.setattr(v,'run',fake_run)
    r=v.execute_visual_job(job,root=Path(__file__).resolve().parents[1],project_dir=tmp_path,
                           ckpt_dir=ckpt,host_reviewed=True)
    assert 'vace_staged_driver.py' in seen['argv'][1]
    assert '--t5_cpu' not in seen['argv']
    assert not r['ok'] # A fixture process returning zero with no output is NOT success.


def test_angle_matrix_connected_to_real_faceid_batch(tmp_path):
    from forge.integrations.faceid import prepare_character_angle_batch
    ref=tmp_path/'r.png';ref.write_bytes(b'fixture')
    result=prepare_character_angle_batch(character='Fictional wizard',identifiers=['round glasses','scar'],
        outfit='charcoal wizard robes, scarlet lining',reference=ref,output_dir=tmp_path/'angles',
        existing=['front_close'])
    assert len(result['batch']['jobs'])==6
    assert all('scar' in j['prompt'] and 'round glasses' in j['prompt'] for j in result['batch']['jobs'])
    assert result['status']=='prepared_not_executed'


def test_voice_seed_experiment_preparation_never_sends(tmp_path,monkeypatch):
    import requests
    from forge.experiments.voice_seed_ab import prepare_voice_seed_ab
    monkeypatch.setattr(requests,'post',lambda *a,**k:pytest.fail('preparation must not send'))
    e=prepare_voice_seed_ab(text='A full sentence.',voice_id='fixture',voice_settings={'stability':.5},output_dir=tmp_path)
    assert e['characters_required']==32 and e['status']=='prepared_not_executed'
    assert [r['seed'] for r in e['parameters']['runs']]==[42,43]


def test_voice_seed_execution_respects_user_hold(tmp_path):
    from forge.experiments.voice_seed_ab import prepare_voice_seed_ab,execute_voice_seed_ab
    held(tmp_path)
    e=prepare_voice_seed_ab(text='A full sentence.',voice_id='fixture',voice_settings={'stability':.5},output_dir=tmp_path)
    with pytest.raises(SpendLocked):execute_voice_seed_ab(e,project_dir=tmp_path,api_key='unused',ledger=Ledger(tmp_path/'ledger.json'))
