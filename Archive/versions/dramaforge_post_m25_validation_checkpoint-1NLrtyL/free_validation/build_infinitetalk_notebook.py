from pathlib import Path
import json,base64,zipfile,io
root=Path('/downloads/df15/dramaforge');bio=io.BytesIO()
with zipfile.ZipFile(bio,'w',zipfile.ZIP_DEFLATED) as z:
 for f in (root/'forge').rglob('*.py'):z.write(f,'dramaforge/'+str(f.relative_to(root)))
 z.write('/downloads/free_validation/Harry_Gryffindor_validation.jpg','reference.jpg')
 z.write('/downloads/free_validation/harry_validation_audio.wav','audio.wav')
payload=base64.b64encode(bio.getvalue()).decode()
metadata=json.load(open('/downloads/free_validation/audio_model_metadata.json'));metadata['MeiGen-AI/InfiniteTalk']=json.load(open('/downloads/free_validation/infinitetalk_model_metadata.json'))
download='''from huggingface_hub import snapshot_download
from pathlib import Path
TMP=Path('/tmp/infinitetalk_validation')
'''
for repo,folder,patterns in [('Wan-AI/Wan2.1-I2V-14B-480P','base',['config.json','Wan2.1_VAE.pth','models_clip_open-clip-xlm-roberta-large-vit-huge-14.pth','models_t5_umt5-xxl-enc-bf16.pth','google/umt5-xxl/*','xlm-roberta-large/*','LICENSE.txt']),('MeiGen-AI/InfiniteTalk','quant',['quant_models/infinitetalk_single_int8.safetensors','quant_models/infinitetalk_single_int8.json','single/infinitetalk.safetensors','README.md']),('TencentGameMate/chinese-wav2vec2-base','wav2vec',['config.json','preprocessor_config.json','pytorch_model.bin','README.md'])]:
 download+=f"snapshot_download({repo!r},revision={metadata[repo]['sha']!r},local_dir=str(TMP/{folder!r}),allow_patterns={patterns!r})\n"
