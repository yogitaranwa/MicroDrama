"""Catalog of vendored third-party repositories (m19).

Free/local inspection only: no downloads, no GPU work, no network calls.
Reports what is present, what is missing, and why a repo cannot run here."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


class IntegrationError(RuntimeError):
    """Raised when a vendored integration cannot proceed; message says why."""


@dataclass(frozen=True)
class VendoredRepo:
    key: str
    path: str           # relative to the dramaforge root
    upstream: str
    commit: str
    license_spdx: str
    license_file: str   # relative to the vendored directory
    entrypoint: str     # main CLI file relative to the vendored directory
    capability: str
    weights: str
    min_gpu_gb: int
    notes: str = ""


REPOS = (
    VendoredRepo(
        key="multitalk",
        path="third_party/multitalk",
        upstream="https://github.com/MeiGen-AI/MultiTalk",
        commit="c1ad84009b99ed36c97ab18e4517ca5f98692438",
        license_spdx="Apache-2.0",
        license_file="LICENSE.txt",
        entrypoint="generate_multitalk.py",
        capability="multi-person audio-driven talking video (per-person audio streams)",
        weights="MeiGen-MultiTalk + Wan2.1-I2V-14B-480P + chinese-wav2vec2-base (Apache-2.0 cards, HF)",
        min_gpu_gb=16,
        notes="README: 480p single GPU with low-VRAM offload; 720p needs multi-GPU; <=15s clips."),
    VendoredRepo(
        key="infinitetalk",
        path="third_party/infinitetalk",
        upstream="https://github.com/MeiGen-AI/InfiniteTalk",
        commit="50aa0a94184315407a991ae804d9b58d6d311ba8",
        license_spdx="Apache-2.0",
        license_file="LICENSE.txt",
        entrypoint="generate_infinitetalk.py",
        capability="audio-driven dubbing/lip-sync video, streaming long-form mode",
        weights="MeiGen-InfiniteTalk + Wan2.1 base (Apache-2.0 cards, HF)",
        min_gpu_gb=16,
        notes="Quality claims over MultiTalk are the authors' own, unverified by us."),
    VendoredRepo(
        key="vace",
        path="third_party/vace",
        upstream="https://github.com/ali-vilab/VACE",
        commit="48eb44f1c4be87cc65a98bff985a26976841e9f3",
        license_spdx="Apache-2.0",
        license_file="LICENSE.txt",
        entrypoint="vace/vace_wan_inference.py",
        capability="reference-guided video generation/editing (ref images, depth/pose/flow control)",
        weights="Wan2.1-VACE-1.3B/14B (Apache-2.0). VACE-LTX-Video-0.9 is RAIL-M - do not use that variant.",
        min_gpu_gb=12,
        notes="1.3B preview targets ~480p on one GPU; 14B targets 720p, much heavier."),
    VendoredRepo(
        key="pulid",
        path="third_party/pulid",
        upstream="https://github.com/ToTheBeginning/PuLID",
        commit="1aa2fc7df4bf51080df39f355f9abdc1cbfefbaa",
        license_spdx="Apache-2.0",
        license_file="LICENSE",
        entrypoint="pulid/pipeline.py",
        capability="identity-preserved portrait stills (library, no CLI)",
        weights="SDXL base + SDXL-Lightning + PuLID v1 + InsightFace antelopev2 (non-commercial face models); stills only",
        min_gpu_gb=16,
        notes="Vendored pipeline.py is SDXL, not FLUX; upstream constructor downloads its own model files. Review all model licenses before use."),
    VendoredRepo(
        key="ip_adapter_faceid", path="third_party/ip_adapter_faceid",
        upstream="https://github.com/tencent-ailab/IP-Adapter",
        commit="62e4af9d0c1ac7d5f8dd386a0ccf2211346af1a2",
        license_spdx="Apache-2.0", license_file="LICENSE",
        entrypoint="ip_adapter/ip_adapter_faceid.py",
        capability="local SDXL single-identity stills and prompt batches",
        weights="local SDXL snapshot + ip-adapter-faceid_sdxl.bin + buffalo_l; face models research-only/non-commercial",
        min_gpu_gb=16,
        notes="Personal research only; no hosted API support; actual model inference not yet validated."),
)


def repo(key: str) -> VendoredRepo:
    for r in REPOS:
        if r.key == key:
            return r
    raise IntegrationError(
        f"unknown vendored repo {key!r}; available: {', '.join(r.key for r in REPOS)}")


def _cuda_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def validate(root: str, need_cuda: bool = False) -> dict:
    """Inspect the vendored tree under `root`; never raises for missing GPU.

    Returns {key: {present, license_ok, entrypoint_ok, blocked}}. `blocked`
    lists human-readable reasons the repo cannot run inference on this host;
    an empty list means the code and weights situation is not the blocker."""
    if not os.path.isdir(root):
        raise IntegrationError(f"dramaforge root not found: {root}")
    report = {}
    cuda = _cuda_available()
    for r in REPOS:
        d = os.path.join(root, r.path)
        present = os.path.isdir(d)
        license_ok = present and os.path.isfile(os.path.join(d, r.license_file))
        entry_ok = present and os.path.isfile(os.path.join(d, r.entrypoint))
        blocked = []
        if not present:
            blocked.append(f"vendored directory missing: {r.path}")
        if present and not license_ok:
            blocked.append(f"license file missing: {r.path}/{r.license_file}")
        if present and not entry_ok:
            blocked.append(f"entrypoint missing: {r.path}/{r.entrypoint}")
        blocked.append("model weights not vendored - fetch from Hugging Face on the GPU host")
        if need_cuda and not cuda:
            blocked.append(f"no CUDA GPU visible here; needs ~{r.min_gpu_gb}GB+ (upstream README)")
        report[r.key] = {
            "present": present,
            "license_ok": license_ok,
            "entrypoint_ok": entry_ok,
            "upstream": r.upstream,
            "commit": r.commit,
            "license_spdx": r.license_spdx,
            "capability": r.capability,
            "blocked": blocked,
        }
    return report
