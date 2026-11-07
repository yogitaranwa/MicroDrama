import requests,json,pathlib,subprocess,math,time
root=pathlib.Path(__file__).parent;key=pathlib.Path(json.load(open('/tmp/mhsecretmeta.json'))['path']).read_text().strip();h={'Authorization':'Bearer '+key};base='https://api.magichour.ai';segs=json.load(open(root/'audio-segments.json'));rows=[]
assert not (root/'sync-jobs.json').exists()
assert 1728+sum(math.ceil((s['end_time_seconds']-s['start_time_seconds'])*24) for s in segs)<=2600
for i,s in enumerate(segs,1):
 d=s['end_time_seconds']-s['start_time_seconds'];v=root/f'shot{i}-trim.mp4';a=root/f'line{i}.wav';subprocess.run(['ffmpeg','-v','error','-i',str(root/f'shot{i}-motion.mp4'),'-t',str(d),'-an','-c:v','libx264','-crf','18','-r','24',str(v),'-y'],check=True)
 r=requests.post(base+'/v1/files/upload-urls',headers=h,json={'items':[{'type':'video','extension':'mp4'},{'type':'audio','extension':'wav'}]},timeout=30);r.raise_for_status();up=r.json()['items']
 for p,u,mt in zip([v,a],up,['video/mp4','audio/wav']):
  r=requests.put(u['upload_url'],data=p.read_bytes(),headers={'Content-Type':mt},timeout=60);r.raise_for_status()
 payload={'name':f'E01-34s-argument-sync-shot{i}-ONCE','start_seconds':0,'end_seconds':round(d,3),'max_fps_limit':24,'assets':{'video_source':'file','video_file_path':up[0]['file_path'],'audio_file_path':up[1]['file_path']},'style':{'generation_mode':'lite'}}
 json.dump(payload,open(root/f'shot{i}-sync-request.json','w'),indent=2);(root/f'shot{i}-sync-started.txt').write_text(str(time.time()))
 r=requests.post(base+'/v1/lip-sync',headers=h,json=payload,timeout=60)
 if r.status_code!=200: (root/f'shot{i}-sync-error.txt').write_text(r.text);r.raise_for_status()
 j=r.json();rows.append({'shot':i,'duration':d,'job':j});json.dump(rows,open(root/'sync-jobs.json','w'),indent=2);print(rows[-1],flush=True)
 assert 1728+sum(x['job']['credits_charged'] for x in rows)<=2600
