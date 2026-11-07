#!/usr/bin/env python3
import concurrent.futures,json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
ROOT=pathlib.Path('/tmp/e01-v43-timed-reconciled-sequence'); OUT=pathlib.Path('/tmp/e01-v43-remaining-motion-tests'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v43-remaining-motion-tests-jobs.json')
BIBLE="Preserve the accepted identities and wardrobe exactly: Harry has messy black hair, round glasses, white dress shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes, and a plain black formal robe with a thin red inner lining. Draconia has platinum blonde hair in a braided updo made only of hair, the emerald embroidered sleeveless Yule gown with sheer dark green shoulder drapes, and emerald formal shoes. Cinematic photorealistic only. No anime, illustration, readable text, tiara, crown, headpiece, long side braid, skates, blades, weapons, extra fingers, distorted faces, or extra people."
SPECS=[
('shot02-draconia-pull','shot02-draconia-pull','Draconia keeps hold of Harry and pulls him one urgent step deeper into the dancers. Continue the action; do not reset their positions. '+BIBLE),
('shot03-floor-warning','shot03-floor-warning-insert','The glowing floor-warning ring pulses around the frozen guest while Harry and Draconia keep moving at the edge. Subtle motion only. '+BIBLE),
('shot05-arrow-volley','shot05-arrow-volley-timing','Ice arrows strike behind Harry and Draconia after the orchestra beat as they shift one step early. Continue the dancers; do not reset their positions. '+BIBLE),
('shot06-ward-mark','shot06-ward-mark','The green ward mark pulses in the ice-arrow holes while Harry and Draconia react. Subtle camera and fabric motion only. '+BIBLE),
('shot08-armor-trolley','shot08-armor-trolley-insert','Empty armor shifts in the background while the drinks trolley rolls slightly and the dancers continue. Keep this as a lower-body action insert with no white-shirt torso. '+BIBLE),
('shot09-trolley-mask','shot09-trolley-mask','The drinks trolley moves toward the armor as Harry turns Draconia\'s stumble into a dance step and the masked figure mirrors them. '+BIBLE),
('shot10-floor-grid','shot10-floor-grid-red-table','The glowing floor grid tugs their formal shoes toward the next step while Harry points toward the red table. '+BIBLE),
('shot11b-marks','shot11b-masked-marks','Green and silver marks burn brighter around Harry and Draconia\'s joined hands while the masked figure watches. Subtle push only. '+BIBLE),
('shot12a-marks-close','shot12a-harry-marks-close','Close continuation of the same instant: the green and silver marks pulse around the joined hands. Do not reset time or change expression. '+BIBLE),
('shot12b-draconia-reaction','shot12b-draconia-reaction','Draconia holds Harry\'s gaze, afraid but honest, as the ballroom light subtly shifts. Keep the braided updo and gown exactly. '+BIBLE),
]
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:1500],file=sys.stderr)
 r.raise_for_status(); return r.json()
def upload(path):
 item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':path.suffix.lstrip('.').lower(),'type':'image'}]})['items'][0]
 with path.open('rb') as f:
  r=requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=180); r.raise_for_status()
 return item['file_path']
def submit(state):
 if 'uploads' not in state:
  state['uploads']={name:upload(ROOT/f'{filename}.png') for name,filename,_ in SPECS}; STATE.write_text(json.dumps(state,indent=2))
 if 'jobs' not in state:
  def one(spec):
   name,fn,prompt=spec; img=state['uploads'][name]
   payload={'name':'Harry Draconia E01 v4.3 remaining motion test '+name,'end_seconds':3,'model':'minimax-h3','resolution':'480p','audio':False,'style':{'prompt':prompt},'assets':{'image_file_path':img,'end_image_file_path':img}}
   return {'name':name,'job':req('POST','/v1/image-to-video',json=payload),'payload':prompt}
  with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex: state['jobs']=list(ex.map(one,SPECS))
  STATE.write_text(json.dumps(state,indent=2))
 return state
def poll(rec):
 jid=rec['job']['id']
 while True:
  d=req('GET',f'/v1/video-projects/{jid}'); rec['details']=d
  if d.get('status') in {'complete','error','canceled'}: break
  time.sleep(5)
 rec['downloaded_paths']=[]
 if d.get('status')=='complete':
  for i,dl in enumerate(d.get('downloads') or [],1):
   p=OUT/f"{rec['name']}-{i:02d}.mp4"; rr=requests.get(dl['url'],timeout=240); rr.raise_for_status(); p.write_bytes(rr.content); rec['downloaded_paths'].append(str(p))
 return rec
state=json.loads(STATE.read_text()) if STATE.exists() else {}
state=submit(state)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex: state['jobs']=list(ex.map(poll,state['jobs']))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps([{'name':r['name'],'id':r['job']['id'],'status':r['details'].get('status'),'credits_charged':r['details'].get('credits_charged'),'downloads':r.get('downloaded_paths',[]),'error':r['details'].get('error')} for r in state['jobs']],indent=2))
