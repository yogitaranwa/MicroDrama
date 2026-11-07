#!/usr/bin/env python3
import concurrent.futures,json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
OLD=json.loads(pathlib.Path('/tmp/e01-v3-still-jobs.json').read_text())
R=OLD['refs']
LOCAL=pathlib.Path('/tmp/harry-original-h3-v4-staged')
NAMES=['ref-harry-front-close.png','ref-harry-fullbody.png','ref-draconia-front-close.png','ref-draconia-fullbody.png','ref-two-shot-dialogue.png','ref-two-shot-action.png','ref-yule-ball-location.png']
OUT=pathlib.Path('/tmp/e01-v38-key-anchors'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v38-key-anchor-jobs.json')
BIBLE="""Canonical identities and wardrobe: Harry has messy black hair, round glasses, white dress shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes, and a plain black formal robe with a thin red inner lining. Draconia has platinum blonde hair in a braided updo made only of hair, matching the accepted reference, with at most one small jeweled side pin; she wears the emerald green embroidered sleeveless Yule gown with sheer dark green shoulder drapes and emerald formal shoes. Preserve the accepted reference faces, hair, outfits and body proportions. Cinematic photorealistic only, candlelit Great Hall, cool blue shadows, natural skin and fabric texture, coherent hands. No anime, illustration, cartoon, readable text, extra fingers, distorted faces, tiara, crown, headpiece, long loose side braid, ice skates, skate blades, metal cuffs, bracelets, swords, rapiers, blades or knives."""
SHOTS=[
('shot01-entry-spark','Shot 1 key anchor: Harry enters the candlelit Yule Ball alone. In a tall window reflection, a small black curse spark opens above his head. Wide vertical 9:16 frame, guests soft in background.'),
('shot02-draconia-pull','Shot 2 key anchor: Draconia drops her programme and pulls Harry into the dancers before he can turn toward the first ice arrow. Both are on foot in formal shoes, urgent but controlled. Vertical 9:16.'),
('shot03-floor-rule','Shot 3 key anchor: Draconia keeps Harry dancing while a separate background guest in a pale dress is frozen in place, glowing marks spreading around that guest’s formal shoes. Harry and Draconia are outside the warning circle, both in formal shoes. Vertical 9:16.'),
('shot04-masked-reflection','Shot 4 key anchor: Harry and Draconia dance close while a tall window reflection clearly shows a faceless masked figure copying their first step. The real masked figure is not yet on the floor. Restrained alarm. Vertical 9:16.'),
('shot06-ward-mark','Shot 6 key anchor: close cinematic detail of fresh ice-arrow holes in the ballroom floor, a green Malfoy ward mark burned into the stone, with Harry and Draconia’s formal shoes and lower robes at the frame edge. Vertical 9:16.'),
('shot07-strings-wand','Shot 7 key anchor: flexible silver orchestra strings whip across the floor while Harry raises a clearly slim wooden wand in his right hand and Draconia stays close, ready to move. The strings are ribbons of magic, not weapons. Vertical 9:16.'),
('shot09-trolley-armor-mask','Shot 9 key anchor: Draconia kicks the drinks trolley toward awakening empty armor while Harry turns her stumble into a dance step; in the center background the faceless masked figure copies them. Vertical 9:16.'),
('shot10-floor-grid-red-table','Shot 10 key anchor: the glowing waltz grid tugs at Harry and Draconia’s polished formal shoes as Harry points toward the red banquet table and chooses to break the pattern. Vertical 9:16.'),
]
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:1000],file=sys.stderr)
 r.raise_for_status(); return r.json()
def upload(path):
 item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':path.suffix.lstrip('.').lower(),'type':'image'}]})['items'][0]
 with path.open('rb') as f:
  r=requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=180); r.raise_for_status()
 return item['file_path']
REFS=[]
for n in NAMES:
 if n not in R:
  R[n]={'local':str(LOCAL/n),'file_path':upload(LOCAL/n)}
 REFS.append(R[n]['file_path'])
pathlib.Path('/tmp/e01-v3-still-jobs.json').write_text(json.dumps(OLD,indent=2))
def submit(x):
 name,scene=x; payload={'name':'Harry Draconia E01 v3.8 key anchor '+name,'image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':scene+' '+BIBLE},'assets':{'image_file_paths':REFS}}
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
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: state['jobs']=list(ex.map(submit,SHOTS))
 STATE.write_text(json.dumps(state,indent=2))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: state['jobs']=list(ex.map(poll,state['jobs']))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps([{'name':j['name'],'id':j['job']['id'],'status':j['details'].get('status'),'credits_charged':j['details'].get('credits_charged'),'downloads':j.get('downloaded_paths',[]),'error':j['details'].get('error')} for j in state['jobs']],indent=2))
