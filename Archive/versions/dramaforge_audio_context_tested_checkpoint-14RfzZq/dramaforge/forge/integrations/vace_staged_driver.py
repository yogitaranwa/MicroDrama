"""Generalized Version4 memory layout, cached weights only.

The original upstream-sample run succeeded on two T4s. This generalized
project/reference route has NOT been inference-validated. Source files stay intact.
"""
import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    for n in ('job','root','project-dir','checkpoint'):p.add_argument('--'+n,required=True)
    p.add_argument('--mode',choices=['proof','episode'],required=True)
    a=p.parse_args()
    from forge.guard.generation_hold import require_generation_open
    require_generation_open(project_dir=a.project_dir)
    from forge.gates.enforce import enforce_render_allowed
    enforce_render_allowed(a.project_dir,a.mode)
    from forge.integrations.visual_jobs import prepare_vace_job
    job=json.loads(Path(a.job).read_text())
    fresh=prepare_vace_job(output=job['expected_output'],**job['parameters'])
    if fresh['input_sha256_expected'] != job.get('input_sha256_expected'):
        raise SystemExit('VACE input changed')
    from forge.gates.still_first import require_still_lock
    lock=require_still_lock(a.project_dir)
    locked={str(Path(v['path']).resolve()):v['sha256'] for v in lock['stills'].values()}
    for ref in fresh['parameters']['references']:
        if locked.get(ref)!=fresh['input_sha256_expected'][ref]:
            raise SystemExit('reference not in current still lock')
    params=fresh['parameters']
    if params['runtime_profile']!='t4_dual_staged' or params['model']!='vace-1.3B':
        raise SystemExit('this experimental path only accepts explicit dual T4 VACE1.3B jobs')
    os.environ['MPLBACKEND']='Agg'
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TRANSFORMERS_OFFLINE']='1'
    sys.path.insert(0,str(Path(a.root)/'third_party/vace/vace'))
    import torch
    if torch.cuda.device_count()<2 or any(torch.cuda.get_device_capability(i)[0]!=7 for i in (0,1)):
        raise SystemExit('explicit two-Turing-GPU layout required; no silent CPU-half fallback')
    if torch.distributed.is_initialized() and torch.distributed.get_world_size()!=1:
        raise SystemExit('staged driver is single-process only')
    from models.wan import WanVace
    from models.wan.configs import WAN_CONFIGS
    from wan.utils.utils import cache_video
    from forge.integrations.t4_attention import install_portable_attention
    patched=install_portable_attention()
    cfg=copy.deepcopy(WAN_CONFIGS['vace-1.3B']);cfg.param_dtype=torch.float16;cfg.t5_dtype=torch.float16
    print('STAGE_MODEL_CONSTRUCTION',flush=True)
    pipe=WanVace(cfg,a.checkpoint,t5_cpu=True)
    pipe.model.cpu().to(dtype=torch.float16);torch.cuda.empty_cache()
    class SeparateGpuEncoder:
        def __init__(self,original):
            self.original=original
            self.original.model.to(torch.device('cuda:1'))
        def __call__(self,texts,device):
            with torch.no_grad():result=self.original(texts,torch.device('cuda:1'))
            if not all(torch.isfinite(t).all() for t in result):raise RuntimeError('non-finite T5 encoding')
            return [t.to(device) for t in result]
    pipe.text_encoder=SeparateGpuEncoder(pipe.text_encoder)
    # Upstream size tuple is width,height. 480p defaults to the vertical proof layout.
    size=(832,480) if params['size']=='832*480' else (480,832)
    src,mask,refs=pipe.prepare_source([params['source_video']],[params['source_mask']],
        [params['references']],params['frames'],size,0)
    print('STAGE_GENERATE',flush=True);started=time.monotonic()
    vid=pipe.generate(params['prompt'],src,mask,refs,size=size,frame_num=params['frames'],
        shift=16,sample_solver='unipc',sampling_steps=params['steps'],guide_scale=5.0,
        seed=params['seed'],offload_model=True)
    output=fresh['expected_output']
    cache_video(tensor=vid[None],save_file=output,fps=16,nrow=1,normalize=True,value_range=(-1,1))
    from forge.gates.common import sha256_file
    Path(output+'.inference.json').write_text(json.dumps(dict(status='generated_unreviewed',
        runtime_profile=params['runtime_profile'],sha256=sha256_file(output),frames=params['frames'],
        seed=params['seed'],steps=params['steps'],seconds=time.monotonic()-started,
        patched_attention=patched,input_sha256=fresh['input_sha256_expected']),indent=2))
    print('VACE_STAGED_GENERATED_UNREVIEWED',flush=True)

if __name__=='__main__':main()
