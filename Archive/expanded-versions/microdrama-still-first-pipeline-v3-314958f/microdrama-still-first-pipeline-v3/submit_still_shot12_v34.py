#!/usr/bin/env python3
import json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
OLD=json.loads(pathlib.Path('/tmp/e01-v3-still-jobs.json').read_text()); REFS=[OLD['refs'][n]['file_path'] for n in ['ref-harry-front-close.png','ref-harry-fullbody.png','ref-draconia-front-close.png','ref-draconia-fullbody.png','ref-yule-ball-location.png']]
OUT=pathlib.Path('/tmp/e01-v34-shot12-composition'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v34-shot12-job.json')
PROMPT="""Vertical 9:16 cinematic photorealistic Yule Ball cliffhanger. Camera is over Draconia's shoulder from behind, so only the back of her platinum braided updo made only of hair is visible; her hairstyle matches the accepted Draconia reference and there is no headpiece at all. Harry faces camera, hurt and suspicious, with messy black hair, round glasses, white dress shirt, plain black tie and plain black formal robe with a thin red inner lining. Their joined hands in the foreground are circled by matching green and silver curse marks. Sealed ballroom doors and a faceless masked figure bowing are visible behind Harry. Draconia wears the emerald embroidered sleeveless Yule gown with sheer dark green shoulder drapes. Preserve the accepted reference faces, formal outfits and body proportions. Candlelit Great Hall, cool blue shadows, natural skin and fabric texture, coherent hands. No tiara, crown, headpiece, jewelry on top of head, long loose side braid, ice skates, skate blades, swords, blades, knives, metal cuffs, anime, illustration, readable text, extra fingers or distorted faces."""
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:1000],file=sys.stderr)
 r.raise_for_status(); return r.json()
state=json.loads(STATE.read_text()) if STATE.exists() else {}
if 'job' not in state:
 payload={'name':'Harry Draconia E01 shot12 over-shoulder composition test','image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':PROMPT},'assets':{'image_file_paths':REFS}}
 state={'job':req('POST','/v1/ai-image-editor',json=payload),'payload':payload,'submitted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}; STATE.write_text(json.dumps(state,indent=2))
jid=state['job']['id']
while True:
 d=req('GET',f'/v1/image-projects/{jid}'); state['details']=d; STATE.write_text(json.dumps(state,indent=2))
 if d.get('status') in {'complete','error','canceled'}: break
 time.sleep(4)
paths=[]
if d.get('status')=='complete':
 for i,dl in enumerate(d.get('downloads') or [],1):
  ext='.png' if '.png' in dl['url'].split('?')[0].lower() else '.jpg'; p=OUT/f'shot12-over-shoulder-{i:02d}{ext}'
  rr=requests.get(dl['url'],timeout=180); rr.raise_for_status(); p.write_bytes(rr.content); paths.append(str(p))
state['downloaded_paths']=paths; STATE.write_text(json.dumps(state,indent=2))
print(json.dumps({'id':jid,'status':d.get('status'),'credits_charged':d.get('credits_charged'),'downloads':paths,'error':d.get('error')},indent=2))
