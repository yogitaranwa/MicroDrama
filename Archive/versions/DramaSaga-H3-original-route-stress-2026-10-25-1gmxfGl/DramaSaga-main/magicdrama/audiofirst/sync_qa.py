"""Measured audio-first H3 sync QA.

This module is deliberately fail-closed: transcript equality, schema validity and
unit tests are not audiovisual acceptance. A render passes only when its decoded
waveform is measurably aligned to the approved source and every dialogue line has
an explicit visible-speaker mouth observation for the same media.
"""
from __future__ import annotations

import json
import math
import subprocess
import tempfile
import wave
from pathlib import Path

from .core import digest


def _decode_wav(path: str | Path, out: Path) -> Path:
    subprocess.run([
        'ffmpeg', '-v', 'error', '-y', '-i', str(path),
        '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(out)
    ], check=True)
    return out


def _pcm16(path: str | Path) -> tuple[list[float], int, float]:
    path = Path(path)
    tmp = None
    try:
        if path.suffix.lower() != '.wav':
            tmp = tempfile.NamedTemporaryFile(prefix='syncqa-', suffix='.wav', delete=False)
            tmp.close()
            path = _decode_wav(path, Path(tmp.name))
        with wave.open(str(path), 'rb') as f:
            if f.getsampwidth() != 2:
                raise ValueError('PCM16 WAV decode required')
            rate = f.getframerate()
            channels = f.getnchannels()
            raw = f.readframes(f.getnframes())
        vals = []
        for i in range(0, len(raw), 2 * channels):
            frame = raw[i:i + 2 * channels]
            if len(frame) < 2 * channels:
                break
            samples = [int.from_bytes(frame[c * 2:c * 2 + 2], 'little', signed=True) / 32768.0 for c in range(channels)]
            vals.append(sum(samples) / channels)
        return vals, rate, len(vals) / rate
    finally:
        if tmp:
            Path(tmp.name).unlink(missing_ok=True)


def _envelope(samples: list[float], rate: int, step: float = 0.02) -> list[float]:
    n = max(1, round(rate * step))
    out = []
    for i in range(0, len(samples), n):
        block = samples[i:i + n]
        if not block:
            continue
        out.append(math.sqrt(sum(x * x for x in block) / len(block)))
    return out


def _onset(env: list[float], step: float = 0.02) -> float:
    if not env:
        raise ValueError('Empty audio')
    peak = max(env)
    if peak <= 1e-5:
        raise ValueError('Silent audio')
    threshold = max(0.015, peak * 0.12)
    for i, value in enumerate(env):
        if value >= threshold:
            return round(i * step, 4)
    raise ValueError('Speech onset not found')


def _corr_at(a: list[float], b: list[float], lag: int) -> float:
    # lag > 0 means b starts later than a.
    if lag >= 0:
        xs, ys = a[:len(b) - lag], b[lag:]
    else:
        xs, ys = a[-lag:len(b) - lag], b[:len(b) + lag]
    n = min(len(xs), len(ys))
    if n < 25:
        return -1.0
    xs, ys = xs[:n], ys[:n]
    ma, mb = sum(xs) / n, sum(ys) / n
    va = sum((x - ma) ** 2 for x in xs)
    vb = sum((y - mb) ** 2 for y in ys)
    if va <= 1e-8 or vb <= 1e-8:
        return -1.0
    return sum((x - ma) * (y - mb) for x, y in zip(xs, ys)) / math.sqrt(va * vb)


def _best_offset(source: list[float], candidate: list[float], step: float = 0.02, max_seconds: float = 1.25) -> tuple[float, float]:
    max_lag = round(max_seconds / step)
    best = (-2.0, 0)
    for lag in range(-max_lag, max_lag + 1):
        score = _corr_at(source, candidate, lag)
        if score > best[0] + 1e-9 or (abs(score - best[0]) <= 1e-9 and abs(lag) < abs(best[1])):
            best = (score, lag)
    return round(best[1] * step, 4), round(best[0], 4)


def _segment_offset(source: list[float], candidate: list[float], start: float, end: float, step: float = 0.02, max_delta: float = 1.5) -> tuple[float, float]:
    i0 = max(0, round(start / step)); i1 = max(i0 + 3, round(end / step))
    segment = source[i0:i1]
    best = (-2.0, 0)
    max_shift = round(max_delta / step)
    for shift in range(-max_shift, max_shift + 1):
        j0 = i0 + shift
        if j0 < 0 or j0 + len(segment) > len(candidate):
            continue
        window = candidate[j0:j0 + len(segment)]
        n = len(segment)
        ma, mb = sum(segment) / n, sum(window) / n
        va = sum((x - ma) ** 2 for x in segment); vb = sum((y - mb) ** 2 for y in window)
        score = -1.0 if va <= 1e-8 or vb <= 1e-8 else sum((x - ma) * (y - mb) for x, y in zip(segment, window)) / math.sqrt(va * vb)
        if score > best[0] + 1e-9 or (abs(score - best[0]) <= 1e-9 and abs(shift) < abs(best[1])):
            best = (score, shift)
    return round(best[1] * step, 4), round(best[0], 4)


