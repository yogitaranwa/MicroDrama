"""Opt-in cached-weight audio experiment, never a production acceptance claim.

Pinned upstream source is untouched. Two T4s: GPU1 encodes T5, GPU0 runs
CPU-offloaded quantized diffusion with the numerical portable-attention fallback.
The gated parent executor validates inputs/weight layout before invoking this.
"""
import argparse
import json
import os
import runpy
import sys
from pathlib import Path


def validate_audio_t4_argv(argv):
    if not isinstance(argv,list) or len(argv)<2:
        raise ValueError('explicit upstream argv required')
    def value(flag):
        if argv.count(flag)!=1:raise ValueError('exactly one '+flag+' required')
        return argv[argv.index(flag)+1]
    if value('--quant') not in ('int8','fp8'):raise ValueError('quantized runtime required')
    if value('--num_persistent_param_in_dit')!='0':raise ValueError('zero persistent DiT params required')
    if '--t5_cpu' not in argv:raise ValueError('T5 CPU branch required for explicit encoder adapter')
    if '--mode' in argv and value('--mode')!='clip':raise ValueError('streaming not allowed in tiny trial')
    if not 1<=int(value('--sample_steps'))<=10:raise ValueError('tiny trial requires1-10steps')
    if not 5<=int(value('--frame_num'))<=81:raise ValueError('tiny trial requires atmost81frames')
    return argv


def main():
    p=argparse.ArgumentParser();p.add_argument('--argv-json',required=True)
    p.add_argument('--project-dir',required=True);a=p.parse_args()
    from forge.guard.generation_hold import require_generation_open
    from forge.gates.enforce import enforce_render_allowed
    require_generation_open(project_dir=a.project_dir)
    enforce_render_allowed(a.project_dir,'proof')
    argv=validate_audio_t4_argv(json.loads(Path(a.argv_json).read_text()))
    script=Path(argv[1]).resolve()
    if script.name not in ('generate_multitalk.py','generate_infinitetalk.py'):
        raise SystemExit('only pinned audio CLIs supported')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    sys.path.insert(0,str(script.parent))
    import torch
    if torch.cuda.device_count()<2 or any(torch.cuda.get_device_capability(i)[0]!=7 for i in (0,1)):
        raise SystemExit('explicit twoTuringGPUs required')
    if torch.distributed.is_initialized():raise SystemExit('distributed runtime not supported')
    import wan
    from forge.integrations.t4_attention import install_portable_attention,force_fp16_configs_for_t4
    patched=install_portable_attention();force_fp16_configs_for_t4()
    pipeline_name = 'InfiniteTalkPipeline' if script.name == 'generate_infinitetalk.py' else 'MultiTalkPipeline'
    if pipeline_name in ('InfiniteTalkPipeline', 'MultiTalkPipeline'):
        # Explicit validation downloads full T5 plus quantized DiT, not quantized T5.
        # Keep the full cached T5 in fp16 on GPU1 instead. No fabricated weights.
        import wan.multitalk as audio_pipeline
        original_t5 = audio_pipeline.T5EncoderModel
        def full_precision_t5(*args, **kwargs):
            kwargs['quant'] = None
            kwargs['quant_dir'] = None
            return original_t5(*args, **kwargs)
        audio_pipeline.T5EncoderModel = full_precision_t5
        print('AUDIO_FULL_FP16_T5_WITH_QUANTIZED_DIT', pipeline_name, flush=True)
    original=getattr(wan, pipeline_name)
    class T5OnSecondGPU:
        def __init__(self,encoder):
            self.encoder=encoder;encoder.model.to(torch.device('cuda:1'))
        def __call__(self,texts,device):
            with torch.no_grad():result=self.encoder(texts,torch.device('cuda:1'))
            if not all(torch.isfinite(t).all() for t in result):raise RuntimeError('nonfinite T5 encoding')
            return [t.to(device) for t in result]
    class StagedPipeline(original):
        def __init__(self,*args,**kwargs):
            if kwargs.get('t5_cpu') is not True:raise RuntimeError('explicit t5_cpu required')
            super().__init__(*args,**kwargs)
            self.text_encoder=T5OnSecondGPU(self.text_encoder)
            from forge.integrations.audio_context_adapter import install_context_adapter
            install_context_adapter(self.model)
            if pipeline_name == 'MultiTalkPipeline':
                from forge.integrations.audio_norm_adapter import install_audio_norm_adapter
                install_audio_norm_adapter(self.model)
                print('AUDIO_NORM_INPUT_DTYPE_ADAPTER', flush=True)
            print("AUDIO_SINGLETON_TEXT_CONTEXT_ADAPTER", flush=True)
            print('AUDIO_T5_PLACED_GPU1',flush=True)
    setattr(wan,pipeline_name,StagedPipeline)
    print('AUDIO_T4_EXPERIMENTAL',patched,flush=True)
    sys.argv=argv[1:]
    runpy.run_path(str(script),run_name='__main__')

if __name__=='__main__':main()
