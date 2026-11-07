#!/usr/bin/env python3
import json,subprocess,pathlib
import numpy as np
from scipy.io import wavfile
from scipy.signal import correlate
lines=json.load(open('/tmp/e01-dialogue-lines.json'))
lip_state=json.load(open('/tmp/e01-lip-jobs.json'))
results=[]
for j in lip_state['jobs']:
 line=lines[j['line']-1]
 src=line['audio']; out=f"/tmp/e01-lip-shot-{j['shot']:02d}-audio.wav"
 subprocess.run(['ffmpeg','-y','-v','error','-i',j['local'],'-vn','-ar','16000','-ac','1',out],check=True)
 # temp source 16k
 s16=f"/tmp/e01-line-audio/line-{j['line']:02d}-16k.wav"; subprocess.run(['ffmpeg','-y','-v','error','-i',src,'-ar','16000','-ac','1',s16],check=True)
 sr1,a=wavfile.read(s16); sr2,b=wavfile.read(out)
 a=a.astype(float); b=b.astype(float); a=(a-a.mean())/(a.std() or 1); b=(b-b.mean())/(b.std() or 1)
 c=correlate(b,a,mode='full'); lag=(np.argmax(c)-(len(a)-1))/sr1; corr=float(np.max(c)/len(a))
 results.append({'shot':j['shot'],'line':j['line'],'text':j['text'],'job_id':j['job']['id'],'credits':j['job']['credits_charged'],'lag_seconds':round(float(lag),3),'correlation':round(corr,4)})
pathlib.Path('/tmp/e01-lip-audio-qa.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
