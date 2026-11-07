"""Local contract/gate tests only. No inference or quality claims."""
from pathlib import Path
import pytest
from forge.gates.common import GateLocked
from forge.gates.still_first import lock_stills
from forge.integrations.registry import IntegrationError
import forge.integrations.visual_jobs as v

ROOT = str(Path(__file__).resolve().parents[1])

def assets(tmp_path):
    ref=tmp_path/'ref.png';ref.write_bytes(b'reference test fixture')
    return ref


def test_vace_validation(tmp_path):
    ref=assets(tmp_path)
    for args in ({'frames':16},{'steps':0},{'size':'720p'},{'seed':-1},
                 {'source_mask':str(ref)}, {'model':'other'}):
        with pytest.raises(IntegrationError):
            v.prepare_vace_job(prompt='test',output=tmp_path/'out.mp4',references=[ref],**args)
    with pytest.raises(IntegrationError):
        v.prepare_vace_job(prompt='test',output=tmp_path/'out.mp4')


def test_pulid_validation(tmp_path):
    ref=assets(tmp_path)
    for args in ({'height':63},{'id_scale':float('nan')},{'seed':-1}):
        with pytest.raises(IntegrationError):
            v.prepare_pulid_job(prompt='test',reference=ref,output=tmp_path/'o.png',**args)


def test_fresh_gates_and_hashes(tmp_path):
    ref=assets(tmp_path)
    job=v.prepare_vace_job(prompt='test',output=tmp_path/'out.mp4',references=[ref])
    with pytest.raises(IntegrationError,match='reviewed'):
        v.execute_visual_job(job,project_dir=tmp_path,root=ROOT)
    with pytest.raises(GateLocked):
        v.execute_visual_job(job,project_dir=tmp_path,root=ROOT,host_reviewed=True)
    lock_stills(tmp_path,{'ref':str(ref)})
    ref.write_bytes(b'changed')
    with pytest.raises(GateLocked,match='changed'):
        v.execute_visual_job(job,project_dir=tmp_path,root=ROOT,host_reviewed=True)


@pytest.mark.parametrize('backend',['vace','pulid'])
def test_executor_builds_safe_argv_and_marks_unreviewed(tmp_path,monkeypatch,backend):
    ref=assets(tmp_path);out=tmp_path/('o.mp4' if backend=='vace' else 'o.png')
    lock_stills(tmp_path,{'ref':str(ref)})
    if backend=='vace':
        job=v.prepare_vace_job(prompt='test',output=out,references=[ref],steps=8)
    else:
        job=v.prepare_pulid_job(prompt='test',reference=ref,output=out)
    job['argv']=['not','trusted']
    ckpt=tmp_path/'weights';ckpt.mkdir();(ckpt/'fixture').write_bytes(b'x')
    seen={}
    monkeypatch.setattr(v,'preflight',lambda argv,**kw:seen.update(argv=argv,preflight=kw))
    def fake_run(argv,**kwargs):
        out.write_bytes(b'not real media: local test fixture')
        return {'ok':True,'returncode':0}
    monkeypatch.setattr(v,'run',fake_run)
    r=v.execute_visual_job(job,project_dir=tmp_path,root=ROOT,ckpt_dir=ckpt,
                           driver_dir=tmp_path,host_reviewed=True)
    assert r['ok'] and r['quality_status']=='unreviewed'
    assert seen['argv'][:2]!=job['argv'][:2]
    assert seen['preflight']['need_cuda'] is True
    if backend=='vace':
        from forge.integrations.contracts import parser_from_source
        parser=parser_from_source(Path(ROOT)/'third_party/vace/vace/vace_wan_inference.py',
            {'WAN_CONFIGS':{'vace-1.3B':None,'vace-14B':None},'SIZE_CONFIGS':{'480p':None,'480*832':None,'832*480':None}})
        args=parser.parse_args(seen['argv'][2:])
        assert args.ckpt_dir==str(ckpt) and args.frame_num==17 and args.sample_steps==8
    with pytest.raises(IntegrationError,match='already exists'):
        v.execute_visual_job(job,project_dir=tmp_path,root=ROOT,host_reviewed=True)


def test_unlocked_reference_refused(tmp_path):
    ref=assets(tmp_path);other=tmp_path/'other.png';other.write_bytes(b'other')
    lock_stills(tmp_path,{'other':str(other)})
    j=v.prepare_pulid_job(prompt='test',reference=ref,output=tmp_path/'o.png')
    with pytest.raises(GateLocked,match='not in the current'):
        v.execute_visual_job(j,project_dir=tmp_path,root=ROOT,host_reviewed=True)


