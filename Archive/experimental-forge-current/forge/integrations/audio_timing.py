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
    if result.get('ok'):
        try:
            result['output_timing']=verify_output_timing(job['expected_output'],timing)
        except (IntegrationError,OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
            result.update(ok=False,quality_status='rejected_output_timing',output_timing_error=str(exc))
    result['audio_timing']=timing
    result['dialogue_acceptance']='unreviewed' if timing['speech_preserved'] else 'rejected_truncated_test_audio'
    return result


def verify_output_timing(path, timing):
    """Verify actual muxed durations, not transcript/identity/lip synchronization."""
    from fractions import Fraction
    proc=subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(path)],
        capture_output=True,text=True,check=True,timeout=30)
    streams=json.loads(proc.stdout).get('streams',[])
    video=next((s for s in streams if s.get('codec_type')=='video'),None)
    audio=next((s for s in streams if s.get('codec_type')=='audio'),None)
    if not video or not audio:raise IntegrationError('output needs verified video AND audio streams')
    fps=float(Fraction(video.get('avg_frame_rate','0/1')))
    count=int(video.get('nb_frames','0')); vd=float(video.get('duration','nan')); ad=float(audio.get('duration','nan'))
    if fps!=25 or count!=timing['frame_count'] or not math.isfinite(vd) or abs(vd-count/25)>1/16000:
        raise IntegrationError('actual video frame/fps/duration differs from planned audio capacity')
    required=min(timing['video_seconds'],max(timing['source_audio_seconds'].values()))
    if not math.isfinite(ad) or ad+1/16000<required:
        raise IntegrationError('actual muxed audio is shorter than required speech window')
    return {'fps':fps,'frame_count':count,'video_seconds':vd,'audio_seconds':ad,
            'required_audio_seconds':required,'duration_verified':True,'av_sync':'unreviewed',
            'speech_content':'unreviewed'}
