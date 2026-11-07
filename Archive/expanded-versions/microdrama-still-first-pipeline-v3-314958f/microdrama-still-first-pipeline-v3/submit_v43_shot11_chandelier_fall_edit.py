#!/usr/bin/env python3
import json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip()
BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
OUT=pathlib.Path('/tmp/e01-v43-shot11-chandelier-fall-edit'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v43-shot11-chandelier-fall-edit-job.json')
SOURCE=pathlib.Path('/tmp/e01-v43-shot11-robe-edit/shot11-table-chandelier-robe-01.png')
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:1000],file=sys.stderr)
 r.raise_for_status(); return r.json()
def upload(path):
 item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':path.suffix.lstrip('.').lower(),'type':'image'}]})['items'][0]
 with path.open('rb') as f:
  r=requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=180); r.raise_for_status()
 return item['file_path']
state=json.loads(STATE.read_text()) if STATE.exists() else {}
if 'job' not in state:
 src=upload(SOURCE)
 prompt="""Edit only the chandelier action. Make the chandelier unmistakably mid-fall: its chain is snapped or whipping loose, the chandelier is tilted and dropping toward the icy floor behind Harry and Draconia, with a few crystals and ice fragments scattering. Preserve Harry's canonical black formal robe with thin red inner lining, white shirt, black tie, black waistcoat, accepted face, glasses, hair, hands, green and silver marks, Draconia's accepted face, hair-only braided updo, emerald gown, the flipped red banquet table shield, floor grid, candles, background, lighting and composition exactly. Cinematic photorealistic only. Do not add text, tiara, crown, long braid, skates, blades, weapons, or extra people."""
 payload={'name':'Harry Draconia E01 v4.3 shot11 chandelier mid-fall edit','image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':prompt},'assets':{'image_file_paths':[src]}}
 state={'job':req('POST','/v1/ai-image-editor',json=payload),'payload':payload}; STATE.write_text(json.dumps(state,indent=2))
jid=state['job']['id']
while True:
 d=req('GET',f'/v1/image-projects/{jid}'); state['details']=d
 if d.get('status') in {'complete','error','canceled'}: break
 time.sleep(5)
state['downloaded_paths']=[]
if d.get('status')=='complete':
 for i,dl in enumerate(d.get('downloads') or [],1):
  ext='.png' if '.png' in dl['url'].split('?')[0].lower() else '.jpg'; p=OUT/f'shot11-chandelier-midfall-{i:02d}{ext}'
  rr=requests.get(dl['url'],timeout=180); rr.raise_for_status(); p.write_bytes(rr.content); state['downloaded_paths'].append(str(p))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps({'id':jid,'status':d.get('status'),'credits_charged':d.get('credits_charged'),'downloads':state['downloaded_paths'],'error':d.get('error')},indent=2))
