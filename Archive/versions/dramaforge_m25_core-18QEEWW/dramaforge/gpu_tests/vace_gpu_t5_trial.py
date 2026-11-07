"""Prepared VACE retry with missing import fixes and streamed process logs.
Not launched until the original run has ended and its evidence is recovered.
"""
import os,sys,subprocess,json,time,base64
from pathlib import Path
OUT=Path('/kaggle/working/vace_trial');OUT.mkdir(exist_ok=True)
TMP=Path('/tmp/vace_trial');TMP.mkdir(exist_ok=True)
os.environ['MPLBACKEND']='Agg'
os.environ['HF_HOME']=str(TMP/'hf')
os.environ['UV_CACHE_DIR']=str(TMP/'uvcache')
(TMP/'portable_attention.py').write_text('"""Opt-in portable attention experiment for pinned audio-driven Wan repos.\n\nUses query chunks and each sequence\'s real key length. This avoids requiring\nFlashAttention2 on T4. It is a numerical fallback, NOT a quality/performance\nclaim. No upstream files are changed. Single-device only; distributed and\nlocal-window attention are refused rather than approximated silently.\n"""\nclass IntegrationError(RuntimeError): pass\n\n\ndef portable_attention(q, k, v, q_lens=None, k_lens=None, dropout_p=0.,\n                       softmax_scale=None, q_scale=None, causal=False,\n                       window_size=(-1, -1), deterministic=False,\n                       dtype=None, version=None, chunk_size=256):\n    import torch\n    import torch.nn.functional as F\n    if window_size != (-1, -1):\n        raise IntegrationError(\'portable attention does not support local windows\')\n    if dropout_p:\n        raise IntegrationError(\'portable inference attention requires dropout_p=0\')\n    if q.ndim != 4 or k.ndim != 4 or v.ndim != 4:\n        raise IntegrationError(\'attention requires [batch, sequence, heads, dim]\')\n    if q.shape[0] != k.shape[0] or k.shape[:3] != v.shape[:3] or q.shape[2] != k.shape[2]:\n        raise IntegrationError(\'attention batch/head/key/value dimensions mismatch\')\n    if not isinstance(chunk_size, int) or chunk_size < 1:\n        raise IntegrationError(\'chunk_size must be a positive integer\')\n    batch, lq = q.shape[:2]\n    lk = k.shape[1]\n    q_lengths = [lq] * batch if q_lens is None else [int(n) for n in q_lens]\n    k_lengths = [lk] * batch if k_lens is None else [int(n) for n in k_lens]\n    if len(q_lengths) != batch or len(k_lengths) != batch:\n        raise IntegrationError(\'one attention length per batch item is required\')\n    if any(not 0 < n <= lq for n in q_lengths) or any(not 0 < n <= lk for n in k_lengths):\n        raise IntegrationError(\'attention lengths must be positive and within tensors\')\n    # Wan rotary embedding returns float32 q/k even when v is fp16.\n    # SDPA requires one dtype; upstream FlashAttention finally uses v\'s half\n    # dtype. Preserve that behavior instead of failing on mixed q/k/v.\n    half_types = (torch.float16, torch.bfloat16)\n    compute_dtype = v.dtype if v.dtype in half_types else (dtype or v.dtype)\n    out = torch.zeros((batch,lq,q.shape[2],v.shape[-1]),device=q.device,dtype=q.dtype)\n    for b in range(batch):\n        kl = k_lengths[b]\n        keys = k[b,:kl].transpose(0,1).unsqueeze(0)\n        vals = v[b,:kl].transpose(0,1).unsqueeze(0)\n        for start in range(0,q_lengths[b],chunk_size):\n            end = min(start+chunk_size,q_lengths[b])\n            queries=q[b,start:end].transpose(0,1).unsqueeze(0)\n            queries, keys, vals = (queries.to(compute_dtype),\n                                   keys.to(compute_dtype), vals.to(compute_dtype))\n            if q_scale is not None:\n                queries=queries*q_scale\n            mask=None\n            if causal:\n                mask = (torch.arange(kl,device=q.device)[None,:] <=\n                        torch.arange(start,end,device=q.device)[:,None])\n            kwargs={} if softmax_scale is None else {\'scale\':softmax_scale}\n            chunk=F.scaled_dot_product_attention(queries,keys,vals,\n                     attn_mask=mask,dropout_p=0.,is_causal=False,**kwargs)\n            out[b,start:end]=chunk.squeeze(0).transpose(0,1).to(out.dtype)\n    return out\n\n\ndef install_portable_attention():\n    """Patch imported aliases, not source files. Call after importing Wan.\n    Explicit opt-in is required; CUDA distributed initialization is refused."""\n    import sys\n    import torch\n    if torch.distributed.is_initialized() and torch.distributed.get_world_size() != 1:\n        raise IntegrationError(\'portable attention is single-device only\')\n    import wan.modules.attention as module\n    original=module.flash_attention\n    replaced=[]\n    for name,obj in list(sys.modules.items()):\n        if name.startswith(\'wan.\') and getattr(obj,\'flash_attention\',None) is original:\n            setattr(obj,\'flash_attention\',portable_attention)\n            replaced.append(name)\n    if not replaced:\n        raise IntegrationError(\'no Wan flash_attention aliases found\')\n    return replaced\n\n\ndef force_fp16_configs_for_t4():\n    """Explicit experimental dtype override after Wan import; no source edit.\n    T4 has no native bf16 support. This is not equivalent to validated output."""\n    import torch\n    from wan.configs import WAN_CONFIGS\n    if not torch.cuda.is_available():\n        raise IntegrationError(\'dtype override requires an actual CUDA host\')\n    if torch.cuda.get_device_capability()[0] != 7:\n        raise IntegrationError(\'Turing-only override requested on a different GPU\')\n    updated=[]\n    for key, cfg in WAN_CONFIGS.items():\n        for name in (\'param_dtype\', \'t5_dtype\', \'clip_dtype\'):\n            if hasattr(cfg,name):\n                setattr(cfg,name,torch.float16)\n        updated.append(key)\n    return updated\n')
(TMP/'infer_vace.py').write_text('"""Experimental T4 execution of pinned VACE library, no source-file patching."""\nimport sys,json,time,hashlib,faulthandler\nfaulthandler.enable()\nfaulthandler.dump_traceback_later(300,repeat=True)\nprint("STAGE_IMPORT_TORCH",flush=True)\nfrom pathlib import Path\nimport torch\nROOT=Path(\'/tmp/vace_trial\')\nsys.path.insert(0,str(ROOT/\'VACE/vace\'))\nprint("STAGE_IMPORT_VACE",flush=True)\nfrom models.wan import WanVace\nfrom models.wan.configs import WAN_CONFIGS\nfrom wan.utils.utils import cache_video\n# Portable attention has separate numerical evidence; model quality remains unverified.\nexec((ROOT/\'portable_attention.py\').read_text(),globals())\npatched=install_portable_attention()\nq=torch.randn(1,17,2,8,device=\'cuda\',dtype=torch.float32)\nk=torch.randn_like(q)\nv=torch.randn(1,17,2,8,device=\'cuda\',dtype=torch.float16)\na=portable_attention(q,k,v,chunk_size=7)\nb=torch.nn.functional.scaled_dot_product_attention(q.half().transpose(1,2),k.half().transpose(1,2),v.transpose(1,2)).transpose(1,2)\ntorch.testing.assert_close(a,b.float(),rtol=.02,atol=.002)\nprint(\'MIXED_DTYPE_GPU_CHECK_PASSED\',flush=True)\nfor cfg in WAN_CONFIGS.values():\n cfg.param_dtype=torch.float16\n cfg.t5_dtype=torch.float16\nprint(\'PATCHED_ATTENTION\',patched,flush=True)\nout=Path(\'/kaggle/working/vace_trial\')\nckpt=ROOT/\'weights\'\nfrom huggingface_hub import snapshot_download\nprint(\'STAGE_DOWNLOAD_WEIGHTS\',flush=True)\nsnapshot_download(\'Wan-AI/Wan2.1-VACE-1.3B\',revision=\'574e6a744642ce3bee319afc31496b88bde8aac4\',local_dir=str(ckpt),allow_patterns=[\'config.json\',\'diffusion_pytorch_model.safetensors\',\'Wan2.1_VAE.pth\',\'models_t5_umt5-xxl-enc-bf16.pth\',\'google/umt5-xxl/*\',\'LICENSE.txt\'])\nprint(\'VACE_WEIGHTS_READY\',flush=True)\nprint(\'STAGE_MODEL_CONSTRUCTION\',flush=True)\npipe=WanVace(WAN_CONFIGS[\'vace-1.3B\'],str(ckpt),t5_cpu=True)\nprint(\'VACE_MODEL_LOADED\',flush=True)\nassert torch.cuda.device_count() >= 2, \'Two GPUs needed for explicit T5 placement\'\n# Source-preserving adapter: the public encoder API returns one tensor per text.\n# Keep VACE on GPU0, place its otherwise CPU-half T5 on GPU1. Return tensors\n# on the requested device so WanVace\'s existing t5_cpu branch stays unchanged.\nclass SeparateGpuEncoder:\n def __init__(self, original):\n  self.original=original\n  self.original.model.to(torch.device(\'cuda:1\'))\n def __call__(self,texts,device):\n  print(\'T5_ENCODE_GPU1_START\',flush=True)\n  with torch.no_grad():\n   result=self.original(texts,torch.device(\'cuda:1\'))\n  result=[t.to(device) for t in result]\n  assert all(torch.isfinite(t).all() for t in result), \'non-finite T5 encoding\'\n  print(\'T5_ENCODE_GPU1_DONE\',flush=True)\n  return result\npipe.text_encoder=SeparateGpuEncoder(pipe.text_encoder)\nprint(\'T5_PLACED_GPU1\',torch.cuda.memory_allocated(1),flush=True)\n# Official example reference is a technical capability test, not an episode asset.\nref=str(ROOT/\'VACE/assets/images/girl.png\')\nassert Path(ref).is_file(),ref\nsrc,mask,refs=pipe.prepare_source([None],[None],[[ref]],17,(480,832),0)\nprompt=\'A girl stands in a quiet courtyard. She slowly turns her head toward the camera. Static camera, natural daylight.\'\nt=time.time()\nvid=pipe.generate(prompt,src,mask,refs,size=(480,832),frame_num=17,shift=16,sample_solver=\'unipc\',sampling_steps=8,guide_scale=5.0,seed=42,offload_model=True)\np=out/\'vace_reference_trial.mp4\'\ncache_video(tensor=vid[None],save_file=str(p),fps=16,nrow=1,normalize=True,value_range=(-1,1))\n(out/\'inference.json\').write_text(json.dumps({\'status\':\'generated_not_visually_reviewed\',\'frames\':17,\'steps\':8,\'seed\':42,\'seconds\':time.time()-t,\'sha256\':hashlib.sha256(p.read_bytes()).hexdigest(),\'experimental\':\'fp16 + portable attention on T4\',\'reference\':ref,\'prompt\':prompt},indent=2))\nprint(\'VACE_REFERENCE_TRIAL_GENERATED\',flush=True)\n')
steps=[]
"""Stream real subprocess progress to disk with bounded process-group cleanup.

No cloud operations or model execution occur on import. Call only in an
approved host workflow. Logs may contain task input; keep them private.
"""
import json
import os
import selectors
import signal
import subprocess
import time
from pathlib import Path


