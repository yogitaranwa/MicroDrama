"""Measured signal checks: freeze, silence, loudness, bed level. Never semantic review.

These establish measurable facts about bytes (frames unchanged, dead air,
levels). They do not establish that a scripted action happened, that a
performance carries emotion, or that lip sync is correct - those still need
competent review of the actual frames and listening.
"""
import json
import math
import re
import subprocess
from pathlib import Path

from .core import finite


def _stderr(args):
    return subprocess.run(args,capture_output=True,text=True,check=False).stderr


def has_audio(path):
    probe=subprocess.run(['ffprobe','-v','error','-select_streams','a','-show_entries','stream=index','-of','csv=p=0',str(path)],capture_output=True,text=True,check=False)
    return bool(probe.stdout.strip())


def freeze_windows(video,noise_db=-60.0,min_seconds=2.0):
    """Windows where measured frames do not change beyond encoder noise."""
    err=_stderr(['ffmpeg','-nostdin','-i',str(video),'-vf',f'freezedetect=n={finite(noise_db,"freeze noise",-120)}dB:d={finite(min_seconds,"freeze window",.5)}','-an','-f','null','-'])
    starts=[float(x) for x in re.findall(r'freeze_start:\s*([\d.]+)',err)]
    ends=[float(x) for x in re.findall(r'freeze_end:\s*([\d.]+)',err)]
    durs=[float(x) for x in re.findall(r'freeze_duration:\s*([\d.]+)',err)]
    return [{'start':s,'end':ends[i] if i<len(ends) else None,'duration':durs[i] if i<len(durs) else None} for i,s in enumerate(starts)]


def silence_windows(video,noise_db=-38.0,min_seconds=1.0):
    if not has_audio(video):return []
    err=_stderr(['ffmpeg','-nostdin','-i',str(video),'-af',f'silencedetect=n={finite(noise_db,"silence noise",-120)}dB:d={finite(min_seconds,"silence window",.2)}','-vn','-f','null','-'])
    starts=[float(x) for x in re.findall(r'silence_start:\s*([\d.]+)',err)]
    ends=[float(x) for x in re.findall(r'silence_end:\s*([\d.]+)',err)]
    return [{'start':s,'end':ends[i] if i<len(ends) else None} for i,s in enumerate(starts)]


def loudness(video):
    """Integrated LUFS plus volumedetect mean/max over the whole file."""
    if not has_audio(video):return {'integrated_lufs':None,'mean_db':None,'max_db':None}
    err=_stderr(['ffmpeg','-nostdin','-i',str(video),'-af','loudnorm=print_format=json','-vn','-f','null','-'])
    integrated=None
    m=re.search(r'\{[^{}]*"input_i"[^{}]*\}',err,re.DOTALL)
    if m:
        try:integrated=float(json.loads(m.group(0))['input_i'])
        except (ValueError,KeyError,json.JSONDecodeError):integrated=None
    vol=_stderr(['ffmpeg','-nostdin','-i',str(video),'-af','volumedetect','-vn','-f','null','-'])
    mean=re.search(r'mean_volume:\s*([-\d.]+)\s*dB',vol);peak=re.search(r'max_volume:\s*([-\d.]+)\s*dB',vol)
    return {'integrated_lufs':integrated,'mean_db':float(mean.group(1)) if mean else None,'max_db':float(peak.group(1)) if peak else None}


def window_level(video,start,end):
    vol=_stderr(['ffmpeg','-nostdin','-ss',f'{finite(start,"window start",0):.3f}','-to',f'{finite(end,"window end",0):.3f}','-i',str(video),'-af','volumedetect','-vn','-f','null','-'])
    mean=re.search(r'mean_volume:\s*([-\d.]+)\s*dB',vol);peak=re.search(r'max_volume:\s*([-\d.]+)\s*dB',vol)
    return {'start':start,'end':end,'mean_db':float(mean.group(1)) if mean else None,'max_db':float(peak.group(1)) if peak else None}


def dialogue_free_gaps(duration,dialogue_windows,min_gap=.5,pad=.15):
    spans=sorted((float(w['start'])-pad,float(w['end'])+pad) for w in dialogue_windows)
    merged=[]
    for s,e in spans:
        if merged and s<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],e)
        else:merged.append([s,e])
    gaps=[];cursor=0.0
    for s,e in merged:
        if s-cursor>=min_gap:gaps.append({'start':cursor,'end':s})
        cursor=max(cursor,e)
    if duration-cursor>=min_gap:gaps.append({'start':cursor,'end':duration})
    return gaps


def episode_report(video,dialogue_windows=None,opening_silence=.75,bed_below_mean_db=12.0):
    """Mechanical defect report for an assembled episode file.

    Level measurements are not audibility verdicts; real playback listening
    remains a separate human check.
    """
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(video)],text=True))
    duration=float(info['format']['duration'])
    freezes=freeze_windows(video);silences=silence_windows(video);levels=loudness(video)
    defects=[]
    for w in freezes:defects.append({'type':'freeze','start':w['start'],'end':w['end'],'duration':w['duration'],'fact':'frames unchanged beyond encoder noise in this window'})
    for w in silences:
        kind='opening_silence' if w['start']<=.05 and (w['end'] or 0)>=opening_silence else 'internal_silence'
        if kind=='opening_silence' or w['start']>.05:defects.append({'type':kind,'start':w['start'],'end':w['end'],'fact':'dead air window above threshold'})
    gaps=[]
    if dialogue_windows and levels['mean_db'] is not None:
        for gap in dialogue_free_gaps(duration,dialogue_windows):
            level=window_level(video,gap['start'],gap['end']);entry=dict(level)
            if level['mean_db'] is not None:
                delta=level['mean_db']-levels['mean_db'];entry['delta_vs_full_mean_db']=round(delta,1)
                if delta<=-bed_below_mean_db:
                    entry['flag']='gap far below full-file mean; any bed is effectively absent'
                    defects.append({'type':'bed_level','start':gap['start'],'end':gap['end'],'mean_db':level['mean_db'],'delta_db':round(delta,1),'fact':'dialogue-free gap level far below full-file mean'})
            gaps.append(entry)
    return {'video':str(video),'duration_seconds':duration,'freeze_windows':freezes,'silence_windows':silences,'loudness':levels,'gap_levels':gaps,'defects':defects,'mechanical_pass':not defects,
            'scope':'Signal measurements only: freeze, silence, levels. Does not establish scripted actions, performance emotion, lip-sync correctness or audibility in real playback.'}


def reject_frozen_video(video,min_seconds=2.0):
    """A generated video asset held static >= min_seconds cannot carry action."""
    windows=freeze_windows(video,min_seconds=min_seconds)
    if windows:raise ValueError('Frozen video asset rejected: '+json.dumps(windows))
