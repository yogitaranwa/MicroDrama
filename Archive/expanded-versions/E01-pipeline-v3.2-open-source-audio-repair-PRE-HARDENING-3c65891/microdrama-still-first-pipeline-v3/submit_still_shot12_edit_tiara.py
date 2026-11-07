#!/usr/bin/env python3
import json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
STATE=pathlib.Path('/tmp/e01-v33-shot12-edit-job.json'); OUT=pathlib.Path('/tmp/e01-v33-shot12-edit'); OUT.mkdir(exist_ok=True)
SOURCE=pathlib.Path('/tmp/e01-v32-character-bible-stills/shot12-cliffhanger-marks-r2-01.png')
DR=pathlib.Path('/tmp/harry-original-h3-v4-staged/ref-draconia-front-close.png')
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:1000],file=sys.stderr)
 r.raise_for_status(); return r.json()
def upload(path):
 item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':path.suffix.lstrip('.').lower(),'type':'image'}]})['items'][0]
 with path.open('rb') as f:
  r=requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=180); r.raise_for_status()
 return item['file_path']
state=json.loads(STATE.read_text()) if STATE.exists() else {'assets':{}}
for name,path in [('source',SOURCE),('draconia_ref',DR)]:
 if name not in state['assets']:
  state['assets'][name]=upload(path); STATE.write_text(json.dumps(state,indent=2))
if 'job' not in state:
 prompt="""Edit the first image only. Remove the tiara/crown from the top of Draconia's head and reconstruct the existing platinum braided updo as hair only, with at most one small jeweled pin tucked into the side braid. Preserve everything else exactly: both faces, Harry's black formal robe with red lining, Draconia's emerald gown, joined hands, green and silver curse marks, masked figure, sealed doors, background, lighting, composition, camera crop, color and realistic texture. Do not change her braided updo into a loose side braid. No tiara, no crown, no headpiece, no new jewelry, no ice skates, no extra fingers, no distorted faces."""
 payload={'name':'Harry Draconia E01 shot12 remove tiara only','image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':prompt},'assets':{'image_file_paths':[state['assets']['source'],state['assets']['draconia_ref']]}}
 state['job']=req('POST','/v1/ai-image-editor',json=payload); state['payload']=payload; STATE.write_text(json.dumps(state,indent=2))
jid=state['job']['id']
while True:
 d=req('GET',f'/v1/image-projects/{jid}'); state['details']=d; STATE.write_text(json.dumps(state,indent=2))
 if d.get('status') in {'complete','error','canceled'}: break
 time.sleep(4)
paths=[]
if d.get('status')=='complete':
 for i,dl in enumerate(d.get('downloads') or [],1):
  ext='.png' if '.png' in dl['url'].split('?')[0].lower() else '.jpg'; p=OUT/f'shot12-tiara-removed-{i:02d}{ext}'
  rr=requests.get(dl['url'],timeout=180); rr.raise_for_status(); p.write_bytes(rr.content); paths.append(str(p))
state['downloaded_paths']=paths; STATE.write_text(json.dumps(state,indent=2))
print(json.dumps({'id':jid,'status':d.get('status'),'credits_charged':d.get('credits_charged'),'downloads':paths,'error':d.get('error')},indent=2))
