#!/usr/bin/env python3
import json,pathlib,requests,sys,time
KEY=pathlib.Path(sys.argv[1]).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
state_path=pathlib.Path('/tmp/e01-base-jobs.json'); state=json.loads(state_path.read_text())
def req(method,path,**kw):
 r=requests.request(method,BASE+path,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(method,path,r.status_code,r.text[:1000],file=sys.stderr)
 r.raise_for_status(); return r.json()
def upload(local):
 item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':'png','type':'image'}]})['items'][0]
 with open(local,'rb') as f: requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=180).raise_for_status()
 return item['file_path']
state.setdefault('rerolls',[])
# Recover shot 12 reroll that was submitted before the earlier state-save exception.
if not any(r['job']['id']=='cmvnlvyre00nyje01dx3prya1' for r in state['rerolls']):
 state['rerolls'].append({'shot':12,'duration':6,'ref':'two-shot-dialogue','action':'continuity reroll submitted before state-save exception','job':{'id':'cmvnlvyre00nyje01dx3prya1','estimated_frame_cost':288,'credits_charged':288},'reason':'first base changed Draconia gown color and failed continuity QA','submitted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')})
if 'harry-front-close' not in state['refs']:
 state['refs']['harry-front-close']={'local':'/tmp/harry-original-h3-v4-staged/ref-harry-front-close.png','file_path':upload('/tmp/harry-original-h3-v4-staged/ref-harry-front-close.png')}
COMMON='Vertical cinematic photorealistic enchanted Yule Ball in the Great Hall, candlelit, realistic skin and fabric, coherent physics, controlled cinematic motion, no anime, no illustration, no readable text, no duplicate foreground people.'
action='Close on Harry looking down through the dancers at a faint glowing geometric waltz grid in the marble floor. He realizes the attacker is using the grid and deliberately steps off the marked line. Serious controlled realization, natural mouth movement in the opening second, no smiling, no generic dancing cutaway.'
payload={'name':'Harry Draconia E01 shot 13 720p base reroll 1','end_seconds':6,'model':'minimax-h3','resolution':'720p','audio':False,'style':{'prompt':COMMON+' '+action},'assets':{'image_file_path':state['refs']['harry-front-close']['file_path']}}
job=req('POST','/v1/image-to-video',json=payload)
state['rerolls'].append({'shot':13,'duration':6,'ref':'harry-front-close','action':action,'payload':payload,'job':job,'reason':'first base was generic ball and failed action QA','submitted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')})
state_path.write_text(json.dumps(state,indent=2))
print(job)
