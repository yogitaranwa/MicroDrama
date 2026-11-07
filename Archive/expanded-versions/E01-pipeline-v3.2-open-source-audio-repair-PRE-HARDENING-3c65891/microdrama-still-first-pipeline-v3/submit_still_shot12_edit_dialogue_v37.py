#!/usr/bin/env python3
import json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
OLD=json.loads(pathlib.Path('/tmp/e01-v3-still-jobs.json').read_text())
OUT=pathlib.Path('/tmp/e01-v37-shot12-dialogue-edit'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v37-shot12-dialogue-edit-job.json')
SOURCE=pathlib.Path('/tmp/harry-original-h3-v4-staged/ref-two-shot-dialogue.png')
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
if 'source' not in state['assets']:
 state['assets']['source']=upload(SOURCE); STATE.write_text(json.dumps(state,indent=2))
if 'job' not in state:
 prompt="""Edit the first photorealistic reference image only. Preserve the exact cinematic photorealistic style, camera framing, both faces, Harry's messy hair and glasses, Draconia's braided updo made only of hair, her emerald gown, Harry's black robe and formalwear, natural skin and fabric texture, and their emotional expressions. Change the scene into the final curse reveal: add matching green and silver glowing curse marks around their visible touching hands and wrists, add sealed ballroom doors and a small faceless masked figure bowing softly in the distant background, and make the lighting slightly colder and more dangerous. Do not change either face, hairstyle, outfit, pose, camera crop or photorealistic rendering. No tiara, crown, headpiece, long side braid, metal cuffs, bracelets, anime, illustration, readable text, extra fingers, distorted faces, swords or blades."""
 payload={'name':'Harry Draconia E01 shot12 grounded dialogue edit','image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':prompt},'assets':{'image_file_paths':[state['assets']['source'],OLD['refs']['ref-yule-ball-location.png']['file_path']]}}
 state['job']=req('POST','/v1/ai-image-editor',json=payload); state['payload']=payload; STATE.write_text(json.dumps(state,indent=2))
jid=state['job']['id']
while True:
 d=req('GET',f'/v1/image-projects/{jid}'); state['details']=d; STATE.write_text(json.dumps(state,indent=2))
 if d.get('status') in {'complete','error','canceled'}: break
 time.sleep(4)
paths=[]
if d.get('status')=='complete':
 for i,dl in enumerate(d.get('downloads') or [],1):
  ext='.png' if '.png' in dl['url'].split('?')[0].lower() else '.jpg'; p=OUT/f'shot12-dialogue-edit-{i:02d}{ext}'
  rr=requests.get(dl['url'],timeout=180); rr.raise_for_status(); p.write_bytes(rr.content); paths.append(str(p))
state['downloaded_paths']=paths; STATE.write_text(json.dumps(state,indent=2))
print(json.dumps({'id':jid,'status':d.get('status'),'credits_charged':d.get('credits_charged'),'downloads':paths,'error':d.get('error')},indent=2))
