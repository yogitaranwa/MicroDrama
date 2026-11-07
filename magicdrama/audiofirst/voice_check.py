"""Voice-consistency measurement and bounded pitch matching for native-audio shots.

Pitch (autocorrelation F0 on voiced frames) and spectral centroid are measured per shot and compared per speaker. These are
signal facts. They catch a voice that drifts between shots; they do not prove two voices are the same person, nor judge
acting. Noisy shots (storm, engine) give unreliable pitch and are flagged instead of trusted. Listening is still required.
"""
import math
import subprocess

import numpy as np

from .native_mix import ffmpeg_exe

SR = 16000
FRAME = 640   # 40 ms
HOP = 160     # 10 ms
MIN_PERIODICITY = 0.55


def _decode(path, start=0.0, seconds=None):
    cmd = [ffmpeg_exe(), '-v', 'error', '-nostdin', '-ss', f'{start:.3f}']
    if seconds is not None:cmd += ['-t', f'{seconds:.3f}']
    raw = subprocess.run(cmd + ['-i', str(path), '-vn', '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float64) / 32768


def speech_profile(path, start=0.0, seconds=None, min_voiced_frames=15):
    """Median F0 (Hz), spectral centroid and how much of the loud audio was clearly voiced. `reliable` is False when
    little of the loud audio is periodic (background noise dominates), so the pitch should not be trusted."""
    x = _decode(path, start, seconds)
    if len(x) < FRAME * 2:raise ValueError('Audio too short to profile')
    lo, hi = SR // 400, SR // 70
    f0s, cents, loud = [], [], 0
    window = np.hanning(FRAME)
    freqs = np.fft.rfftfreq(2 * FRAME, 1 / SR)
    gate = max(np.percentile(np.abs(x), 95) * 0.25, 0.01)
    for i in range(0, len(x) - FRAME, HOP):
        f = x[i:i + FRAME]
        if np.sqrt(np.mean(f ** 2)) < gate:continue
        loud += 1
        f = (f - f.mean()) * window
        spec = np.fft.rfft(f, 2 * FRAME)
        ac = np.fft.irfft(np.abs(spec) ** 2)[:hi + 1]
        if ac[0] <= 0:continue
        seg = ac[lo:hi + 1] / ac[0]
        k = int(np.argmax(seg))
        if seg[k] < MIN_PERIODICITY:continue
        mag = np.abs(spec)
        f0s.append(SR / (lo + k));cents.append(float((mag * freqs).sum() / (mag.sum() + 1e-12)))
    if len(f0s) < min_voiced_frames:raise ValueError('Too few voiced frames for a voice profile')
    f0s = np.array(f0s)
    fraction = len(f0s) / max(loud, 1)
    return {'median_f0': float(np.median(f0s)), 'f0_p10': float(np.percentile(f0s, 10)), 'f0_p90': float(np.percentile(f0s, 90)),
            'centroid_hz': float(np.median(cents)), 'voiced_frames': len(f0s), 'voiced_fraction': round(fraction, 2),
            'reliable': fraction >= 0.2}


def semitones(a, b):
    return 12 * math.log2(a / b)


def consistency_report(profiles, max_pitch_spread_st=3.0, max_centroid_ratio=1.35):
    """profiles: {speaker: {shot_id: profile}} (single-speaker shots only). Flags speakers whose voice drifts between shots
    and speakers who sound too alike to tell apart. Unreliable (noisy) profiles are listed but not used."""
    out, medians = {}, {}
    for speaker, shots in profiles.items():
        used = {k: v for k, v in shots.items() if v.get('reliable', True)}
        skipped = sorted(set(shots) - set(used))
        if len(used) < 2:
            out[speaker] = {'shots': len(used), 'skipped_noisy': skipped, 'status': 'not_enough_reliable_shots'}
            if used:medians[speaker] = float(np.median([p['median_f0'] for p in used.values()]))
            continue
        f0 = [p['median_f0'] for p in used.values()];cen = [p['centroid_hz'] for p in used.values()]
        spread = semitones(max(f0), min(f0));ratio = max(cen) / min(cen)
        medians[speaker] = float(np.median(f0))
        out[speaker] = {'shots': len(used), 'skipped_noisy': skipped, 'pitch_spread_semitones': round(spread, 2), 'centroid_ratio': round(ratio, 2),
                        'median_f0_by_shot': {k: round(v['median_f0'], 1) for k, v in used.items()},
                        'status': 'drifts' if spread > max_pitch_spread_st or ratio > max_centroid_ratio else 'consistent_by_signal'}
    names = list(medians)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            gap = abs(semitones(medians[a], medians[b]))
            out.setdefault('_between_speakers', {})[a + ' vs ' + b] = {'pitch_gap_semitones': round(gap, 2), 'distinct_by_pitch': gap >= 3.0}
    return {'speakers': out, 'defects': [{'type': 'voice_drift', 'speaker': s, 'spread_semitones': v['pitch_spread_semitones']}
                                          for s, v in out.items() if v.get('status') == 'drifts'],
            'scope': 'Pitch/timbre measurements only; not speaker identity, not acting. Listening required.'}


def plan_pitch_match(profiles, max_shift_st=3.0):
    """Per-shot pitch shift (semitones) that moves each reliable single-speaker shot toward that speaker's median. A shot
    needing more than `max_shift_st` is not shifted (it would sound processed): it is listed to be regenerated instead."""
    shifts, regenerate = {}, []
    for speaker, shots in profiles.items():
        used = {k: v for k, v in shots.items() if v.get('reliable', True)}
        if len(used) < 2:continue
        target = float(np.median([p['median_f0'] for p in used.values()]))
        for shot, p in used.items():
            need = semitones(target, p['median_f0'])
            if abs(need) <= 0.4:shifts[shot] = 0.0
            elif abs(need) <= max_shift_st:shifts[shot] = round(need, 2)
            else:regenerate.append({'shot': shot, 'speaker': speaker, 'needs_semitones': round(need, 2)})
    return {'shifts': shifts, 'regenerate': regenerate}
