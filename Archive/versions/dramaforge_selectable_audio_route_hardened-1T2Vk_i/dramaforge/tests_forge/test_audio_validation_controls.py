"""Control forwarding only, no GPU inference claim."""
import json
from pathlib import Path
import pytest
from forge.integrations.registry import IntegrationError
from forge.integrations.execute import execute_audio_job

@pytest.mark.parametrize('kw',[
 {'sample_steps':0},{'sample_steps':True},{'sample_steps':101},{'sample_steps':1.5},
 {'num_persistent_param_in_dit':-1},{'num_persistent_param_in_dit':False},
 {'num_persistent_param_in_dit':2.2},{'t5_cpu':'yes'}])
def test_invalid_validation_controls_fail_before_execution(tmp_path,kw):
 with pytest.raises(IntegrationError):
  execute_audio_job({},project_dir=tmp_path,root=tmp_path,ckpt_dir=tmp_path,
   wav2vec_dir=tmp_path,host_reviewed=True,**kw)

@pytest.mark.parametrize('backend',['multitalk','infinitetalk'])
def test_controls_reach_safe_argv(tmp_path,monkeypatch,backend):
 import forge.integrations.execute as ex
 from forge.gates.common import sha256_file
 from forge.gates.still_first import lock_stills
 root=tmp_path/'root';root.mkdir();ref=tmp_path/'ref';ref.write_bytes(b'fixture')
 audio=tmp_path/'audio';audio.write_bytes(b'fixture')
 project=tmp_path/'project';project.mkdir();lock_stills(project,{'fixture':str(ref)})
 weights=tmp_path/'weights';weights.mkdir();(weights/'fixture').write_bytes(b'NOT WEIGHTS')
 inp=tmp_path/'input.json';inp.write_text(json.dumps({'cond_video':str(ref),'cond_image':str(ref),'cond_audio':{'person1':str(audio)}}))
 out=tmp_path/'out.mp4';ckpt=weights/'fixture'
 job={'backend':backend,'argv':['python','entry.py','--input_json',str(inp),'--base_seed','42','--size',backend+'-480'],
      'frame_num':17,'expected_output':str(out),'reference_sha256_expected':sha256_file(ref),
      'audio_sha256_expected':{'person1':sha256_file(audio)}}
 monkeypatch.setattr(ex,'check_weight_layout',lambda *a,**k:{'layout_ok':True})
 monkeypatch.setattr(ex,'preflight',lambda *a,**k:None)
 calls=[]
 def fake_run(argv,**kwargs):
  calls.append(argv);out.write_bytes(b'NOT VIDEO');return {'ok':True}
 monkeypatch.setattr(ex,'run',fake_run)
 r=ex.execute_audio_job(job,project_dir=project,root=root,ckpt_dir=weights,wav2vec_dir=weights,
   infinitetalk_ckpt=ckpt,host_reviewed=True,sample_steps=4,num_persistent_param_in_dit=0,t5_cpu=True)
 argv=calls[0]
 assert argv[argv.index('--sample_steps')+1]=='4'
 assert argv[argv.index('--num_persistent_param_in_dit')+1]=='0'
 assert argv[argv.index('--save_file')+1]==str(out.with_suffix(''))
 assert '--t5_cpu' in argv and r['quality_status']=='unreviewed'
