#!/usr/bin/env python3
import concurrent.futures,json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
OLD=json.loads(pathlib.Path('/tmp/e01-v3-still-jobs.json').read_text()); R=OLD['refs']
REFS=[R[n]['file_path'] for n in ['ref-harry-front-close.png','ref-harry-fullbody.png','ref-draconia-front-close.png','ref-draconia-fullbody.png','ref-two-shot-dialogue.png','ref-two-shot-action.png','ref-yule-ball-location.png']]
OUT=pathlib.Path('/tmp/e01-v39-key-anchor-repairs'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v39-key-anchor-repair-jobs.json')
BIBLE="""Canonical identities and wardrobe: Harry has messy black hair, round glasses, white dress shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes, and a plain black formal robe with a thin red inner lining. Draconia has platinum blonde hair in a braided updo made only of hair, matching the accepted reference, with at most one small jeweled side pin; she wears the emerald green embroidered sleeveless Yule gown with sheer dark green shoulder drapes and emerald formal shoes. Preserve the accepted reference faces, hair, outfits and body proportions. Cinematic photorealistic only, candlelit Great Hall, cool blue shadows, natural skin and fabric texture, coherent hands. No anime, illustration, cartoon, readable text, letters, words, typography, extra fingers, distorted faces, tiara, crown, headpiece, long loose side braid, ice skates, skate blades, metal cuffs, bracelets, swords, rapiers, blades or knives."""
SHOTS=[
('shot03-floor-warning-repair','Shot 3 key anchor repair: close cinematic floor-level frame. Harry and Draconia remain dancing outside a glowing circular warning mark, while a separate background guest is frozen inside it. Every visible person wears ordinary formal shoes or formal heels; absolutely no skates or blades. The glowing mark is an abstract magical circle with rune-like curves only, no letters or readable symbols. Vertical 9:16.'),
('shot06-ward-mark-repair','Shot 6 key anchor repair: close cinematic detail of fresh ice-arrow holes in the ballroom floor and a glowing green abstract Malfoy ward sigil burned into the stone. The sigil is decorative rune-like geometry only, with no letters, no words and no readable typography. Harry and Draconia’s polished formal shoes and lower hems appear at the frame edge. Vertical 9:16.'),
('shot08-armor-trolley-repair','Shot 8 key anchor repair: Draconia kicks a polished drinks trolley toward several awakening empty medieval suits of armor while Harry keeps hold of her hand and turns her stumble into a dance step. Draconia’s hair must stay in the accepted braided updo made only of hair with no tiara or crown. Vertical 9:16.'),
]
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:1000],file=sys.stderr)
 r.raise_for_status(); return r.json()
def submit(x):
 name,scene=x; payload={'name':'Harry Draconia E01 v3.9 key anchor repair '+name,'image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':scene+' '+BIBLE},'assets':{'image_file_paths':REFS}}
 job=req('POST','/v1/ai-image-editor',json=payload); return {'name':name,'job':job,'payload':payload,'submitted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
def poll(rec):
 jid=rec['job']['id']
 while True:
  d=req('GET',f'/v1/image-projects/{jid}'); rec['details']=d
  if d.get('status') in {'complete','error','canceled'}: break
  time.sleep(5)
 rec['downloaded_paths']=[]
 if d.get('status')=='complete':
  for i,dl in enumerate(d.get('downloads') or [],1):
   ext='.png' if '.png' in dl['url'].split('?')[0].lower() else '.jpg'; p=OUT/f'{rec["name"]}-{i:02d}{ext}'
   rr=requests.get(dl['url'],timeout=180); rr.raise_for_status(); p.write_bytes(rr.content); rec['downloaded_paths'].append(str(p))
 return rec
state=json.loads(STATE.read_text()) if STATE.exists() else {'jobs':[]}
if not state['jobs']:
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex: state['jobs']=list(ex.map(submit,SHOTS))
 STATE.write_text(json.dumps(state,indent=2))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex: state['jobs']=list(ex.map(poll,state['jobs']))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps([{'name':j['name'],'id':j['job']['id'],'status':j['details'].get('status'),'credits_charged':j['details'].get('credits_charged'),'downloads':j.get('downloaded_paths',[]),'error':j['details'].get('error')} for j in state['jobs']],indent=2))
