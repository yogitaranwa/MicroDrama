"""Pinned upstream contract checks. These are not inference acceptance."""
import ast,json
from pathlib import Path
from forge.integrations.jobs import build_infinitetalk_input
from forge.integrations.plan_bridge import prepare_audio_driven_jobs
from forge.gates.common import sha256_file

def test_infinitetalk_image_uses_cond_video_alias(tmp_path):
 ref=tmp_path/'ref.jpg';ref.write_bytes(b'fixture');audio=tmp_path/'audio.wav';audio.write_bytes(b'fixture')
 out=tmp_path/'input.json';d=build_infinitetalk_input('speech',str(ref),{'person1':str(audio)},str(out))
 assert d['cond_video']==d['cond_image']==str(ref)
 assert json.loads(out.read_text())==d

def test_plan_bridge_uses_native_infinitetalk_schema(tmp_path):
 ref=tmp_path/'ref.jpg';ref.write_bytes(b'fixture');audio=tmp_path/'audio.wav';audio.write_bytes(b'fixture')
 job=prepare_audio_driven_jobs([dict(plan_n=1,seconds=.68,silent=False,prompt='speech',still_present=True,reference_still_path=str(ref),reference_still_sha256=sha256_file(ref))],{1:{'person1':str(audio)}},root=tmp_path,out_dir=tmp_path/'out',backend='infinitetalk',ckpt_dir=tmp_path,wav2vec_dir=tmp_path)[0]
 argv=job['argv'];d=json.loads(Path(argv[argv.index('--input_json')+1]).read_text())
 assert d['cond_video']==str(ref.resolve()) and job['frame_num']==17

def test_adapter_selects_correct_upstream_pipeline():
 import forge.integrations.audio_t4_driver as driver
 text=Path(driver.__file__).read_text();ast.parse(text)
 assert "'InfiniteTalkPipeline' if script.name == 'generate_infinitetalk.py'" in text
 assert "setattr(wan,pipeline_name,StagedPipeline)" in text

def test_both_quantized_backends_keep_cached_full_t5():
 import forge.integrations.audio_t4_driver as driver
 text=Path(driver.__file__).read_text()
 assert "if pipeline_name in ('InfiniteTalkPipeline', 'MultiTalkPipeline'):" in text
 assert "kwargs['quant'] = None" in text
 assert "kwargs['quant_dir'] = None" in text
