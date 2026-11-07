# H3 on Modal (serverless): the manager's production R2V graph (research/h3/runpod/r2v_v1.json) in ComfyUI v0.36.0,
# billed per second only while a clip renders, scaling to zero between films. Replaces the RunPod pods (availability
# lottery, idle billing, boot scripts).
#   .venv/bin/modal run research/h3/modal_h3.py::download     # once: the ~37 GB of weights into the h3-weights volume
#   .venv/bin/modal deploy research/h3/modal_h3.py            # the H3 class; comfy_r2v.py --modal calls it
# GPUs: Blackwell only — the text encoder is nvfp4. B200 first: same cost per clip as an RTX PRO 6000 ($6.25 vs $3.03/h, ~2x faster), runs with SageAttention off (our build is
# sm_120). Docs: https://modal.com/docs/guide/gpu, /guide/volumes, /guide/lifecycle-functions, /guide/images.
import json, os, subprocess, time, urllib.request, uuid
from pathlib import Path
import modal

app = modal.App('h3-render')
# Corrective-test safety defaults: one GPU container and hard call bounds. Production can override at deploy time.
H3_GPU = [x.strip() for x in os.environ.get('H3_MODAL_GPU', 'RTX-PRO-6000,B200').split(',') if x.strip()]
H3_TIMEOUT = int(os.environ.get('H3_MODAL_TIMEOUT_SECONDS', '1800'))
H3_DOWNLOAD_TIMEOUT = int(os.environ.get('H3_MODAL_DOWNLOAD_TIMEOUT_SECONDS', '1800'))
H3_MAX_CONTAINERS = int(os.environ.get('H3_MODAL_MAX_CONTAINERS', '1'))
weights = modal.Volume.from_name('h3-weights', create_if_missing=True)
W, COMFY = '/weights', '/opt/ComfyUI'
HF = 'https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/'
WEIGHT_META = {
    'diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors': (20970379616, '9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779'),
    'text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors': (15687142551, '35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6'),
    'vae/minimax_h3_video_vae_fp16.safetensors': (5207808496, '7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522'),
    'vae/minimax_h3_audio_vae_fp32.safetensors': (605254808, '8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48'),
}
WEIGHTS = list(WEIGHT_META)  # corrective test: default graph uses int8; omit unused 61GB BF16
image = (
    modal.Image.from_registry('nvidia/cuda:12.8.1-devel-ubuntu24.04', add_python='3.12')
    .apt_install('git', 'ffmpeg', 'aria2', 'wget', 'libgl1', 'libglib2.0-0', 'build-essential')
    .pip_install('torch==2.8.0', 'torchvision==0.23.0', 'torchaudio==2.8.0', index_url='https://download.pytorch.org/whl/cu128')
    .pip_install('setuptools', 'wheel', 'packaging', 'ninja', 'requests')
    .run_commands(
        f'git clone --branch v0.36.0 --depth 1 https://github.com/comfyanonymous/ComfyUI.git {COMFY}',
        f"pip install -r {COMFY}/requirements.txt 'huggingface-hub<2.0'",
        f'cd {COMFY}/custom_nodes && git clone --depth 1 https://github.com/kijai/ComfyUI-KJNodes.git'
        ' && git clone --depth 1 https://github.com/T8mars/comfyui-minimax-h3-blockcache-T8.git'
        ' && git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git',
        f'cd {COMFY}/custom_nodes && for d in */; do [ -f "$d/requirements.txt" ] && pip install -r "$d/requirements.txt"; done; true',
        # Corrective test: skip the SageAttention native build; the graph disables it below for reliability.
        f"printf 'h3:\\n  base_path: {W}\\n  diffusion_models: diffusion_models\\n  text_encoders: text_encoders\\n  vae: vae\\n' > {COMFY}/extra_model_paths.yaml",
    )
)


@app.function(image=image, volumes={W: weights}, timeout=H3_DOWNLOAD_TIMEOUT)
def download():
    todo = [p for p in WEIGHTS if not Path(W, p).is_file() or Path(W, p + '.aria2').exists()]
    if todo:
        Path('/tmp/w.txt').write_text(''.join(f'{HF}{p}\n  dir={W}/{Path(p).parent}\n  out={Path(p).name}\n' for p in todo))
        subprocess.run(['aria2c', '--input-file', '/tmp/w.txt', '-x16', '-s16', '--min-split-size=1M', '--max-concurrent-downloads=4',
                        '--console-log-level=warn', '--summary-interval=30', '--auto-file-renaming=false', '--allow-overwrite=true'], check=True)
        weights.commit()
    for p in WEIGHTS: print(f'{Path(W, p).stat().st_size / 1e9:6.2f} GB  {p}')


