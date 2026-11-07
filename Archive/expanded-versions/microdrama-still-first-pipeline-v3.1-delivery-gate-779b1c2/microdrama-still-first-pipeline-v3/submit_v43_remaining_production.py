#!/usr/bin/env python3
import concurrent.futures,json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
ROOT=pathlib.Path('/tmp/e01-v43-timed-reconciled-sequence'); ANCH=pathlib.Path('/tmp/e01-v43-production-end-anchors'); OUT=pathlib.Path('/tmp/e01-v43-remaining-production-720p'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v43-remaining-production-720p-jobs.json')
BIBLE="Preserve the accepted identities and wardrobe exactly: Harry has messy black hair, round glasses, white dress shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes, and a plain black formal robe with a thin red inner lining. Draconia has platinum blonde hair in a braided updo made only of hair, the emerald embroidered sleeveless Yule gown with sheer dark green shoulder drapes, and emerald formal shoes. Cinematic photorealistic only. No anime, illustration, readable text, tiara, crown, headpiece, long side braid, skates, blades, weapons, extra fingers, distorted faces, or extra people."
# end=None means start-only action to avoid the loop seen in same-start/end 480p tests.
SPECS=[
('shot02-draconia-pull','shot02-draconia-pull.png',None,6,'Draconia keeps hold of Harry and pulls him deeper into the dancers in one continuous urgent move. Do not loop back to the opening pose. '+BIBLE),
('shot03-floor-warning','shot03-floor-warning-insert.png','shot03-end-anchor.png',9,'A translucent frozen party guest remains stopped inside the glowing floor-warning ring while the ring pulses. The dark-robed edge figure is only passing foreground. '+BIBLE),
('shot05-arrow-volley','shot05-arrow-volley-timing.png',None,6,'Ice arrows streak behind Harry and Draconia after the orchestra beat as they keep moving forward through one continuous evasive dance step. Do not loop back to the opening pose. '+BIBLE),
('shot06-ward-mark','shot06-ward-mark.png','shot06-end-anchor.png',9,'The green Malfoy ward mark pulses in the ice-arrow holes while Harry and Draconia react with restrained fear. '+BIBLE),
('shot07-strings-wand','shot07-strings-wand.png','shot07-end-anchor.png',6,'Silver orchestra strings and intentional magical music-staff symbols pulse around Harry\'s slim wooden wand and Draconia. Keep hair and wardrobe stable. '+BIBLE),
('shot08-armor-trolley','shot08-armor-trolley-insert.png','shot08-end-anchor.png',8,'Lower-body insert: the drinks trolley rolls slightly, armor shifts behind it, and the dancers\' formal shoes continue. Do not reveal a white-shirt torso. '+BIBLE),
('shot09-trolley-mask','shot09-trolley-mask.png',None,7,'The drinks trolley moves toward the armor as Harry turns Draconia\'s stumble into one continuous dance step while the masked figure mirrors them. Do not loop back to the opening pose. '+BIBLE),
('shot10-floor-grid','shot10-floor-grid-red-table.png','shot10-end-anchor.png',9,'The glowing floor grid tugs their formal shoes toward the next step while Harry points toward the red banquet table. '+BIBLE),
('shot11b-marks','shot11b-masked-marks.png','shot11b-end-anchor.png',4,'Green and silver marks burn brighter around Harry and Draconia\'s joined hands while the masked figure watches. Subtle push only. '+BIBLE),
('shot12a-marks-close','shot12a-harry-marks-close.png','shot12a-end-anchor.png',4,'Close continuation of the same instant: the green and silver marks pulse around the joined hands. Do not reset time or expression. '+BIBLE),
('shot12b-draconia-reaction','shot12b-draconia-reaction.png','shot12b-end-anchor.png',5,'Draconia holds Harry\'s gaze, afraid but honest, as the ballroom light subtly shifts. Keep the braided updo and gown exactly. '+BIBLE),
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
  uploads={}
  for name,fn,endfn,secs,prompt in SPECS:
   uploads[name]={'start':upload(ROOT/fn)}
   if endfn: uploads[name]['end']=upload(ANCH/endfn)
  state['uploads']=uploads; STATE.write_text(json.dumps(state,indent=2))
 if 'jobs' not in state:
  def one(spec):
   name,fn,endfn,secs,prompt=spec; assets={'image_file_path':state['uploads'][name]['start']}
   if endfn: assets['end_image_file_path']=state['uploads'][name]['end']
   payload={'name':'Harry Draconia E01 v4.3 remaining production '+name,'end_seconds':secs,'model':'minimax-h3','resolution':'720p','audio':False,'style':{'prompt':prompt},'assets':assets}
   return {'name':name,'seconds':secs,'job':req('POST','/v1/image-to-video',json=payload),'payload':prompt,'end_anchor':bool(endfn)}
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
print(json.dumps([{'name':r['name'],'id':r['job']['id'],'seconds':r['seconds'],'status':r['details'].get('status'),'credits_charged':r['details'].get('credits_charged'),'downloads':r.get('downloaded_paths',[]),'error':r['details'].get('error')} for r in state['jobs']],indent=2))
