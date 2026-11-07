"""Local assembly preflight. Does not evaluate acting or authorize generation."""
import json
import math
import subprocess
from pathlib import Path
from .reviewgate import validate_requirements


def ffconcat_entry(path):
    value = str(Path(path).resolve())
    if any(c in value for c in ('\n', '\r', '\x00')):
        raise ValueError('Newline/control characters in media paths refused')
    return "file '" + value.replace("'", "'\\''") + "'\n"


def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True, check=True, timeout=30)
    return json.loads(p.stdout)


def validate_assembly_inputs(requirements, assets, audio, output):
    validate_requirements(requirements)
    expected = {str(b['beat']) for b in requirements['beats']}
    if set(assets) != expected:
        raise ValueError('Assets must exactly match ordered requirements')
    sources = [Path(p).resolve() for p in assets.values()] + [Path(audio).resolve()]
    target = Path(output).resolve()
    if target in sources:
        raise ValueError('Output cannot alias an input')
    # Existing outputs are immutable, even when they were a prior candidate.
    if target.exists():
        raise ValueError('Fresh output path required; preserve prior candidate')
    geometry = None
    for beat in requirements['beats']:
        path = Path(assets[str(beat['beat'])])
        ffconcat_entry(path)
        info = probe(path)
        videos = [s for s in info['streams'] if s['codec_type'] == 'video']
        if len(videos) != 1:
            raise ValueError('Exactly one video stream required per beat')
        v = videos[0];current = (v['width'], v['height'], v.get('sample_aspect_ratio', '1:1'))
        if geometry is not None and current != geometry:
            raise ValueError('Mixed shot geometry requires explicit reviewed conform step')
        geometry = current
        duration = float(v.get('duration', info['format']['duration']))
        if not math.isfinite(duration) or abs(duration - (beat['end'] - beat['start'])) > .1:
            raise ValueError('Shot duration differs from requirements; explicit reviewed trim required')
    info = probe(audio)
    streams = [s for s in info['streams'] if s['codec_type'] == 'audio']
    if len(streams) != 1:
        raise ValueError('Exactly one final audio stream required')
    duration = float(streams[0].get('duration', info['format']['duration']))
    if not math.isfinite(duration) or abs(duration - requirements['beats'][-1]['end']) > .15:
        raise ValueError('Final audio duration differs from timeline; refuse silent truncation')
