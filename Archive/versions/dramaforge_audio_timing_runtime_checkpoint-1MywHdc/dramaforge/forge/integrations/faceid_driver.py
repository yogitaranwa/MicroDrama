"""Real cached-weight FaceID inference. No network or model work at import/help."""
import argparse
import json
import os
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    for name in ('manifest','repo','base-model','adapter','insightface-root','project-dir'): p.add_argument('--'+name,required=True)
    a = p.parse_args()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from forge.guard.generation_hold import require_generation_open
    require_generation_open(project_dir=a.project_dir)
    from forge.integrations.faceid import validate_batch
    b = validate_batch(json.loads(Path(a.manifest).read_text()))
    from forge.gates.still_first import require_still_lock
    lock=require_still_lock(a.project_dir)
    if not any(str(Path(v['path']).resolve())==b['reference'] and v['sha256']==b['reference_sha256'] for v in lock['stills'].values()):
        raise SystemExit('FaceID reference not in current still lock')
    sys.path.insert(0,a.repo)
    import torch
    import cv2
    from insightface.app import FaceAnalysis
    from diffusers import StableDiffusionXLPipeline, DDIMScheduler
    from ip_adapter.ip_adapter_faceid import IPAdapterFaceIDXL
    if not torch.cuda.is_available(): raise SystemExit('FaceID requires CUDA')
    modeldir=Path(a.insightface_root)/'models'/'buffalo_l'
    if len(list(modeldir.glob('*.onnx'))) < 5: raise SystemExit('cached buffalo_l missing, no download allowed')
    app = FaceAnalysis(name='buffalo_l',root=a.insightface_root,providers=['CUDAExecutionProvider','CPUExecutionProvider'])
    app.prepare(ctx_id=0,det_size=(640,640))
    image = cv2.imread(b['reference'])
    if image is None: raise SystemExit('unreadable reference')
    faces = app.get(image)
    if len(faces) != 1: raise SystemExit('reference must contain exactly ONE detected face; do not select the wrong person')
    embedding=torch.from_numpy(faces[0].normed_embedding).unsqueeze(0)
    scheduler=DDIMScheduler(num_train_timesteps=1000,beta_start=0.00085,beta_end=0.012,
        beta_schedule='scaled_linear',clip_sample=False,set_alpha_to_one=False,steps_offset=1)
    pipe=StableDiffusionXLPipeline.from_pretrained(a.base_model,torch_dtype=torch.float16,
        scheduler=scheduler,add_watermarker=False,local_files_only=True)
    pipe.enable_vae_slicing()
    model=IPAdapterFaceIDXL(pipe,a.adapter,'cuda')
    receipts=[]
    for job in b['jobs']:
        if Path(job['output']).exists(): raise SystemExit('output appeared; refusing overwrite')
        images=model.generate(faceid_embeds=embedding,prompt=job['prompt'],
            negative_prompt='monochrome, lowres, bad anatomy, worst quality, blurry',
            scale=job['scale'],num_samples=1,seed=job['seed'],width=job['width'],height=job['height'],
            num_inference_steps=job['steps'],guidance_scale=7.5)
        images[0].save(job['output'])
        from forge.integrations.faceid import digest
        receipts.append({'output':job['output'],'sha256':digest(job['output']),'quality_status':'unreviewed'})
        Path(a.manifest+'.receipts.json').write_text(json.dumps(receipts,indent=2))
    print('FaceID outputs saved; identity/wardrobe/angle visual review is still required.')

if __name__ == '__main__': main()