def run_step(argv, *, log_path, status_path, timeout_s, cwd=None, emit=print):
    if timeout_s <= 0:
        raise ValueError('timeout must be positive')
    log_path, status_path = Path(log_path), Path(status_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    env = dict(os.environ, PYTHONUNBUFFERED='1')
    record = {'argv': [str(a) for a in argv], 'status': 'starting',
              'log': str(log_path), 'timeout_s': timeout_s}
    def save(**values):
        record.update(values)
        status_path.write_text(json.dumps(record, indent=2))
    save()
    proc = subprocess.Popen(record['argv'], cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    save(status='running', pid=proc.pid)
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    timed_out = False
    try:
        with log_path.open('wb') as log:
            while sel.get_map():
                remaining = timeout_s - (time.monotonic() - started)
                if remaining <= 0:
                    timed_out = True
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                    # Children can outlive a wrapper that already exited.
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                for key, _ in sel.select(min(1.0, remaining)):
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        sel.unregister(key.fileobj)
                        continue
                    log.write(data)
                    log.flush()
                    emit(data.decode('utf-8', errors='replace'), end='', flush=True)
            code = proc.wait(timeout=10)
        save(status='timed_out' if timed_out else ('passed' if code == 0 else 'failed'),
             returncode=code, seconds=round(time.monotonic()-started, 2))
    except BaseException as exc:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=10)
        save(status='interrupted', error=type(exc).__name__)
        raise
    finally:
        sel.close()
        proc.stdout.close()
    return record

def cmd(args,cwd=None,timeout=1800):
 name=f'{len(steps):02d}'
 result=run_step(args,cwd=cwd,timeout_s=timeout,
     log_path=OUT/f'{name}.log',status_path=OUT/f'{name}_status.json')
 steps.append(result)
 (OUT/'steps.json').write_text(json.dumps(steps,indent=2))
 print('STEP',name,result['status'],flush=True)
 if result['status'] != 'passed':
  raise RuntimeError('step failed: '+name+' '+result['status'])
 return result

try:
 cmd([sys.executable,'-m','pip','install','uv'])
 uv=[sys.executable,'-m','uv']
 cmd(uv+['venv','--python','3.10',str(TMP/'env')])
 py=str(TMP/'env/bin/python')
 cmd(uv+['pip','install','--python',py,'torch==2.5.1','torchvision==0.20.1','--index-url','https://download.pytorch.org/whl/cu124'])
 cmd(uv+['pip','install','--python',py,'diffusers==0.33.1','transformers==4.49.0','accelerate','numpy<2','opencv-python-headless<4.12','easydict','ftfy','imageio','imageio-ffmpeg','einops','dashscope','pycocotools','matplotlib','onnxruntime','decord','scikit-image','timm','beautifulsoup4','sentencepiece','protobuf','huggingface_hub','safetensors','tqdm'])
 cmd(['git','clone','https://github.com/ali-vilab/VACE',str(TMP/'VACE')])
 cmd(['git','checkout','48eb44f1c4be87cc65a98bff985a26976841e9f3'],cwd=TMP/'VACE')
 cmd(['git','clone','https://github.com/Wan-Video/Wan2.1',str(TMP/'Wan2.1')])
 cmd(['git','checkout','9737cba9c1c3c4d04b33fcad41c111989865d315'],cwd=TMP/'Wan2.1')
 # No dependency resolution may install unsupported flash-attn behind our back.
 cmd(uv+['pip','install','--python',py,'--no-deps',str(TMP/'Wan2.1')])
 try:
  cmd([py,str(TMP/'VACE/vace/vace_wan_inference.py'),'--help'],cwd=TMP/'VACE')
 except RuntimeError as e:
  print('CLI_HELP_BLOCKED_TRY_CORE_LIBRARY',str(e),flush=True)
 cmd([py,str(TMP/'infer_vace.py')],cwd=TMP/'VACE',timeout=2700)
 (OUT/'status.json').write_text(json.dumps({'status':'inference_subprocess_passed','next':'visual review required'},indent=2))
 print('VACE_TRIAL_SUBPROCESS_PASSED',flush=True)
except Exception as e:
 (OUT/'status.json').write_text(json.dumps({'status':'blocked','error':str(e)},indent=2))
 print('VACE_TRIAL_BLOCKED',str(e),flush=True)
 raise
