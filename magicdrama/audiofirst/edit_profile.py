"""Measure how a finished video feels as an edit, and compare it with a reference video. Numbers only; judging stays with a person.

Measured: cut rhythm, how much actually moves between cuts, how far the sound level jumps at each cut (a continuous music or
ambience bed keeps this small), loudness range, and how much of the time the sound floor is empty. Derived from a reference the user
pointed at as "fast, clear, understandable": it cuts about every 4.6 s, moves about a third more than our shots, jumps about 9 dB at
cuts (ours 20) and has twice our loudness range.
"""
import re
import subprocess

import numpy as np

from .native_mix import ffmpeg_exe

W, H = 160, 90


def detect_cuts(path, threshold=0.25):
    """Seconds of hard cuts, from scene-change detection."""
    err = subprocess.run([ffmpeg_exe(), '-hide_banner', '-nostdin', '-i', str(path), '-vf', f"select='gt(scene,{threshold})',showinfo", '-an', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    times = sorted({round(float(t), 3) for t in re.findall(r'pts_time:([\d.]+)', err)})
    return [t for t in times if t > 0.3]


def _frames(path):
    raw = subprocess.run([ffmpeg_exe(), '-v', 'error', '-i', str(path), '-vf', f'fps=24,scale={W}:{H},format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(float)


def _audio(path, channels=1):
    result = subprocess.run([ffmpeg_exe(), '-v', 'error', '-nostdin', '-i', str(path), '-vn', '-ac', str(channels), '-ar', '16000', '-f', 's16le', '-'], capture_output=True)
    if result.returncode:raise RuntimeError('Audio measurement failed: ' + result.stderr.decode(errors='replace')[:600])
    audio = np.frombuffer(result.stdout, np.int16).astype(float) / 32768
    return audio if channels == 1 else audio.reshape(-1, channels)


def _db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def cut_audio_levels(audio, cuts, sample_rate=16000, window_seconds=0.25, warning_db=12.0):
    """Adjacent-window RMS changes, not click detection or a perceptual loudness verdict.

    Stereo is measured by channel power, avoiding phase cancellation from mono downmix.
    Incomplete windows are explicit skips, never wrapped slices or shorter comparisons.
    """
    if not np.isfinite(window_seconds) or window_seconds <= 0 or sample_rate <= 0:
        raise ValueError('Positive window and sample rate required')
    if not np.isfinite(warning_db) or warning_db <= 0:raise ValueError('Positive warning threshold required')
    width = round(sample_rate * window_seconds)
    if width < 1:raise ValueError('Window must contain samples')
    rows = []
    for cut in cuts:
        cut = float(cut)
        if not np.isfinite(cut):raise ValueError('Finite cut time required')
        center = round(cut * sample_rate)
        row = {'at_seconds': round(cut, 3)}
        if center < width or center + width > len(audio):
            row.update(status='skipped', reason='incomplete_audio_window')
        else:
            before, after = _db(audio[center - width:center]), _db(audio[center:center + width])
            delta = float(after - before)
            row.update(status='measured', before_dbfs=round(float(before), 1), after_dbfs=round(float(after), 1),
                       delta_db=round(delta, 1), jump_db=round(abs(delta), 1), review=bool(abs(delta) >= warning_db))
        rows.append(row)
    measured = [r for r in rows if r['status'] == 'measured']
    return {'window_seconds': window_seconds, 'warning_db': warning_db, 'cuts': rows,
            'review_count': sum(r['review'] for r in measured),
            'guidance': 'Review flagged cuts in playback. Check adjacent shot gain and ambience continuity; retain intentional impacts and quiet beats. '
                        'Short fades address clicks, not sustained level changes. Do not auto-normalize these warnings.',
            'scope': 'Stereo channel-power RMS over adjacent windows; not LUFS, click detection, speech detection or an automatic defect.'}


def cut_audio_report(path, cuts, warning_db=12.0):
    """Measure the final mix at known edit boundaries; no media is modified."""
    return cut_audio_levels(_audio(path, channels=2), cuts, warning_db=warning_db)


def edit_profile(path, cuts=None):
    frames, audio = _frames(path), _audio(path)
    duration = len(frames) / 24
    cuts = detect_cuts(path) if cuts is None else list(cuts)
    diff = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    near = {i + d for c in cuts for i in [int(round(c * 24))] for d in (-1, 0, 1)}
    motion = np.array([v for i, v in enumerate(diff) if i not in near]) if len(diff) else np.array([0.0])
    jumps = [abs(_db(audio[int(c * 16000):int(c * 16000) + 4000]) - _db(audio[int(c * 16000) - 4000:int(c * 16000)]))
             for c in cuts if 4000 < int(c * 16000) < len(audio) - 4000]
    win = 8000
    levels = np.array([_db(audio[i:i + win]) for i in range(0, max(len(audio) - win, 1), win)])
    err = subprocess.run([ffmpeg_exe(), '-hide_banner', '-nostdin', '-i', str(path), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    lra = re.findall(r'LRA:\s*([\d.]+)', err)
    return {'seconds': round(duration, 2), 'cuts': len(cuts), 'seconds_per_cut': round(duration / max(len(cuts), 1), 2),
            'motion_mean': round(float(motion.mean()), 2), 'motion_p90': round(float(np.percentile(motion, 90)), 2),
            'audio_jump_mean_db': round(float(np.mean(jumps)), 1) if jumps else None, 'audio_jump_max_db': round(float(np.max(jumps)), 1) if jumps else None,
            'quiet_fraction': round(float(np.mean(levels < -45)), 2), 'loudness_range_lu': float(lra[-1]) if lra else None,
            'cut_audio': cut_audio_report(path, cuts)}


def compare_profiles(reference, ours, motion_floor=0.8, jump_ceiling=1.5, lra_floor=0.7):
    """Where `ours` is further from `reference` than the tolerances. Each finding names what an editor would change."""
    gaps = []
    if ours['motion_mean'] < reference['motion_mean'] * motion_floor or ours['motion_p90'] < reference['motion_p90'] * 0.7:
        gaps.append({'metric': 'movement', 'ours': (ours['motion_mean'], ours['motion_p90']), 'reference': (reference['motion_mean'], reference['motion_p90']),
                     'fix': 'push-ins/pull-outs, camera moves in the prompt, flash or shake on impacts'})
    if ours['audio_jump_mean_db'] and reference['audio_jump_mean_db'] and ours['audio_jump_mean_db'] > reference['audio_jump_mean_db'] * jump_ceiling:
        gaps.append({'metric': 'sound jumps at cuts', 'ours': ours['audio_jump_mean_db'], 'reference': reference['audio_jump_mean_db'],
                     'fix': 'one continuous music bed and ambience under every cut'})
    if ours['loudness_range_lu'] and reference['loudness_range_lu'] and ours['loudness_range_lu'] < reference['loudness_range_lu'] * lra_floor:
        gaps.append({'metric': 'flat dynamics', 'ours': ours['loudness_range_lu'], 'reference': reference['loudness_range_lu'],
                     'fix': 'music swells, sound-effect stings, louder impacts against quiet beats'})
    if abs(ours['seconds_per_cut'] - reference['seconds_per_cut']) > 0.3 * reference['seconds_per_cut']:
        gaps.append({'metric': 'cut rhythm', 'ours': ours['seconds_per_cut'], 'reference': reference['seconds_per_cut'], 'fix': 'merge or split shots'})
    return {'gaps': gaps, 'scope': 'Measured edit statistics only; says nothing about acting, voices or story.'}