execute='''import sys,json,hashlib
from pathlib import Path
TMP=Path('/tmp/infinitetalk_validation');ROOT=TMP/'dramaforge';sys.path.insert(0,str(ROOT))
from forge.gates.still_first import lock_stills
from forge.integrations.plan_bridge import prepare_audio_driven_jobs
from forge.integrations.execute import execute_audio_job
OUT=Path('/kaggle/working/infinitetalk_validation');project=TMP/'validation_project';project.mkdir(exist_ok=True)
ref=TMP/'reference.jpg';lock_stills(project,{'character:harry:approved':str(ref)})
render=[dict(plan_n=1,seconds=.68,silent=False,prompt='The same adult wizard speaks calmly. Static camera. Preserve the face, glasses and dark robe.',still_present=True,reference_still_path=str(ref),reference_still_sha256=hashlib.sha256(ref.read_bytes()).hexdigest())]
job=prepare_audio_driven_jobs(render,{1:{'person1':str(TMP/'audio.wav')}},root=ROOT,out_dir=OUT/'jobs',backend='infinitetalk',ckpt_dir=TMP/'base',wav2vec_dir=TMP/'wav2vec')[0]
(OUT/'prepared_job.json').write_text(json.dumps(job,indent=2))
r=execute_audio_job(job,project_dir=project,root=ROOT,ckpt_dir=TMP/'base',wav2vec_dir=TMP/'wav2vec',host_reviewed=True,timeout_s=1500,python=sys.executable,sample_steps=4,num_persistent_param_in_dit=0,t5_cpu=True,runtime_profile='t4_dual_quantized',quant='int8',quant_dir=TMP/'quant/quant_models/infinitetalk_single_int8.safetensors',infinitetalk_ckpt=TMP/'quant/single/infinitetalk.safetensors')
(OUT/'executor_result.json').write_text(json.dumps(r,indent=2))
if not r['ok']:raise RuntimeError('InfiniteTalk actual executor failed')
p=Path(job['expected_output']);(OUT/'output_receipt.json').write_text(json.dumps({'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'quality':'unreviewed'},indent=2))
print('ACTUAL_INFINITETALK_EXECUTOR_PASSED_UNREVIEWED',flush=True)
'''
code='''import os,sys,json,base64,zipfile,io
from pathlib import Path
OUT=Path('/kaggle/working/infinitetalk_validation');OUT.mkdir(exist_ok=True)
TMP=Path('/tmp/infinitetalk_validation');TMP.mkdir(exist_ok=True)
os.environ['HF_HOME']=str(TMP/'hf');os.environ['UV_CACHE_DIR']=str(TMP/'uvcache');os.environ['MPLBACKEND']='Agg';os.environ['PYTORCH_CUDA_ALLOC_CONF']='expandable_segments:True'
zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD))).extractall(TMP)
ROOT=TMP/'dramaforge';sys.path.insert(0,str(ROOT))
from forge.integrations.streaming_process import run_step
steps=[]
def cmd(args,cwd=None,timeout=1800):
 n='%02d'%len(steps);r=run_step(args,cwd=cwd,timeout_s=timeout,log_path=OUT/(n+'.log'),status_path=OUT/(n+'_status.json'))
 steps.append(r);(OUT/'steps.json').write_text(json.dumps(steps,indent=2))
 if r['status']!='passed':raise RuntimeError('step failed:'+n)
 return r
try:
 cmd([sys.executable,'-m','pip','install','uv']);uv=[sys.executable,'-m','uv']
 cmd(uv+['venv','--python','3.10',str(TMP/'env')]);py=str(TMP/'env/bin/python')
 cmd(uv+['pip','install','--python',py,'torch==2.5.1','torchvision==0.20.1','torchaudio==2.5.1','--index-url','https://download.pytorch.org/whl/cu124'])
 cmd(uv+['pip','install','--python',py,'diffusers==0.33.1','transformers==4.49.0','accelerate>=1.1.1','numpy<2','opencv-python-headless<4.12','easydict','ftfy','imageio','imageio-ffmpeg','einops','dashscope','pycocotools','matplotlib','onnxruntime','decord','scenedetect','moviepy==1.0.3','scikit-image','timm','beautifulsoup4','sentencepiece','protobuf','huggingface_hub<1','safetensors','tqdm','loguru','pyloudnorm','librosa','soundfile','optimum-quanto==0.2.6','kokoro','xfuser==0.4.1','xformers==0.0.28.post3'])
 repo=ROOT/'third_party/infinitetalk';repo.parent.mkdir(exist_ok=True)
 cmd(['git','clone','https://github.com/MeiGen-AI/InfiniteTalk',str(repo)])
 cmd(['git','checkout','50aa0a94184315407a991ae804d9b58d6d311ba8'],cwd=repo)
 cmd([py,'-c','import sys,runpy;sys.path.insert(0,'+repr(str(repo))+');runpy.run_path('+repr(str(repo/'generate_infinitetalk.py'))+',run_name="integration_import_preflight");print(123)'])
 (TMP/'download.py').write_text(DOWNLOAD_SCRIPT);cmd([py,str(TMP/'download.py')])
 (TMP/'execute.py').write_text(EXECUTE_SCRIPT);cmd([py,str(TMP/'execute.py')],timeout=1800)
 (OUT/'status.json').write_text(json.dumps({'status':'executor_passed_output_review_required'},indent=2))
except Exception as e:
 (OUT/'status.json').write_text(json.dumps({'status':'blocked','error':str(e)},indent=2));raise
'''
for k,v in [('PAYLOAD',payload),('DOWNLOAD_SCRIPT',download),('EXECUTE_SCRIPT',execute)]:code=code.replace(k,repr(v))
for n,s in [('main',code),('execute',execute),('download',download)]:compile(s,n,'exec')
nb={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'}},'cells':[{'cell_type':'markdown','metadata':{},'source':['# InfiniteTalk bounded real executor validation\nPrivate free trial17frames4steps with approved reference and a 1.2s crop of recovered existing v9 Chatterbox draft audio, not final voice acceptance. Experimental int8 twoT4 CPU-offload profile. Not E01 or lipsync acceptance.']},{'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':code.splitlines(True)}]}
p=Path('/downloads/free_validation/infinitetalk_executor_validation_PREPARED.ipynb');p.write_text(json.dumps(nb));print(p,p.stat().st_size)