def _load_track(path: str | Path | None, video_sha: str) -> list[dict]:
    if not path:
        return []
    data = json.loads(Path(path).read_text())
    if data.get('video_sha256') != video_sha:
        raise ValueError('Mouth track belongs to different video')
    entries = data.get('entries')
    if not isinstance(entries, list):
        raise ValueError('Mouth track entries required')
    return entries


def evaluate_render_sync(
    source_audio: str | Path,
    rendered_video_audio: str | Path,
    dialogue_lines: list[dict],
    *,
    mouth_track_path: str | Path | None = None,
    rendered_video_sha256: str | None = None,
    max_offset_seconds: float = 0.12,
    min_correlation: float = 0.75,
) -> dict:
    """Measure render audio against the approved source and visible-speaker track.

    dialogue_lines use source-audio seconds: [{id,speaker,start,end,text}].
    A mouth track is required for every line midpoint in rendered-output time.
    """
    source, sr, source_seconds = _pcm16(source_audio)
    candidate, cr, candidate_seconds = _pcm16(rendered_video_audio)
    if sr != cr:
        raise ValueError('Decoded sample rates differ')
    env_a, env_b = _envelope(source, sr), _envelope(candidate, cr)
    offset, correlation = _best_offset(env_a, env_b)
    onset_a, onset_b = _onset(env_a), _onset(env_b)
    onset_offset = round(onset_b - onset_a, 4)
    video_sha = rendered_video_sha256 or digest(rendered_video_audio)
    track = _load_track(mouth_track_path, video_sha)
    line_results = []
    visible_count = 0
    for i, line in enumerate(dialogue_lines):
        start = float(line['start']); end = float(line['end'])
        if not start < end:
            raise ValueError('Dialogue line timing invalid')
        line_offset, line_correlation = _segment_offset(env_a, env_b, start, end)
        midpoint = (start + end) / 2 + line_offset
        speaker = line['speaker']
        matches = [e for e in track if e.get('speaker_id') == speaker and abs(float(e.get('t', -999)) - midpoint) <= 0.08]
        visible = bool(matches and all(e.get('face_visible') and e.get('mouth_visible') for e in matches))
        visible_count += int(visible)
        line_results.append({
            'id': line.get('id', f'line-{i + 1}'), 'speaker': speaker,
            'source_start': start, 'source_end': end, 'render_midpoint': round(midpoint, 3),
            'line_offset_seconds': line_offset, 'line_correlation': line_correlation,
            'speaker_mouth_visible': visible,
        })
    max_line_offset = max((abs(l['line_offset_seconds']) for l in line_results), default=0.0)
    min_line_correlation = min((l['line_correlation'] for l in line_results), default=0.0)
    failures = []
    if abs(offset) > max_offset_seconds:
        failures.append(f'audio envelope offset {offset}s exceeds {max_offset_seconds}s')
    if abs(onset_offset) > max_offset_seconds:
        failures.append(f'speech onset offset {onset_offset}s exceeds {max_offset_seconds}s')
    if max_line_offset > max_offset_seconds:
        failures.append(f'worst dialogue-line offset {max_line_offset}s exceeds {max_offset_seconds}s')
    if correlation < min_correlation:
        failures.append(f'audio correlation {correlation} below {min_correlation}')
    if visible_count != len(dialogue_lines):
        failures.append(f'visible speaker mouth verified for {visible_count}/{len(dialogue_lines)} dialogue lines')
    return {
        'status': 'pass' if not failures else 'fail',
        'failures': failures,
        'source_audio_sha256': digest(source_audio),
        'rendered_audio_sha256': digest(rendered_video_audio),
        'source_seconds': round(source_seconds, 4),
        'rendered_seconds': round(candidate_seconds, 4),
        'envelope_offset_seconds': offset,
        'speech_onset_offset_seconds': onset_offset,
        'envelope_correlation': correlation,
        'max_dialogue_line_offset_seconds': round(max_line_offset, 4),
        'min_dialogue_line_correlation': round(min_line_correlation, 4),
        'visible_speaker_lines': visible_count,
        'dialogue_line_count': len(dialogue_lines),
        'lines': line_results,
    }
