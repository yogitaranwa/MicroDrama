#!/usr/bin/env python3
raise RuntimeError("Historical one-off paid submission script retired. No network call made. Use reviewed manifest/ledger execution after separate approval.")
import json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
OLD=json.loads(pathlib.Path('/tmp/e01-v3-still-jobs.json').read_text()); R=OLD['refs']
REFS=[R[n]['file_path'] for n in ['ref-harry-front-close.png','ref-harry-fullbody.png','ref-draconia-front-close.png','ref-draconia-fullbody.png','ref-two-shot-dialogue.png','ref-two-shot-action.png','ref-yule-ball-location.png']]
OUT=pathlib.Path('/tmp/e01-v40-key-anchor-shot11'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v40-key-anchor-shot11-job.json')
PROMPT="""Shot 11 key anchor: the faceless masked figure has stepped out of the reflection and now advances across the glowing ballroom floor behind Harry and Draconia, copying their dance posture while they turn toward the red table. Harry has messy black hair, round glasses, white dress shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes, and a plain black formal robe with a thin red inner lining. Draconia has platinum blonde hair in a braided updo made only of hair, matching the accepted reference, with at most one small jeweled side pin; she wears the emerald green embroidered sleeveless Yule gown with sheer dark green shoulder drapes and emerald formal shoes. Preserve accepted faces and proportions. Cinematic photorealistic only, candlelit Great Hall, cool blue shadows, natural texture, coherent hands. No anime, illustration, readable text, tiara, crown, headpiece, long loose side braid, ice skates, skate blades, metal cuffs, swords or blades. Vertical 9:16."""
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:1000],file=sys.stderr)
 r.raise_for_status(); return r.json()
state=json.loads(STATE.read_text()) if STATE.exists() else {}
if 'job' not in state:
 payload={'name':'Harry Draconia E01 v4.0 key anchor shot11 masked advance','image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':PROMPT},'assets':{'image_file_paths':REFS}}
 state={'job':req('POST','/v1/ai-image-editor',json=payload),'payload':payload}; STATE.write_text(json.dumps(state,indent=2))
jid=state['job']['id']
while True:
 d=req('GET',f'/v1/image-projects/{jid}'); state['details']=d
 if d.get('status') in {'complete','error','canceled'}: break
 time.sleep(5)
state['downloaded_paths']=[]
if d.get('status')=='complete':
 for i,dl in enumerate(d.get('downloads') or [],1):
  ext='.png' if '.png' in dl['url'].split('?')[0].lower() else '.jpg'; p=OUT/f'shot11-masked-advance-{i:02d}{ext}'
  rr=requests.get(dl['url'],timeout=180); rr.raise_for_status(); p.write_bytes(rr.content); state['downloaded_paths'].append(str(p))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps({'id':jid,'status':d.get('status'),'credits_charged':d.get('credits_charged'),'downloads':state['downloaded_paths'],'error':d.get('error')},indent=2))