def test_source_video_hash_is_checked(tmp_path):
    ref=assets(tmp_path);source=tmp_path/'src.mp4';source.write_bytes(b'source')
    lock_stills(tmp_path,{'ref':str(ref)})
    job=v.prepare_vace_job(prompt='test',output=tmp_path/'out.mp4',references=[ref],source_video=source)
    source.write_bytes(b'changed source')
    with pytest.raises(GateLocked,match='changed'):
        v.execute_visual_job(job,project_dir=tmp_path,root=ROOT,host_reviewed=True)


def test_missing_weights_and_false_success_refused(tmp_path,monkeypatch):
    ref=assets(tmp_path);out=tmp_path/'out.mp4'
    lock_stills(tmp_path,{'ref':str(ref)})
    job=v.prepare_vace_job(prompt='test',output=out,references=[ref])
    with pytest.raises(IntegrationError,match='checkpoint'):
        v.execute_visual_job(job,project_dir=tmp_path,root=ROOT,host_reviewed=True)
    ckpt=tmp_path/'weights';ckpt.mkdir();(ckpt/'fixture').write_bytes(b'x')
    monkeypatch.setattr(v,'preflight',lambda *a,**kw:None)
    monkeypatch.setattr(v,'run',lambda *a,**kw:{'ok':True,'returncode':0})
    result=v.execute_visual_job(job,project_dir=tmp_path,root=ROOT,host_reviewed=True,ckpt_dir=ckpt)
    assert result['ok'] is False and result['quality_status']=='failed'


def test_render_mode_and_dimensions_revalidated(tmp_path):
    ref=assets(tmp_path);lock_stills(tmp_path,{'ref':str(ref)})
    job=v.prepare_pulid_job(prompt='test',reference=ref,output=tmp_path/'o.png')
    job['parameters']['height']=63
    with pytest.raises(IntegrationError):
        v.execute_visual_job(job,project_dir=tmp_path,root=ROOT,host_reviewed=True)
    job['parameters']['height']=1024
    with pytest.raises(GateLocked):
        v.execute_visual_job(job,project_dir=tmp_path,root=ROOT,host_reviewed=True,mode='episode')


def test_infinitetalk_explicit_checkpoint_matches_upstream(tmp_path):
    from forge.integrations.jobs import infinitetalk_cli
    from forge.integrations.contracts import parser_from_source
    inp=tmp_path/'input.json';inp.write_text('{}')
    ckpt=tmp_path/'infinitetalk.safetensors';ckpt.write_bytes(b'fixture only')
    argv=infinitetalk_cli(ROOT,str(inp),'/base','/wav','o.mp4',infinitetalk_ckpt=str(ckpt))
    parser=parser_from_source(Path(ROOT)/'third_party/infinitetalk/generate_infinitetalk.py',
        {'WAN_CONFIGS':{'infinitetalk-14B':None},'SIZE_CONFIGS':{'infinitetalk-480':None}})
    assert parser.parse_args(argv[2:]).infinitetalk_dir == str(ckpt)


def test_preflight_checks_script_with_absolute_python(tmp_path):
    from forge.integrations.runner import preflight
    with pytest.raises(IntegrationError,match='entrypoint not found'):
        preflight(['/tmp/env/bin/python','/missing/test.py'])


def test_checkpoint_inventory_never_calls_empty_folder_ready(tmp_path):
    from forge.integrations.weight_layout import check_weight_layout
    r=check_weight_layout('vace',tmp_path)
    assert r['layout_ok'] is False
    assert any('diffusion_pytorch_model' in s for s in r['errors'])
    assert r['verification']=='presence_only_not_authenticity_or_inference'


def test_multitalk_wrong_index_and_path_escape_reported(tmp_path):
    import json
    from forge.integrations.weight_layout import check_weight_layout
    index=tmp_path/'diffusion_pytorch_model.safetensors.index.json'
    index.write_text(json.dumps({'weight_map':{'x':'../outside.safetensors'}}))
    r=check_weight_layout('multitalk',tmp_path)
    assert any('escapes' in x for x in r['errors'])
    assert any('merged index' in x for x in r['errors'])


def test_complete_vace_layout_still_not_inference_claim(tmp_path):
    from forge.integrations.weight_layout import check_weight_layout
    for name in ['config.json','models_t5_umt5-xxl-enc-bf16.pth','Wan2.1_VAE.pth',
                 'google/umt5-xxl/spiece.model','diffusion_pytorch_model.safetensors']:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
    assert check_weight_layout('vace',tmp_path)['layout_ok'] is True
