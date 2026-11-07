#!/usr/bin/env python3
import concurrent.futures,json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
ROOT=pathlib.Path('/tmp/e01-v43-timed-reconciled-sequence'); ANCH=pathlib.Path('/tmp/e01-v43-production-end-anchors'); OUT=pathlib.Path('/tmp/e01-v43-targeted-fix-tests'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v43-targeted-fix-tests-jobs.json')
BIBLE="Preserve Harry's messy black hair, round glasses, white dress shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes, and plain black formal robe with only a thin red inner lining. Preserve Draconia's platinum braided updo made only of hair, emerald embroidered sleeveless Yule gown, sheer dark green shoulder drapes, and emerald formal shoes. Cinematic photorealistic only."
SPECS=[
('shot03-frozen-guest','shot03-floor-warning-insert.png','shot03-end-anchor.png','A translucent frozen party guest is completely motionless inside the glowing floor-warning ring. Only the ring pulses. No walking, swaying, turning, or leg movement. '+BIBLE),
('shot05-no-crest','shot05-arrow-volley-timing.png',None,'Ice arrows streak behind Harry and Draconia as they move through one continuous evasive dance step. Harry\'s robe must remain plain and unembellished with no crest, emblem, logo, badge, or school insignia. Do not loop back to the opening pose. '+BIBLE+' No crest, emblem, logo, badge, readable text, tiara, crown, headpiece, skates, blades, weapons, extra fingers, distorted faces, or extra people.'),
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
  state['uploads']={}
  for name,fn,endfn,prompt in SPECS:
   state['uploads'][name]={'start':upload(ROOT/fn)}
   if endfn: state['uploads'][name]['end']=upload(ANCH/endfn)
  STATE.write_text(json.dumps(state,indent=2))
 if 'jobs' not in state:
  def one(spec):
   name,fn,endfn,prompt=spec; assets={'image_file_path':state['uploads'][name]['start']}
   if endfn: assets['end_image_file_path']=state['uploads'][name]['end']
   payload={'name':'Harry Draconia E01 v4.3 targeted fix test '+name,'end_seconds':3,'model':'minimax-h3','resolution':'480p','audio':False,'style':{'prompt':prompt},'assets':assets}
   return {'name':name,'job':req('POST','/v1/image-to-video',json=payload),'payload':prompt}
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: state['jobs']=list(ex.map(one,SPECS))
  STATE.write_text(json.dumps(state,indent=2))
 return state
def poll(rec):
 while True:
  d=req('GET',f"/v1/video-projects/{rec['job']['id']}"); rec['details']=d
  if d.get('status') in {'complete','error','canceled'}: break
  time.sleep(5)
 rec['downloaded_paths']=[]
 if d.get('status')=='complete':
  for i,dl in enumerate(d.get('downloads') or [],1):
   p=OUT/f"{rec['name']}-{i:02d}.mp4"; rr=requests.get(dl['url'],timeout=180); rr.raise_for_status(); p.write_bytes(rr.content); rec['downloaded_paths'].append(str(p))
 return rec
state=json.loads(STATE.read_text()) if STATE.exists() else {}
state=submit(state)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: state['jobs']=list(ex.map(poll,state['jobs']))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps([{'name':r['name'],'id':r['job']['id'],'status':r['details'].get('status'),'credits_charged':r['details'].get('credits_charged'),'downloads':r.get('downloaded_paths',[]),'error':r['details'].get('error')} for r in state['jobs']],indent=2))
