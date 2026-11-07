import json,wave
import pytest
from forge.integrations.audio_timing import check_speech_duration, probe_audio_duration, execute_audio_job_preserving_speech
from forge.integrations.registry import IntegrationError

def test_17frames_cannot_preserve_1point2_seconds():
    with pytest.raises(IntegrationError, match='never silently'):check_speech_duration(17, {'person1':1.2})

def test_test_crop_is_explicit_not_dialogue_acceptance():
    report=check_speech_duration(17, {'person1':1.2},allow_test_truncation=True)
    assert report['video_seconds']==.68 and not report['speech_preserved']
    assert report['truncated_seconds']['person1']==pytest.approx(.52)

def test_33frames_preserve1point2_without_speed_change():
    report=check_speech_duration(33,{'person1':1.2})
    assert report['speech_preserved'] and report['video_seconds']==1.32

def test_both_speakers_checked():
    with pytest.raises(IntegrationError):check_speech_duration(17,{'person1':.5,'person2':1.2})

def test_real_wav_duration_and_no_model_launch_on_truncation(tmp_path,monkeypatch):
    path=tmp_path/'audio.wav'
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0\0'*19200)
    assert probe_audio_duration(path)==1.2
    manifest=tmp_path/'input.json';manifest.write_text(json.dumps({'cond_audio':{'person1':str(path)}}))
    def fail(*a,**k):raise AssertionError('model must not launch')
    monkeypatch.setattr('forge.integrations.execute.execute_audio_job',fail)
    with pytest.raises(IntegrationError):execute_audio_job_preserving_speech({'argv':['python','--input_json',str(manifest)],'frame_num':17})

def test_real_mux_duration_checks_and_short_output_rejection(tmp_path):
    import subprocess
    from forge.integrations.audio_timing import verify_output_timing
    output=tmp_path/'test.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=s=16x16:r=25:d=1.32','-f','lavfi','-i','sine=frequency=300:sample_rate=16000:duration=1.2','-c:v','libx264','-c:a','aac',str(output)],check=True)
    timing=check_speech_duration(33,{'person1':1.2})
    report=verify_output_timing(output,timing)
    assert report['duration_verified'] and report['speech_content']=='unreviewed'
    short=tmp_path/'short.mp4'
    subprocess.run(['ffmpeg','-v','error','-i',str(output),'-t','0.68','-c','copy',str(short)],check=True)
    with pytest.raises(IntegrationError):verify_output_timing(short,timing)

def test_runtime_success_cannot_hide_output_timing_failure(tmp_path,monkeypatch):
    manifest=tmp_path/'input.json';manifest.write_text(json.dumps({'cond_audio':{'person1':'voice'}}))
    monkeypatch.setattr('forge.integrations.audio_timing.probe_audio_duration',lambda p:1.2)
    monkeypatch.setattr('forge.integrations.execute.execute_audio_job',lambda *a,**k:{'ok':True})
    def bad(*a):raise IntegrationError('actual muxed audio is shorter')
    monkeypatch.setattr('forge.integrations.audio_timing.verify_output_timing',bad)
    result=execute_audio_job_preserving_speech({'argv':['--input_json',str(manifest)],'frame_num':33,'expected_output':'output'})
    assert result['ok'] is False and result['quality_status']=='rejected_output_timing'
