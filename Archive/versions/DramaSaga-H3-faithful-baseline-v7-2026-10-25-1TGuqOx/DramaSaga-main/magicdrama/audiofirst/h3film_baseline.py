"""Faithful offline baseline compiler for the preserved H3Film R2V runner.

The authoritative graph-building code is the byte-exact user-supplied
``research/h3/runpod/comfy_r2v.py`` file itself. This module can compile that
exact code path offline by replacing only the final Modal transport with a
capture stub. It never submits a job. A real render must use the returned
command only after separate compute and spend approval.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
from typing import Any, Iterable

from .core import finite

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNNER = ROOT / 'vendor/h3-film-reference/research/h3/runpod/comfy_r2v.py'
EXPECTED_COMFY_R2V_SHA256 = '3587ca8a94d95f0e7c9a06045518d93130b77a202e1bacd9c784ef244bfd537e'
EXPECTED_R2V_V1_SHA256 = '1d927b51d05405fa0d2683593822882c7cf8a6d5f9742817863338e7efe069a3'


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _existing_file(path: str | Path, label: str) -> Path:
    p = Path(path)
    if not p.is_file():
        raise ValueError(f'{label} does not exist: {p}')
    return p


def build_h3film_clip(
    *,
    clip_id: str,
    prompt_path: str | Path,
    seconds: float,
    image_paths: Iterable[str | Path],
    audio_path: str | Path,
    videos: Iterable[str | Path] = (),
    pins: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Build the clip JSON consumed by the preserved H3Film runner.

    The field names are the runner's own schema: ``id``, ``prompt``, ``seconds``,
    ``images``, ``videos``, ``audio`` and optional ``pins``. No timed audio guide
    extension is added here.
    """
    if not isinstance(clip_id, str) or not clip_id.strip():
        raise ValueError('clip_id is required')
    prompt = _existing_file(prompt_path, 'prompt file')
    seconds = finite(seconds, 'clip seconds', 0.01)
    images = [_existing_file(p, 'reference image') for p in image_paths]
    if not 1 <= len(images) <= 9:
        raise ValueError('H3Film R2V accepts 1-9 reference images')
    if len({str(p) for p in images}) != len(images):
        raise ValueError('reference images must be unique')
    audio = _existing_file(audio_path, 'audio file')
    video_paths = [_existing_file(p, 'reference video') for p in videos]
    if len(video_paths) > 3:
        raise ValueError('H3Film R2V accepts at most 3 reference videos')
    pin_list = list(pins)
    if not isinstance(pin_list, list):
        raise ValueError('pins must be a list')
    clip: dict[str, Any] = {
        'id': clip_id,
        'prompt': str(prompt),
        'seconds': seconds,
        'images': [str(p) for p in images],
        'audio': str(audio),
    }
    if video_paths:
        clip['videos'] = [str(p) for p in video_paths]
    if pin_list:
        clip['pins'] = pin_list
    return clip


def original_runner_command(
    *,
    runner_path: str | Path = DEFAULT_RUNNER,
    clip_path: str | Path,
    output_path: str | Path,
    rows: int = 576,
    ratio: str = '9:16',
    audio_mode: str = 'inpaint',
    seed: int | None = None,
) -> list[str]:
    """Return, but do not execute, the preserved H3Film runner command."""
    runner = _existing_file(runner_path, 'H3Film runner')
    if _sha256_path(runner) != EXPECTED_COMFY_R2V_SHA256:
        raise ValueError('H3Film runner hash changed; requires fresh source audit')
    if ratio not in ('16:9', '9:16'):
        raise ValueError('This baseline is audited only for 16:9 or 9:16')
    if audio_mode not in ('inpaint', 'reference'):
        raise ValueError('H3Film audio mode must be inpaint or reference')
    command = [
        sys.executable,
        str(runner),
        f'--clip={Path(clip_path)}',
        str(Path(output_path)),
        f'--rows={int(rows)}',
        f'--ratio={ratio}',
        f'--audio={audio_mode}',
    ]
    if seed is not None:
        command.append(f'--seed={int(seed)}')
    return command


