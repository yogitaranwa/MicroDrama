#!/usr/bin/env python3
raise RuntimeError("Historical one-off paid submission script retired. No network call made. Use reviewed manifest/ledger execution after separate approval.")
import concurrent.futures,json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
ROOT=pathlib.Path('/tmp/e01-v43-timed-reconciled-sequence'); OUT=pathlib.Path('/tmp/e01-v43-recovery-motion'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v43-recovery-motion-jobs.json')
BIBLE="Preserve the accepted identities and wardrobe exactly: Harry has messy black hair, round glasses, white dress shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes, and a plain black formal robe with a thin red inner lining. Draconia has platinum blonde hair in a braided updo made only of hair, the emerald embroidered sleeveless Yule gown with sheer dark green shoulder drapes, and emerald formal shoes. Cinematic photorealistic only. No anime, illustration, readable text, tiara, crown, headpiece, long side braid, skates, blades, weapons, extra fingers, distorted faces, or extra people."
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:1500],file=sys.stderr)
 r.raise_for_status(); return r.json()
def upload(path):
 item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':path.suffix.lstrip('.').lower(),'type':'image'}]})['items'][0]
 with path.open('rb') as f:
  r=requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=180); r.raise_for_status()
 return item['file_path']
def submit_all(state):
 if 'uploads' not in state:
  files={k:ROOT/f'{k}.png' for k in ['shot01-entry-spark','shot04-masked-window-reflection','shot07-strings-wand','shot10-floor-grid-red-table','shot11a-table-chandelier-action']}
  state['uploads']={k:upload(v) for k,v in files.items()}; STATE.write_text(json.dumps(state,indent=2))
 if 'video_jobs' not in state:
  u=state['uploads']
  specs=[
   ('shot01-entry-recovery',u['shot01-entry-spark'],u['shot01-entry-spark'],3,'Very subtle slow push-in as Harry walks alone through the candlelit Yule Ball. He remains the only foreground person. The black curse spark flickers only in the window reflection. '+BIBLE),
   ('shot04-reflection-recovery',u['shot04-masked-window-reflection'],u['shot04-masked-window-reflection'],3,'Harry and Draconia continue one slow controlled waltz beat. The faint blue masked figure remains one consistent silhouette inside the window glass and copies their step; it does not multiply and does not enter the ballroom. '+BIBLE),
   ('shot07-strings-wand-recovery',u['shot07-strings-wand'],u['shot07-strings-wand'],3,'Flexible silver orchestra strings tighten and whip subtly while Harry keeps his slim wooden wand raised and Draconia keeps her braided updo and gown exactly. Short controlled action, no camera spin. '+BIBLE),
   ('shot11-action-transition',u['shot10-floor-grid-red-table'],u['shot11a-table-chandelier-action'],4,'Advance from the red-table setup into the action anchor: Draconia pulls the red banquet table up as a shield while the chandelier drops toward the ice and the green and silver marks ignite around their joined hands. Preserve geography and wardrobe. '+BIBLE),
  ]
  def one(spec):
   name,start,end,secs,prompt=spec
   payload={'name':'Harry Draconia E01 v4.3 recovery motion '+name,'end_seconds':secs,'model':'minimax-h3','resolution':'480p','audio':False,'style':{'prompt':prompt},'assets':{'image_file_path':start,'end_image_file_path':end}}
   return {'name':name,'job':req('POST','/v1/image-to-video',json=payload),'payload':prompt}
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: state['video_jobs']=list(ex.map(one,specs))
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
state=submit_all(state)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: state['video_jobs']=list(ex.map(poll,state['video_jobs']))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps([{'name':r['name'],'id':r['job']['id'],'status':r['details'].get('status'),'credits_charged':r['details'].get('credits_charged'),'downloads':r.get('downloaded_paths',[]),'error':r['details'].get('error')} for r in state['video_jobs']],indent=2))
