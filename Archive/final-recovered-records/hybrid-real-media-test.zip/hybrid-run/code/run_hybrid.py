"""Actual-media hybrid process test: camera-linked review + our audio-first assembly.
Original local implementation. No third-party repo execution, API, installs or production writes.
"""
import hashlib,json,subprocess,argparse
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd):
 p=subprocess.run(cmd,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr[-3000:])
 return p.stdout

def probe(p):return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
def render(root,current):
 inputs=root/'inputs';out=root/'results';out.mkdir(exist_ok=True)
 lock=json.loads((current/'production-2026-10-26/accepted-audio-sha256-lock.json').read_text())
 parts=[('e01-s17-b1.mp4',3.0,'e01-l16-harry.mp3'),('e01-s18-b1.mp4',4.5,None),('e01-s18-b2.mp4',1.5,None)]
 takes=['e01-l16-harry.mp3','e01-l17-draconia.mp3']; bindings=[]
 for take in takes:
  source=current/'accepted-audio'/take
  if sha(source)!=lock[take]:raise ValueError('Locked take mismatch')
  target=inputs/take
  if not target.exists():target.write_bytes(source.read_bytes())
  bindings.append({'file':take,'sha256':sha(source),'duration':float(probe(source)['format']['duration'])})
 # Rebuild explicit 3s + 4.5s + 1.5s timeline from existing footage, never generated audio.
 cmd=['ffmpeg','-y','-v','error']
 for name,_,_ in parts:cmd+=['-i',str(inputs/name)]
 cmd+=['-i',str(inputs/takes[0]),'-i',str(inputs/takes[1])]
 f=[]
 for i,(_,dur,_) in enumerate(parts):
  f.append(f'[{i}:v]trim=duration={dur},setpts=PTS-STARTPTS,scale=540:960,setsar=1,fps=30[v{i}]')
 f += ['[v0][v1][v2]concat=n=3:v=1:a=0[v]',
       '[3:a]aresample=48000,aformat=channel_layouts=mono,apad=whole_dur=3,atrim=duration=3[a0]',
       '[4:a]aresample=48000,aformat=channel_layouts=mono,apad=whole_dur=6,atrim=duration=6[a1]',
       '[a0][a1]concat=n=2:v=0:a=1[a]']
 target=out/'hybrid-e01-s17-s18-process-test.mp4'
 cmd+=['-filter_complex',';'.join(f),'-map','[v]','-map','[a]','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(target)]
 run(cmd)
 # Reference PCM masters establish exact intended audio samples before AAC export.
 master=out/'hybrid-approved-takes-master.wav'
 run(['ffmpeg','-y','-v','error','-i',str(inputs/takes[0]),'-i',str(inputs/takes[1]),'-filter_complex','[0:a]aresample=48000,aformat=channel_layouts=mono,apad=whole_dur=3,atrim=duration=3[a0];[1:a]aresample=48000,aformat=channel_layouts=mono,apad=whole_dur=6,atrim=duration=6[a1];[a0][a1]concat=n=2:v=0:a=1[a]','-map','[a]','-c:a','pcm_s16le',str(master)])
 info=probe(target);v=next(s for s in info['streams'] if s['codec_type']=='video')
 result={'status':'process_completed_quality_not_accepted','output':target.name,'output_sha256':sha(target),'duration':float(info['format']['duration']),'dimensions':[v['width'],v['height']],'fps':v['avg_frame_rate'],
 'audio_bindings':bindings,'master_pcm_sha256':sha(master),'audio_note':'Original MP3 bytes preserved. Decode/resample/pad only; MP4 AAC is lossy, not byte-identical PCM.',
 'timeline':[{'source':name,'source_sha256':sha(inputs/name),'seconds':dur} for name,dur,_ in parts],
 'camera_plan':[{'id':'harry_cu','shots':['s17b1'],'parent':None},{'id':'draconia_cu','shots':['s18b1'],'parent':'harry_cu','reason':'same conversation location and reverse speaker coverage; supplied footage, not new angle generation'},{'id':'hall_insert','shots':['s18b2'],'parent':None,'reason':'establishing aftermath insert; no speaker face'}],
 'visual_review':{'source_sampling':'3 samples per beat in hybrid-source-review.png','identity':'readable adult faces across selected samples','wardrobe':'Harry red-lined robe/black bow tie; Draconia green gown in selected source frames','continuity_failed':['Intact hanging chandeliers remain in dialogue backgrounds despite prior crash in plot','Draconia close-up moves toward near-lens gaze'], 'lip_sync':'not verified; original generated mouths remain, no lipsync run'},
 'sources':'ViMax-inspired explicit camera provenance and candidate review, combined with original production locked-audio/timing approach. No external repository code executed or copied.',
 'scope':'No new generation and no production merge. This demonstrates an executable local hybrid edit path, not improved photoreal synthesis.'}
 (out/'run-result.json').write_text(json.dumps(result,indent=2));(out/'ffmpeg-command.json').write_text(json.dumps(cmd,indent=2))
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--current',type=Path,required=True);a=p.parse_args();render(a.root,a.current)
