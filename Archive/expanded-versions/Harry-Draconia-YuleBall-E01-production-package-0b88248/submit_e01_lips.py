#!/usr/bin/env python3
import json,pathlib,requests,subprocess,sys,time
KEY=pathlib.Path(sys.argv[1]).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
resp1=json.load(open('/tmp/harry-e01-action-scene-tts-response.json'))
resp2=json.load(open('/tmp/harry-e01-remaining-tts-response.json'))
texts1=["Potter, don't turn around.","Dance now, insult me later.","This is how Slytherins ask?","It's how they keep you alive.","They follow the offbeat.","Then count faster."]
texts2=["Show off.","Efficient.","I definitely planned that.","You didn't.","He's using the Waltz grid.","Then we break the grid.","That was your plan.","Left side, three beats, red table.","It has our names.","What did you do?","I tried to warn you."]
line_sources=[]
for i,s in enumerate(resp1['voice_segments']): line_sources.append({'line':i+1,'text':texts1[i],'source':'/tmp/Harry_Draconia_E01_action_scene_v1.mp3','start':s['start_time_seconds'],'end':s['end_time_seconds'],'voice_id':s['voice_id']})
for i,s in enumerate(resp2['voice_segments']): line_sources.append({'line':i+7,'text':texts2[i],'source':'/tmp/Harry_Draconia_E01_remaining_dialogue_v1.mp3','start':s['start_time_seconds'],'end':s['end_time_seconds'],'voice_id':s['voice_id']})
outdir=pathlib.Path('/tmp/e01-line-audio'); outdir.mkdir(exist_ok=True)
for l in line_sources:
 out=outdir/f"line-{l['line']:02d}.wav"; l['audio']=str(out); l['duration']=round(l['end']-l['start'],3)
 if not out.exists() or out.stat().st_size<1000:
  subprocess.run(['ffmpeg','-y','-v','error','-ss',str(l['start']),'-to',str(l['end']),'-i',l['source'],'-ar','48000','-ac','1',str(out)],check=True)
pathlib.Path('/tmp/e01-dialogue-lines.json').write_text(json.dumps(line_sources,indent=2))
# Visible-face Pro shots. Shot 13 deliberately stays off-screen/grid dialogue because its selected visual is mostly over-shoulder/back-of-head.
LIP={4:3,5:4,6:5,7:6,15:14,17:16,18:17}
def req(method,path,**kw):
 r=requests.request(method,BASE+path,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(method,path,r.status_code,r.text[:1200],file=sys.stderr)
 r.raise_for_status(); return r.json()
def upload(local,typ):
 ext=pathlib.Path(local).suffix.lstrip('.').lower()
 item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':ext,'type':typ}]})['items'][0]
 with open(local,'rb') as f: requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=180).raise_for_status()
 return item['file_path']
state_path=pathlib.Path('/tmp/e01-lip-jobs.json'); state=json.loads(state_path.read_text()) if state_path.exists() else {'jobs':[]}
existing={j['shot'] for j in state['jobs']}
for shot,line_no in LIP.items():
 if shot in existing: continue
 l=line_sources[line_no-1]
 video=f'/tmp/e01-base-shot-{shot:02d}-reroll1.mp4' if shot in (5,6,7,13) else f'/tmp/e01-base-shot-{shot:02d}.mp4'
 if not pathlib.Path(video).exists(): video=f'/tmp/e01-base-shot-{shot:02d}.mp4'
 vfile=upload(video,'video'); afile=upload(l['audio'],'audio')
 payload={'name':f'Harry Draconia E01 shot {shot:02d} Pro lip line {line_no:02d}','start_seconds':0,'end_seconds':l['duration'],'max_fps_limit':24,'assets':{'video_source':'file','video_file_path':vfile,'audio_file_path':afile},'style':{'generation_mode':'pro'}}
 job=req('POST','/v1/lip-sync',json=payload)
 state['jobs'].append({'shot':shot,'line':line_no,'text':l['text'],'duration':l['duration'],'video_local':video,'audio_local':l['audio'],'payload':payload,'job':job,'submitted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')})
 state_path.write_text(json.dumps(state,indent=2))
 print('submit',shot,line_no,job)
print(json.dumps({'submitted':len(state['jobs']),'credits':sum(j['job'].get('credits_charged',0) for j in state['jobs'])},indent=2))
