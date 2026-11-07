"""Job builders for vendored repos (m19).

Each builder writes the real input file the upstream CLI reads and returns
the real argv to run it. No GPU, network or model work happens here; the
runner module executes the argv. Fail-closed on missing inputs."""
from __future__ import annotations

import json
import os

from .registry import IntegrationError, repo

_MULTITALK_SIZES = ("multitalk-480", "multitalk-720")
_AUDIO_TYPES = ("para", "add")


def _need_file(path: str, what: str) -> str:
    if not path or not os.path.isfile(path):
        raise IntegrationError(f"{what} not found: {path!r}")
    return path


def build_multitalk_input(prompt: str, cond_image: str, cond_audio: dict,
                          out_json: str, audio_type: str = "para") -> dict:
    """Write MultiTalk/InfiniteTalk's input JSON in its exact schema.

    cond_audio maps person1..personN to existing wav paths (1-2 speakers;
    matches generate_multitalk.py's cond_audio reader). audio_type 'para'
    = parallel speakers, 'add' = sequential, per upstream code."""
    if not prompt or not prompt.strip():
        raise IntegrationError("prompt must be non-empty")
    _need_file(cond_image, "conditioning image")
    if audio_type not in _AUDIO_TYPES:
        raise IntegrationError(f"audio_type must be one of {_AUDIO_TYPES}")
    if not isinstance(cond_audio, dict) or not (1 <= len(cond_audio) <= 2):
        raise IntegrationError("cond_audio needs 1-2 speakers (person1[, person2])")
    cleaned = {}
    for name, wav in cond_audio.items():
        if name not in ("person1", "person2"):
            raise IntegrationError(f"cond_audio keys must be personN, got {name!r}")
        cleaned[name] = _need_file(wav, f"audio for {name}")
    if set(cleaned) != {"person1", "person2"} and set(cleaned) != {"person1"}:
        raise IntegrationError("speaker keys must be person1 or person1 + person2")
    data = {"prompt": prompt, "cond_image": cond_image,
            "audio_type": audio_type, "cond_audio": cleaned}
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return data


def _frame_num_ok(n: int) -> bool:
    return isinstance(n, int) and n >= 5 and (n - 1) % 4 == 0


def multitalk_cli(root: str, input_json: str, ckpt_dir: str, wav2vec_dir: str,
                  save_file: str, size: str = "multitalk-480",
                  frame_num: int = 81, base_seed: int = 42,
                  sample_steps=None, python: str = "python3") -> list:
    """Real argv for third_party/multitalk/generate_multitalk.py."""
    r = repo("multitalk")
    if size not in _MULTITALK_SIZES:
        raise IntegrationError(f"size must be one of {_MULTITALK_SIZES}")
    if not _frame_num_ok(frame_num):
        raise IntegrationError("frame_num must be 4n+1 (upstream constraint)")
    _need_file(input_json, "input json")
    argv = [python, os.path.join(root, r.path, r.entrypoint),
            "--task", "multitalk-14B", "--size", size,
            "--frame_num", str(frame_num),
            "--ckpt_dir", ckpt_dir, "--wav2vec_dir", wav2vec_dir,
            "--input_json", input_json, "--save_file", save_file,
            "--base_seed", str(base_seed), "--offload_model", "True"]
    if sample_steps:
        argv += ["--sample_steps", str(int(sample_steps))]
    return argv


def infinitetalk_cli(root: str, input_json: str, ckpt_dir: str,
                     wav2vec_dir: str, save_file: str,
                     size: str = "infinitetalk-480", frame_num: int = 81,
                     base_seed: int = 42, mode: str = "clip",
                     python: str = "python3", infinitetalk_ckpt=None) -> list:
    """Real argv for third_party/infinitetalk/generate_infinitetalk.py
    (same cond_audio input schema as MultiTalk)."""
    r = repo("infinitetalk")
    if size not in ("infinitetalk-480", "infinitetalk-720"):
        raise IntegrationError("unsupported InfiniteTalk size")
    if mode not in ("clip", "streaming"):
        raise IntegrationError("mode must be 'clip' or 'streaming'")
    if not _frame_num_ok(frame_num):
        raise IntegrationError("frame_num must be 4n+1 (upstream constraint)")
    _need_file(input_json, "input json")
    argv = [python, os.path.join(root, r.path, r.entrypoint),
            "--task", "infinitetalk-14B", "--size", size,
            "--frame_num", str(frame_num), "--mode", mode,
            "--ckpt_dir", ckpt_dir, "--wav2vec_dir", wav2vec_dir,
            "--input_json", input_json, "--save_file", save_file,
            "--base_seed", str(base_seed)]
    if infinitetalk_ckpt is not None:
        argv += ["--infinitetalk_dir", _need_file(infinitetalk_ckpt, "InfiniteTalk checkpoint")]
    return argv