@app.function(image=image, volumes={W: weights}, timeout=H3_DOWNLOAD_TIMEOUT)
def verify():
    import hashlib
    result = {}
    for p, (size, sha) in WEIGHT_META.items():
        path = Path(W, p)
        if not path.is_file() or Path(W, p + '.aria2').exists():
            raise RuntimeError(f'Weight incomplete: {p}')
        actual_size = path.stat().st_size
        if actual_size != size:
            raise RuntimeError(f'Weight size mismatch for {p}: {actual_size} != {size}')
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(16 * 1024 * 1024), b''):
                h.update(chunk)
        actual_sha = h.hexdigest()
        if actual_sha != sha:
            raise RuntimeError(f'Weight SHA256 mismatch for {p}: {actual_sha} != {sha}')
        result[p] = {'size': actual_size, 'sha256': actual_sha}
    return result


@app.cls(image=image, volumes={W: weights}, gpu=H3_GPU, timeout=H3_TIMEOUT, scaledown_window=30, max_containers=H3_MAX_CONTAINERS)  # workspace cap also binds; Starter observed at 10 GPUs
class H3:
    @modal.enter()
    def start(self):
        for d in ('input', 'output', 'user'): Path('/tmp/comfy', d).mkdir(parents=True, exist_ok=True)
        # T8 picks the prefetch-cleanup call by looking for GRAPH_MODULES, which v0.36.0 lacks: read the real signature
        # (applied here because the build-time shell quoting of this edit silently did nothing).
        t8 = Path(COMFY, 'custom_nodes/comfyui-minimax-h3-blockcache-T8/nodes.py')
        t8.write_text(t8.read_text().replace('PREFETCH_CLEANUP_TAKES_MODULE = hasattr(comfy.model_prefetch, "GRAPH_MODULES")',
            'PREFETCH_CLEANUP_TAKES_MODULE = "module" in inspect.signature(comfy.model_prefetch.cleanup_prefetched_modules).parameters'))
        self.proc = subprocess.Popen(['python', '-u', 'main.py', '--listen', '127.0.0.1', '--port', '8188', '--disable-auto-launch',
                                      '--dont-print-server', '--input-directory', '/tmp/comfy/input', '--output-directory',
                                      '/tmp/comfy/output', '--user-directory', '/tmp/comfy/user'],
                                     cwd=COMFY, env={'PYTHONNOUSERSITE': '1', 'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True',
                                                     **__import__('os').environ})
        for _ in range(600):
            try: urllib.request.urlopen('http://127.0.0.1:8188/object_info', timeout=2); return
            except Exception: time.sleep(0.5)
        raise RuntimeError('ComfyUI did not start')

    @modal.method()
    def render(self, graph: dict, files: dict) -> dict:
        import torch, requests
        for name, data in files.items(): Path('/tmp/comfy/input', name).write_bytes(data)
        gpu = torch.cuda.get_device_name(0)
        graph['141']['inputs']['sage_attention'] = 'disabled'  # corrective test: deterministic portable attention, no native Sage build
        t0 = time.time()
        pid = requests.post('http://127.0.0.1:8188/prompt', json={'prompt': graph, 'client_id': uuid.uuid4().hex}).json()
        if 'prompt_id' not in pid: raise RuntimeError(json.dumps(pid)[:3000])
        pid = pid['prompt_id']
        while True:
            h = requests.get(f'http://127.0.0.1:8188/history/{pid}').json().get(pid)
            if h and h.get('status', {}).get('completed'): break
            if h and h.get('status', {}).get('status_str') == 'error': raise RuntimeError(json.dumps(h['status'])[:3000])
            time.sleep(3)
        f = next(f for o in h['outputs'].values() for k in ('images', 'videos', 'gifs') for f in o.get(k, []))
        return {'mp4': Path('/tmp/comfy/output', f.get('subfolder', ''), f['filename']).read_bytes(), 'seconds': round(time.time() - t0), 'gpu': gpu}
