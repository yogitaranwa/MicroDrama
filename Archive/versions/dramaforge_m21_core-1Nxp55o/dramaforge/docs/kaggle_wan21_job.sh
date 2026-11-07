# m18 proof: Wan2.1-T2V-1.3B clip generation on free Kaggle T4 (approved
# scope: official Wan-AI repo/weights only, 2-3 short shots, one character,
# one location, NO lip-sync, no paid credits, no voice model).
# Uses the Kaggle image's preinstalled CUDA torch + official PyPI diffusers;
# the vendor repo's own generate.py needs flash_attn (sm80+, absent on T4),
# so the diffusers WanPipeline with CPU offload is the supported T4 route.
set -e
cd /kaggle/working
pip -q install 'diffusers>=0.33.0' 'transformers>=4.49.0' 'accelerate>=1.1.1' imageio imageio-ffmpeg ftfy && echo STEP_PIP
python3 - <<'PYEOF'
import json, os, time, torch
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
from diffusers import WanPipeline
from diffusers.utils import export_to_video

NEG = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，"
       "JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，"
       "形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走")
JOBS = json.load(open("/kaggle/working/wan_jobs.json"))
pipe = WanPipeline.from_pretrained("Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
                                   torch_dtype=torch.float16)
pipe.enable_model_cpu_offload()  # T4 16GB: keep only the active module on GPU
pipe.vae.enable_tiling()  # bound VAE decode memory
print("STEP_PIPE_READY")
for j in JOBS:
    t0 = time.time()
    frames = pipe(prompt=j["prompt"], negative_prompt=NEG,
                  height=832, width=480, num_frames=j.get("num_frames", 33),
                  num_inference_steps=j.get("steps", 40),
                  guidance_scale=5.0).frames[0]
    out = f"/kaggle/working/shot_{j['plan_n']}.mp4"
    export_to_video(frames, out, fps=16)
    print(f"STEP_SHOT_DONE_{j['plan_n']} {out} {round(time.time()-t0,1)}s")
print("STEP_ALL_DONE")
PYEOF
