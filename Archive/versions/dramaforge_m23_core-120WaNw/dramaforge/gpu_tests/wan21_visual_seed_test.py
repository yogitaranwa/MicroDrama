# Controlled visual-only seed test, official previously authorized Wan2.1 route.
import os
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
import json, time, hashlib
from pathlib import Path
import torch
from diffusers import WanPipeline
from diffusers.utils import export_to_video

OUT = Path('/kaggle/working/seed_visual_test')
OUT.mkdir(exist_ok=True)
PROMPT = ('Cinematic photorealistic vertical video. One adult platinum-blonde woman '
          'with a tidy braid, emerald ball gown and black travelling cloak, on a '
          'stone castle corridor lit by warm amber candles. Medium close-up, '
          'stationary camera. She turns her eyes toward a sound offscreen and '
          'raises one hand slightly. Preserve her face, braid, gown and cloak. '
          'One restrained action, no speaking, no text, no other person.')
NEG = 'cartoon, anime, text, subtitles, watermark, deformed hands, extra fingers, blurry face, low quality'
CONTROLS = {'model':'Wan-AI/Wan2.1-T2V-1.3B-Diffusers', 'prompt':PROMPT,
            'negative_prompt':NEG,'height':832,'width':480,'num_frames':33,
            'num_inference_steps':20,'guidance_scale':5.0,'fps':16,
            'seeds':[42,43],'audio':False,
            'scope':'visual sensitivity only; cannot diagnose native voice pitch or other models',
            'reference_conditioning':False,
            'limitation':'text-to-video does not pin identity to the approved image bank'}
(OUT/'controls.json').write_text(json.dumps(CONTROLS,indent=2))
assert torch.cuda.is_available(), 'No GPU: stop instead of switching routes'
torch.set_grad_enabled(False)
pipe = WanPipeline.from_pretrained(CONTROLS['model'], torch_dtype=torch.float16)
pipe.enable_model_cpu_offload()
pipe.vae.enable_tiling()
results=[]
for seed in CONTROLS['seeds']:
    t0=time.time()
    frames=pipe(prompt=PROMPT,negative_prompt=NEG,height=832,width=480,
                num_frames=33,num_inference_steps=20,guidance_scale=5.0,
                generator=torch.Generator('cpu').manual_seed(seed)).frames[0]
    out=OUT/f'seed_{seed}.mp4'
    export_to_video(frames,str(out),fps=16)
    results.append({'seed':seed,'file':out.name,'seconds':round(time.time()-t0,1),
                    'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
                    'status':'generated_not_visually_reviewed'})
    (OUT/'results.json').write_text(json.dumps(results,indent=2))
    print('SEED_DONE',seed,flush=True)
print('CONTROLLED_VISUAL_TEST_COMPLETE',flush=True)