@dataclass(frozen=True)
class BaselineCompileResult:
    clip: dict[str, Any]
    graph: dict[str, Any]
    files_manifest: dict[str, dict[str, Any]]
    workflow_sha256: str
    runner_sha256: str
    command: list[str]


def compile_with_original_runner_offline(
    *,
    clip: dict[str, Any],
    runner_path: str | Path = DEFAULT_RUNNER,
    rows: int = 576,
    ratio: str = '9:16',
    audio_mode: str = 'inpaint',
    seed: int | None = None,
    scratch_dir: str | Path,
) -> BaselineCompileResult:
    """Compile through the preserved runner with Modal replaced by a capture stub.

    This executes the runner's local graph-building code, including its audio
    pad/cut step, but replaces ``modal.Cls...render.remote`` so no network call,
    GPU job, or spend can occur.
    """
    runner = _existing_file(runner_path, 'H3Film runner')
    runner_sha = _sha256_path(runner)
    if runner_sha != EXPECTED_COMFY_R2V_SHA256:
        raise ValueError('H3Film runner hash changed; requires fresh source audit')
    graph_path = runner.with_name('r2v_v1.json')
    if _sha256_path(graph_path) != EXPECTED_R2V_V1_SHA256:
        raise ValueError('H3Film R2V graph hash changed; requires fresh source audit')

    scratch = Path(scratch_dir)
    scratch.mkdir(parents=True, exist_ok=True)
    clip_path = scratch / f"{clip['id']}.clip.json"
    clip_path.write_text(json.dumps(clip, indent=2, sort_keys=True))
    output_path = (scratch / f"{clip['id']}.dry-run.mp4").resolve()
    if output_path == runner.resolve() or scratch.resolve() not in output_path.parents:
        raise ValueError('dry-run output must stay inside scratch_dir')
    command = original_runner_command(
        runner_path=runner, clip_path=clip_path, output_path=output_path,
        rows=rows, ratio=ratio, audio_mode=audio_mode, seed=seed)

    captured: dict[str, Any] = {}

    class _Render:
        def remote(self, graph: dict, files: dict) -> dict[str, Any]:
            captured['graph'] = graph
            captured['files'] = files
            return {'mp4': b'', 'seconds': 0, 'gpu': 'offline-dry-run'}

    class _H3:
        def __init__(self) -> None:
            self.render = _Render()

    class _Cls:
        @classmethod
        def from_name(cls, *args: Any, **kwargs: Any) -> Any:
            return lambda: _H3()

    old_argv = sys.argv[:]
    old_modal = sys.modules.get('modal')
    sys.modules['modal'] = types.SimpleNamespace(Cls=_Cls)
    try:
        # comfy_r2v.py parses --rows at module import time, before main().
        sys.argv = command[1:]  # runner argv[0], then its own arguments
        spec = importlib.util.spec_from_file_location('h3film_comfy_r2v_authoritative', runner)
        if spec is None or spec.loader is None:
            raise ValueError(f'Cannot load H3Film runner: {runner}')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.main()
    finally:
        sys.argv = old_argv
        if old_modal is None:
            sys.modules.pop('modal', None)
        else:
            sys.modules['modal'] = old_modal

    graph = captured.get('graph')
    files = captured.get('files')
    if not isinstance(graph, dict) or not graph or not isinstance(files, dict):
        raise RuntimeError('H3Film dry-run did not produce a graph and input files')
    files_manifest = {
        name: {'bytes': len(data), 'sha256': _sha256_bytes(data)}
        for name, data in sorted(files.items())
    }
    canonical = json.dumps(graph, sort_keys=True, separators=(',', ':')).encode()
    return BaselineCompileResult(
        clip=clip,
        graph=graph,
        files_manifest=files_manifest,
        workflow_sha256=hashlib.sha256(canonical).hexdigest(),
        runner_sha256=runner_sha,
        command=command,
    )
