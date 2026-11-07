"""Explicit 25fps speech-preservation checks for the pinned audio backends.

Their muxer crops audio to frame_count / 25. A runtime pass cannot prove full
speech is preserved. Legacy execution stays available; use the guarded entry
point here for dialogue. Test truncation requires a separate explicit flag.
"""
import json
import math
import subprocess
from pathlib import Path
from .registry import IntegrationError


def probe_audio_duration(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
        '-show_entries', 'stream=duration:format=duration', '-of', 'json', str(path)],
        check=True, capture_output=True, text=True, timeout=30)
    info = json.loads(result.stdout)
    if not info.get('streams'):
        raise IntegrationError('source has no verified audio stream')
    duration = float(info['streams'][0].get('duration', info.get('format', {}).get('duration', 'nan')))
    if not math.isfinite(duration) or duration <= 0:
        raise IntegrationError('source audio duration is not verifiable')
    return duration


def check_speech_duration(frame_count, audio_seconds, *, allow_test_truncation=False):
    if type(frame_count) is not int or frame_count < 5 or (frame_count - 1) % 4:
        raise IntegrationError('audio frame count must be4n+1')
    if type(allow_test_truncation) is not bool:
        raise IntegrationError('test truncation flag must be bool')
    capacity = frame_count / 25
    durations = {name: float(value) for name, value in audio_seconds.items()}
    if not durations or any(not math.isfinite(v) or v <= 0 for v in durations.values()):
        raise IntegrationError('every source audio duration must be verified')
    truncated = {name: max(0., value-capacity) for name, value in durations.items() if value > capacity + 1/16000}
    report = {'fps':25, 'frame_count':frame_count, 'video_seconds':capacity,
        'source_audio_seconds':durations, 'truncated_seconds':truncated,
        'speech_preserved':not truncated, 'test_truncation_explicit':allow_test_truncation,
        'audio_policy':'upstream prefix crop, no retiming'}
    if truncated and not allow_test_truncation:
        raise IntegrationError('audio exceeds video capacity; increase4n+1frame count, never silently crop or speed speech')
    return report


def execute_audio_job_preserving_speech(job, *, allow_test_truncation=False, **kwargs):
    """Fail closed before model launch when any source would be cropped."""
    argv=job.get('argv', [])
    try:
        data=json.loads(Path(argv[argv.index('--input_json')+1]).read_text())
        sources=data['cond_audio']
        durations={name:probe_audio_duration(path) for name,path in sources.items()}
        timing=check_speech_duration(job['frame_num'], durations,
            allow_test_truncation=allow_test_truncation)
    except (KeyError, ValueError, IndexError, OSError, subprocess.SubprocessError) as exc:
        raise IntegrationError('audio duration preflight failed: '+str(exc)) from exc
    from .execute import execute_audio_job
    result=execute_audio_job(job, **kwargs)
    result['audio_timing']=timing
    result['dialogue_acceptance']='unreviewed' if timing['speech_preserved'] else 'rejected_truncated_test_audio'
    return result
