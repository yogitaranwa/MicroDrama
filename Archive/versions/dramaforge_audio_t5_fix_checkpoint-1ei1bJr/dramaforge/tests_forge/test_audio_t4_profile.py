import pytest
from forge.integrations.audio_t4_driver import validate_audio_t4_argv
from forge.integrations.weight_layout import check_weight_layout

BASE=['python','generate_multitalk.py','--quant','int8','--num_persistent_param_in_dit','0','--t5_cpu','--sample_steps','4','--frame_num','17']
def test_explicit_tiny_profile():assert validate_audio_t4_argv(BASE)==BASE
@pytest.mark.parametrize('a',[
 ['python','generate_multitalk.py'],BASE+['--mode','streaming'],
 [x if x!='int8' else 'bad' for x in BASE],
 [x if x!='4' else '40' for x in BASE],
 [x if x!='17' else '377' for x in BASE],
 [x for x in BASE if x!='--t5_cpu'],BASE+['--quant','int8']])
def test_profile_refuses_unsafe_or_unbounded(a):
 with pytest.raises((ValueError,IndexError)):validate_audio_t4_argv(a)
@pytest.mark.parametrize('backend',['multitalk','infinitetalk'])
def test_quantized_layout_does_not_require_unused_full_shards(tmp_path,backend):
 import json
 root=tmp_path/'base';root.mkdir();wav=tmp_path/'wav';wav.mkdir()
 for f in ['config.json','models_t5_umt5-xxl-enc-bf16.pth','Wan2.1_VAE.pth',
 'google/umt5-xxl/spiece.model','models_clip_open-clip-xlm-roberta-large-vit-huge-14.pth']:
  p=root/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'FIXTURE NOT WEIGHTS')
 for f in ['config.json','preprocessor_config.json','model.safetensors']:(wav/f).write_bytes(b'FIXTURE')
 q=tmp_path/'quant'
 if backend=='multitalk':
  tensor=q/'quant_models/dit_model_int8.safetensors';mapping=q/'quant_models/dit_model_map_int8.json'
 else:q=q.with_suffix('.safetensors');tensor=q;mapping=q.with_suffix('.json')
 tensor.parent.mkdir(parents=True,exist_ok=True);tensor.write_bytes(b'FIXTURE');mapping.write_text(json.dumps({'fixture':{}}))
 result=check_weight_layout(backend,root,wav2vec_dir=wav,quant='int8',quant_dir=q)
 assert result['layout_ok'],result
 mapping.write_text('{}')
 assert not check_weight_layout(backend,root,wav2vec_dir=wav,quant='int8',quant_dir=q)['layout_ok']
