import json,pathlib,requests,time
root=pathlib.Path(__file__).parent;key=pathlib.Path(json.load(open('/tmp/mhsecretmeta.json'))['path']).read_text().strip();h={'Authorization':'Bearer '+key};base='https://api.magichour.ai'
assert not (root/'generation-jobs.json').exists()
paths=[root/'harry-crop.png',root/'draconia-ref.png'];r=requests.post(base+'/v1/files/upload-urls',headers=h,json={'items':[{'type':'image','extension':'png'}]*2},timeout=30);r.raise_for_status();up=r.json()['items'];assets=[]
for p,u in zip(paths,up):
 r=requests.put(u['upload_url'],data=p.read_bytes(),headers={'Content-Type':'image/png'},timeout=45);r.raise_for_status();assets.append(u['file_path'])
rows=[]
for i,d in enumerate([10,8,9,9]):
 who='Harry' if i%2==0 else 'Draconia'
 prompt=('Cinematic photorealistic tense ballroom argument, one continuous single-speaker close-up. Preserve exactly the reference face, hair, costume and room. '+('Young man with round glasses, black formal robe with red lining, white shirt and black tie. He is frightened and accusatory, brows tense, jaw tight, breath uneven. He turns his gaze toward the woman just off camera; ice arrow passes out of frame immediately. ' if i%2==0 else 'Young blonde woman with braided hair updo, emerald gown and sheer draped fabric. Recognition makes her frightened and defensive, brow creases, her voice almost breaks but she tries to hold control. She looks at the man just off camera. ')+ 'Natural small shoulder movement and breathing as they continue a restrained turning step, urgent danger, no smile. Keep the full face and mouth unobstructed and sharply visible throughout, no dramatic camera orbit, no cuts, no face morphing, no text. Only this one face visible. Silent visual performance for separately supplied dialogue.')
 payload={'name':f'E01-34s-argument-test-shot{i+1}-ONCE','model':'minimax-h3','resolution':'720p','audio':False,'end_seconds':d,'assets':{'image_file_path':assets[i%2]},'style':{'prompt':prompt}}
 (root/f'shot{i+1}-generation-started.txt').write_text(str(time.time()));json.dump(payload,open(root/f'shot{i+1}-request.json','w'),indent=2)
 r=requests.post(base+'/v1/image-to-video',headers=h,json=payload,timeout=60)
 if r.status_code!=200: (root/f'shot{i+1}-error.txt').write_text(r.text);r.raise_for_status()
 x=r.json();rows.append({'shot':i+1,'speaker':who,'seconds':d,'job':x});json.dump(rows,open(root/'generation-jobs.json','w'),indent=2);print(rows[-1],flush=True)
 assert sum(z['job'].get('credits_charged',0) for z in rows)<=1728
