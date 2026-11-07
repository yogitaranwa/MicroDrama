#!/usr/bin/env python3
import json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
OLD=json.loads(pathlib.Path('/tmp/e01-v3-still-jobs.json').read_text()); REFS=[OLD['refs'][n]['file_path'] for n in ['ref-draconia-front-close.png','ref-draconia-fullbody.png','ref-harry-front-close.png','ref-harry-fullbody.png','ref-yule-ball-location.png']]
OUT=pathlib.Path('/tmp/e01-v36-shot12-reverse-tight'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v36-shot12-reverse-job.json')
PROMPT="""Vertical 9:16 cinematic photorealistic Yule Ball final-reveal closeup. Camera is tight on Draconia's face and joined hands; the top of her head is cropped out of frame, so no hair ornament can appear. Draconia faces Harry, hurt and honest, saying the final warning reveal. Her platinum hair is pulled back in the accepted braided updo, but only the lower braided edge is visible; no tiara, crown, headpiece, or loose side braid. She wears the emerald embroidered sleeveless Yule gown with sheer dark green shoulder drapes. Harry is only a soft out-of-focus shoulder and messy hair edge in the foreground, wearing the canonical black robe with red lining over white shirt, black long tie and black buttoned waistcoat. Their joined hands low in frame carry matching green and silver curse marks; no metal cuffs or bracelets. Sealed ballroom doors and a faceless masked figure bowing are visible softly behind her. Preserve the accepted reference faces and outfits. Candlelit Great Hall, cool blue shadows, natural skin and fabric texture, coherent hands. No anime, illustration, readable text, extra fingers, distorted faces, ice skates, skate blades, swords, blades, knives, metal cuffs or bracelets."""
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:1000],file=sys.stderr)
 r.raise_for_status(); return r.json()
state=json.loads(STATE.read_text()) if STATE.exists() else {}
if 'job' not in state:
 payload={'name':'Harry Draconia E01 shot12 tight Draconia reveal test','image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':PROMPT},'assets':{'image_file_paths':REFS}}
 state={'job':req('POST','/v1/ai-image-editor',json=payload),'payload':payload,'submitted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}; STATE.write_text(json.dumps(state,indent=2))
jid=state['job']['id']
while True:
 d=req('GET',f'/v1/image-projects/{jid}'); state['details']=d; STATE.write_text(json.dumps(state,indent=2))
 if d.get('status') in {'complete','error','canceled'}: break
 time.sleep(4)
paths=[]
if d.get('status')=='complete':
 for i,dl in enumerate(d.get('downloads') or [],1):
  ext='.png' if '.png' in dl['url'].split('?')[0].lower() else '.jpg'; p=OUT/f'shot12-draconia-reveal-tight-{i:02d}{ext}'
  rr=requests.get(dl['url'],timeout=180); rr.raise_for_status(); p.write_bytes(rr.content); paths.append(str(p))
state['downloaded_paths']=paths; STATE.write_text(json.dumps(state,indent=2))
print(json.dumps({'id':jid,'status':d.get('status'),'credits_charged':d.get('credits_charged'),'downloads':paths,'error':d.get('error')},indent=2))
