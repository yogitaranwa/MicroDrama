#!/usr/bin/env python3
import concurrent.futures, json, os, pathlib, requests, sys, time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
OLD=json.loads(pathlib.Path('/tmp/e01-v3-still-jobs.json').read_text()); REFS=[OLD['refs'][n]['file_path'] for n in ['ref-harry-front-close.png','ref-harry-fullbody.png','ref-draconia-front-close.png','ref-draconia-fullbody.png','ref-yule-ball-location.png']]
OUT=pathlib.Path('/tmp/e01-v32-character-bible-stills'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v32-still-jobs.json')
BIBLE="""Harry has messy black hair, round glasses, a white dress shirt, plain black tie, dark trousers, a plain black formal robe with a thin red inner lining, and plain black formal dress shoes. Draconia has platinum blonde hair in a braided crown updo matching the accepted reference, with only the small jeweled braid pin from that reference, and wears the emerald green embroidered sleeveless Yule gown with sheer dark green shoulder drapes and emerald formal dress shoes. Preserve the exact accepted reference faces, hair, outfits, footwear and body proportions. No waistcoat, tuxedo jacket, long loose side braid, tiara, crown, new jewelry, ice skates, skate blades, boots, swords, blades, knives or metal cuffs. Cinematic photorealistic, candlelit Great Hall, cool blue shadows, natural skin and fabric texture, restrained expressions, coherent hands. No anime, illustration, readable text, extra fingers or distorted faces."""
SHOTS=[
('shot03-dialogue-close-r2',"Shot 3 dialogue closeup: Draconia holds Harry's hand and turns him through the dancers, urgent but controlled. Harry and Draconia are on foot in formal dress shoes. In the background, a separate guest in a pale dress is frozen in place, with glowing floor marks around that guest's shoes. Harry and Draconia are outside that warning circle. Vertical 9:16 still."),
('shot12-cliffhanger-marks-r2',"Shot 12 cliffhanger closeup: Harry and Draconia's joined hands are circled by matching green and silver curse marks. Sealed ballroom doors and a faceless masked figure bowing are visible softly behind them. Their expressions are shaken and suspicious, not romanticized. Draconia has no tiara or crown, only the small jeweled braid pin in her braided updo. Vertical 9:16 still."),
]
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:1000],file=sys.stderr)
 r.raise_for_status(); return r.json()
def submit(x):
 name,scene=x; payload={'name':'Harry Draconia E01 v3.2 bible correction '+name,'image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':scene+' '+BIBLE},'assets':{'image_file_paths':REFS}}
 job=req('POST','/v1/ai-image-editor',json=payload); return {'name':name,'job':job,'payload':payload,'submitted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
def poll(rec):
 jid=rec['job']['id']
 while True:
  d=req('GET',f'/v1/image-projects/{jid}'); rec['details']=d
  if d.get('status') in {'complete','error','canceled'}: break
  time.sleep(4)
 rec['downloaded_paths']=[]
 if d.get('status')=='complete':
  for i,dl in enumerate(d.get('downloads') or [],1):
   ext='.png' if '.png' in dl['url'].split('?')[0].lower() else '.jpg'; p=OUT/f"{rec['name']}-{i:02d}{ext}"
   rr=requests.get(dl['url'],timeout=180); rr.raise_for_status(); p.write_bytes(rr.content); rec['downloaded_paths'].append(str(p))
 return rec
state=json.loads(STATE.read_text()) if STATE.exists() else {'jobs':[]}
if not state['jobs']:
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: state['jobs']=list(ex.map(submit,SHOTS))
 STATE.write_text(json.dumps(state,indent=2))
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: state['jobs']=list(ex.map(poll,state['jobs']))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps([{'name':j['name'],'id':j['job']['id'],'status':j['details'].get('status'),'credits_charged':j['details'].get('credits_charged'),'downloads':j.get('downloaded_paths',[]),'error':j['details'].get('error')} for j in state['jobs']],indent=2))