def vace_cli(root: str, prompt: str, save_file: str,
             src_ref_images=(), src_video=None, src_mask=None,
             model: str = "vace-1.3B", python: str = "python3") -> list:
    """Real argv for third_party/vace/vace/vace_wan_inference.py."""
    r = repo("vace")
    if not prompt or not prompt.strip():
        raise IntegrationError("prompt must be non-empty")
    if model not in ("vace-1.3B", "vace-14B"):
        raise IntegrationError("vace model must be 'vace-1.3B' or 'vace-14B'")
    argv = [python, os.path.join(root, r.path, r.entrypoint),
            "--model_name", model, "--size", "480p",
            "--prompt", prompt, "--save_file", save_file]
    for img in src_ref_images:
        _need_file(img, "VACE reference image")
    if src_ref_images:
        argv += ["--src_ref_images", ",".join(src_ref_images)]
    if src_video:
        argv += ["--src_video", _need_file(src_video, "VACE source video")]
    if src_mask:
        argv += ["--src_mask", _need_file(src_mask, "VACE mask video")]
    return argv


_PULID_SDXL_DRIVER = '''"""PuLID SDXL driver. Upstream constructor fetches model files if uncached.
Use only on an explicitly prepared GPU host after reviewing model licenses."""
import argparse, os, sys

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pulid_root", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--ref_image", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--id_scale", type=float, default=1.0)
    p.add_argument("--steps", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--width", type=int, default=1024)
    a = p.parse_args()
    sys.path.insert(0, a.pulid_root)
    from PIL import Image
    import numpy as np
    import torch
    from pulid.pipeline import PuLIDPipeline
    from pulid.utils import resize_numpy_image_long, seed_everything
    from pulid import attention_processor as attention
    if not torch.cuda.is_available():
        raise SystemExit("PuLID requires a CUDA GPU")
    os.chdir(a.pulid_root)
    torch.set_grad_enabled(False)
    attention.NUM_ZERO = 8
    attention.ORTHO = False
    attention.ORTHO_v2 = True
    pipe = PuLIDPipeline()
    ref = resize_numpy_image_long(np.array(Image.open(a.ref_image).convert("RGB")), 1024)
    embedding = pipe.get_id_embedding(ref)
    seed_everything(a.seed)
    imgs = pipe.inference(a.prompt, (1, a.height, a.width),
                          image_embedding=embedding, id_scale=a.id_scale,
                          steps=a.steps)
    imgs[0].save(a.out)
    print(a.out)

if __name__ == "__main__":
    main()
'''


def pulid_sdxl_driver(root: str, out_dir: str, prompt: str, ref_image: str,
                      out_image: str, id_scale: float = 1.0, steps: int = 4,
                      seed: int = 42, height: int = 1024, width: int = 1024,
                      python: str = "python3") -> list:
    """Actual vendored pipeline is SDXL-Lightning, not FLUX. Constructor
    manages its own weights and may download them. No generation here."""
    if not prompt or not prompt.strip():
        raise IntegrationError("prompt must be non-empty")
    if steps != 4:
        raise IntegrationError("vendored SDXL-Lightning checkpoint is the 4-step variant")
    if any(not isinstance(n, int) or n < 64 or n % 8 for n in (height, width)):
        raise IntegrationError("height and width must be positive multiples of 8, >=64")
    ref_image = os.path.abspath(_need_file(ref_image, "PuLID reference image"))
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    script = os.path.join(out_dir, "pulid_sdxl_drive.py")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(_PULID_SDXL_DRIVER)
    return [python, script, "--pulid_root", os.path.abspath(os.path.join(root, "third_party", "pulid")),
            "--prompt", prompt, "--ref_image", ref_image,
            "--out", os.path.abspath(out_image), "--id_scale", str(id_scale),
            "--steps", str(steps), "--seed", str(seed),
            "--height", str(height), "--width", str(width)]


def pulid_driver(root: str, out_dir: str, flux_ckpt: str, pulid_ckpt: str,
                 prompt: str, ref_image: str, out_image: str,
                 id_scale: float = 1.0, steps: int = 4,
                 python: str = "python3") -> list:
    """Compatibility entrypoint retained but fail-closed: this API was based
    on a FLUX assumption incompatible with the vendored SDXL pipeline."""
    raise IntegrationError("FLUX adapter unavailable: vendored pulid.pipeline is SDXL. "
                           "Use pulid_sdxl_driver after reviewing model licenses.")
