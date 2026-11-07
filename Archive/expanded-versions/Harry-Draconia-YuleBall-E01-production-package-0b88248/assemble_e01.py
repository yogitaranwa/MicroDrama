#!/usr/bin/env python3
import json,subprocess,pathlib,math
lines=json.load(open('/tmp/e01-dialogue-lines.json'))
shots=[
 (1,5.0,'/tmp/e01-base-shot-01.mp4',None),
 (2,3.042,'/tmp/mh-l1-720-base.mp4','/tmp/mh-l1-720-pro.mp4'),
 (3,6.0,'/tmp/e01-base-shot-03.mp4',None),
 (4,5.0,'/tmp/e01-base-shot-04.mp4','/tmp/e01-lip-shot-04.mp4'),
 (5,6.0,'/tmp/e01-base-shot-05-reroll1.mp4','/tmp/e01-lip-shot-05.mp4'),
 (6,5.0,'/tmp/e01-base-shot-06-reroll1.mp4','/tmp/e01-lip-shot-06.mp4'),
 (7,4.0,'/tmp/e01-base-shot-07-reroll1.mp4','/tmp/e01-lip-shot-07.mp4'),
 (8,7.0,'/tmp/e01-base-shot-08.mp4',None),
 (9,5.0,'/tmp/e01-base-shot-09.mp4',None),
 (10,7.0,'/tmp/e01-base-shot-10.mp4',None),
 (11,5.0,'/tmp/e01-base-shot-11.mp4',None),
 (12,6.0,'/tmp/e01-base-shot-12-reroll1.mp4',None),
 (13,6.0,'/tmp/e01-base-shot-13-reroll1.mp4',None),
 (14,6.0,'/tmp/e01-base-shot-14.mp4',None),
 (15,5.0,'/tmp/e01-base-shot-15.mp4','/tmp/e01-lip-shot-15.mp4'),
 (16,5.0,'/tmp/e01-base-shot-16.mp4',None),
 (17,5.0,'/tmp/e01-base-shot-17.mp4','/tmp/e01-lip-shot-17.mp4'),
 (18,3.0,'/tmp/e01-base-shot-18.mp4','/tmp/e01-lip-shot-18.mp4'),
]
line_by_shot={2:1,3:2,4:3,5:4,6:5,7:6,8:7,9:8,10:9,11:10,12:11,13:12,14:13,15:14,16:15,17:16,18:17}
inputs=[]; filters=[]; vlabels=[]
def add(path):
 inputs.extend(['-i',path]); return len(inputs)//2-1
for shot,dur,base,lip in shots:
 if lip:
  li=add(lip); bi=add(base); lipdur=lines[line_by_shot[shot]-1]['duration']
  filters.append(f'[{li}:v]trim=0:{lipdur:.3f},setpts=PTS-STARTPTS,scale=570:1024,fps=24,format=yuv420p[v{shot}a]')
  filters.append(f'[{bi}:v]trim={lipdur:.3f}:{dur:.3f},setpts=PTS-STARTPTS,scale=570:1024,fps=24,format=yuv420p[v{shot}b]')
  filters.append(f'[v{shot}a][v{shot}b]concat=n=2:v=1:a=0[v{shot}]')
 else:
  bi=add(base); filters.append(f'[{bi}:v]trim=0:{dur:.3f},setpts=PTS-STARTPTS,scale=570:1024,fps=24,format=yuv420p[v{shot}]')
 vlabels.append(f'[v{shot}]')
filters.append(''.join(vlabels)+f'concat=n={len(shots)}:v=1:a=0,eq=contrast=1.025:saturation=1.02[vout]')
# dialogue track
starts={}; t=0
for shot,dur,_,_ in shots:
 starts[shot]=t; t+=dur
alabels=[]
for l in lines:
 ai=add(l['audio']); shot={v:k for k,v in line_by_shot.items()}[l['line']]
 ms=int(round(starts[shot]*1000))
 filters.append(f'[{ai}:a]aresample=48000,adelay={ms}|{ms},apad=whole_dur={t:.3f}[a{l["line"]}]')
 alabels.append(f'[a{l["line"]}]')
filters.append(''.join(alabels)+f'amix=inputs={len(alabels)}:normalize=0:dropout_transition=0[dia]')
filters.append(f'anoisesrc=color=brown:duration={t:.3f}:amplitude=0.12,lowpass=f=420,volume=0.055[room]')
filters.append('[dia][room]amix=inputs=2:duration=first:dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]')
cmd=['ffmpeg','-y','-v','error',*inputs,'-filter_complex',';'.join(filters),'-map','[vout]','-map','[aout]','-c:v','libx264','-preset','medium','-crf','18','-r','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','/tmp/Harry-Draconia-YuleBall-E01-assembly-v1.mp4']
pathlib.Path('/tmp/assemble_e01_ffmpeg.sh').write_text(' '.join(subprocess.list2cmdline([x]) for x in cmd))
print('duration',t,'inputs',len(inputs)//2)
subprocess.run(cmd,check=True)
# save timeline
out=[]; t=0
for shot,dur,base,lip in shots:
 rec={'shot':shot,'start':round(t,3),'end':round(t+dur,3),'duration':dur,'base':base,'lip':lip}
 if shot in line_by_shot:
  l=lines[line_by_shot[shot]-1]; rec.update({'line':l['line'],'text':l['text'],'line_audio':l['audio'],'line_duration':l['duration']})
 out.append(rec); t+=dur
pathlib.Path('/tmp/e01-timeline.json').write_text(json.dumps(out,indent=2))
