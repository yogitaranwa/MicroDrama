"""CPU audio repair using pyloudnorm (BS.1770) and FFmpeg decoding.
Does not certify emotional quality, music audibility, or final episode approval.
"""
import hashlib, json, subprocess
from pathlib import Path
import numpy as np
import pyloudnorm as pyln
import soundfile as sf

RATE = 44100

def decode(path):
    raw = subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-ac','2','-ar',str(RATE),'-'])
    return np.frombuffer(raw,dtype='<f4').reshape(-1,2).astype(np.float64)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rms_db(x):
    return float(20*np.log10(max(np.sqrt(np.mean(x*x)),1e-12)))

def make_voice(source, lines, beats, duration):
    result = np.zeros((round(duration*RATE),2),dtype=np.float64)
    byline = {x['line']:x for x in lines}
    windows=[]
    seen=set()
    for beat in beats:
        for w in beat['lines']:
            if w['line'] in seen:
                raise ValueError('Duplicate dialogue line placement')
            seen.add(w['line'])
            src=byline[w['line']]
            a,b=round(src['source_start']*RATE),round(src['source_end']*RATE)
            start=round(w['start']*RATE)
            if a<0 or b>len(source)+RATE//10 or b<=a or start<0:
                raise ValueError('Invalid source/timeline bounds')
            clip=source[a:min(b,len(source))]
            if start+len(clip)>len(result):
                raise ValueError('Dialogue would be truncated')
            end=start+len(clip)
            if any(start<v and end>u for u,v in windows):
                raise ValueError('Overlapping dialogue placement')
            result[start:end]+=clip
            windows.append((start,end))
    if seen!=set(byline):
        raise ValueError('Not all dialogue lines placed exactly once')
    return result,windows

def mix_stems(voice, music, windows, bed_lufs=-29, duck_db=6):
    meter=pyln.Meter(RATE)
    if len(music)<len(voice):
        raise ValueError('Music too short; no silent padding permitted')
    music=music[:len(voice)].copy()
    music=pyln.normalize.loudness(music,meter.integrated_loudness(music),bed_lufs)
    envelope=np.ones(len(voice))
    # 100ms attack before speech, 250ms release after speech, no hard toggles.
    target=10**(-duck_db/20)
    for a,b in windows:
        l=max(0,a-round(.1*RATE)); r=min(len(voice),b+round(.25*RATE))
        env=np.ones(r-l)
        env[:a-l]=np.linspace(1,target,a-l,endpoint=False)
        env[a-l:b-l]=target
        env[b-l:]=np.linspace(target,1,r-b,endpoint=False)
        envelope[l:r]=np.minimum(envelope[l:r],env)
    # Music remains present through final frame. No pre-roll silence or early fade.
    bed=music*envelope[:,None]
    mixed=voice+bed
    loudness=meter.integrated_loudness(mixed)
    mixed=pyln.normalize.loudness(mixed,loudness,-18)
    # Sample-peak safety here; true peak is checked independently by FFmpeg.
    peak=np.max(np.abs(mixed)); limit=10**(-2/20)
    if peak>limit: mixed*=limit/peak
    return mixed,bed

def repair(voice_path,music_path,plan_path,script_plan_path,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=False)
    p=json.loads(Path(plan_path).read_text()); s=json.loads(Path(script_plan_path).read_text())
    source=decode(voice_path); music=decode(music_path)
    voice,windows=make_voice(source,s['lines'],p['beats'],p['base_duration_seconds'])
    # Skip digital pre-roll only, never change spoken/audio timeline.
    meter=pyln.Meter(RATE)
    preview=music[:min(len(music),round(p['base_duration_seconds']*RATE))]
    normalized=pyln.normalize.loudness(preview,meter.integrated_loudness(preview),-29)
    block=round(.05*RATE)
    energies=[rms_db(normalized[i:i+block]) for i in range(0,len(normalized)-block,block)]
    active=[i for i,v in enumerate(energies) if v>=-42 and i+1<len(energies) and energies[i+1]>=-42]
    if not active: raise ValueError('No sustained audible music onset')
    offset=int(active[0]*block); music=music[offset:]
    # A 5ms anti-click ramp, not a multi-second fade from silence.
    music[:round(.005*RATE)]*=np.linspace(0,1,round(.005*RATE))[:,None]
    mixed,bed=mix_stems(voice,music,windows)
    sf.write(out/'dialogue-timed.wav',voice,RATE,subtype='PCM_24')
    sf.write(out/'music-ducked.wav',bed,RATE,subtype='PCM_24')
    sf.write(out/'audio-review-candidate.wav',mixed,RATE,subtype='PCM_24')
    meter=pyln.Meter(RATE)
    report={'status':'REVIEW_REQUIRED','scope':'audio repair only, not final episode',
      'emotional_listen':False,'phone_speaker_listen':False,'duration':len(mixed)/RATE,
      'placed_lines':len(windows),'music_preroll_removed_seconds':offset/RATE,
      'integrated_lufs':float(meter.integrated_loudness(mixed)),
      'sample_peak_dbfs':float(20*np.log10(np.max(np.abs(mixed)))),
      'opening_0_0.5s_rms_dbfs':rms_db(mixed[:RATE//2]),
      'tail_0.5s_rms_dbfs':rms_db(mixed[-RATE//2:]),
      'source_sha256':{str(Path(x).name):digest(x) for x in [voice_path,music_path,plan_path,script_plan_path]}}
    (out/'audio-repair-report.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser(); a.add_argument('--voice',required=True); a.add_argument('--music',required=True); a.add_argument('--assembly-plan',required=True); a.add_argument('--script-plan',required=True); a.add_argument('--output-dir',required=True)
    x=a.parse_args(); print(json.dumps(repair(x.voice,x.music,x.assembly_plan,x.script_plan,x.output_dir),indent=2))
