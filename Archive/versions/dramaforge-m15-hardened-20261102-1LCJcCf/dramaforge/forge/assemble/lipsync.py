"""Build the MuseTalk 1.5 shell command for one shot (run on a GPU host)."""
from pathlib import Path

def musetalk_cmd(video: str, audio_wav: str, out_dir: str, repo: str = "MuseTalk") -> str:
    cfg = Path(out_dir) / "task.yaml"
    yaml = f'task_0:\n video_path: "{video}"\n audio_path: "{audio_wav}"\n'
    return (f"mkdir -p {out_dir} && printf '{yaml}' > {cfg} && cd {repo} && MPLBACKEND=agg "
            f"python -m scripts.inference --inference_config {cfg} --result_dir {out_dir} "
            "--unet_model_path models/musetalkV15/unet.pth "
            "--unet_config models/musetalkV15/musetalk.json --version v15")


def latentsync_cmd(video: str, audio_wav: str, out_mp4: str, repo: str = "LatentSync") -> str:
    """Default engine: LatentSync 1.5 (weights from ByteDance/LatentSync-1.5)."""
    return (f"cd {repo} && MPLBACKEND=agg python -m scripts.inference "
            "--unet_config_path configs/unet/stage2.yaml "
            "--inference_ckpt_path checkpoints/latentsync_unet.pt "
            f"--inference_steps 20 --guidance_scale 1.5 --enable_deepcache "
            f"--video_path {video} --audio_path {audio_wav} --video_out_path {out_mp4}")

DEFAULT_ENGINE = "latentsync"
