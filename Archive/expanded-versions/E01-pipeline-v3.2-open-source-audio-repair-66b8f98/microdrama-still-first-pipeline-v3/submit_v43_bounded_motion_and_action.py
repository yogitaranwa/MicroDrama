#!/usr/bin/env python3
raise RuntimeError("Historical one-off paid submission script retired. No network call made. Use reviewed manifest/ledger execution after separate approval.")
import concurrent.futures,json,os,pathlib,requests,sys,time

if os.environ.get('MH_KEYFILE'):
 KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip()
else:
 KEY=json.loads(pathlib.Path('/tmp/vault-magichour-key.json').read_text())['key'].strip()
BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
ROOT=pathlib.Path('/tmp/e01-v42-reconciled-still-sequence')
OUT=pathlib.Path('/tmp/e01-v43-bounded-motion-action'); OUT.mkdir(exist_ok=True)
STATE=pathlib.Path('/tmp/e01-v43-bounded-motion-action-jobs.json')
BIBLE="Preserve the accepted identities and wardrobe exactly: Harry has messy black hair, round glasses, white dress shirt, plain black long tie, black buttoned waistcoat, dark trousers, polished black formal shoes, and a plain black formal robe with a thin red inner lining. Draconia has platinum blonde hair in a braided updo made only of hair, the emerald embroidered sleeveless Yule gown with sheer dark green shoulder drapes, and emerald formal shoes. Cinematic photorealistic only. No anime, illustration, readable text, tiara, crown, headpiece, long side braid, skates, blades, weapons, extra fingers, distorted faces, or extra people."
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400:
  print(m,p,r.status_code,r.text[:1500],file=sys.stderr)
 r.raise_for_status(); return r.json()
def upload(path):
 item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':path.suffix.lstrip('.').lower(),'type':'image'}]})['items'][0]
 with path.open('rb') as f:
  r=requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=180); r.raise_for_status()
 return item['file_path']
def submit_all(state):
 if 'uploads' not in state:
  files={
   'shot01':ROOT/'shot01-entry-spark.png',
   'shot04':ROOT/'shot04-masked-window-reflection.png',
   'shot07':ROOT/'shot07-strings-wand.png',
   'shot10':ROOT/'shot10-floor-grid-red-table.png',
  }
  state['uploads']={k:upload(v) for k,v in files.items()}; STATE.write_text(json.dumps(state,indent=2))
 if 'still_action' not in state:
  prompt=("Advance this same ballroom moment by one story beat: Draconia flips the red banquet table up as a shield while Harry redirects a charm toward the chandelier chain. "
          "The chandelier begins to crash into the icy floor behind them. Green and silver curse marks are just beginning to burn around their joined hands. "
          "Preserve the same camera geography, accepted faces, poses as much as the action allows, and canonical wardrobe. "+BIBLE)
  payload={'name':'Harry Draconia E01 v4.3 shot11 table chandelier action edit','image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':prompt},'assets':{'image_file_paths':[state['uploads']['shot10']]}}
  state['still_action']={'job':req('POST','/v1/ai-image-editor',json=payload),'payload':prompt,'kind':'image'}; STATE.write_text(json.dumps(state,indent=2))
 if 'video_jobs' not in state:
  specs=[
   ('shot01-entry-motion',state['uploads']['shot01'],'Slow cinematic push-in as Harry walks through the candlelit Yule Ball. Snow and candle flames move subtly. The black curse spark flickers only in the tall window reflection. '+BIBLE),
   ('shot04-reflection-motion',state['uploads']['shot04'],'Harry and Draconia continue a slow controlled waltz turn. Candlelight and window reflections move naturally. The faint blue masked figure remains only inside the window glass and copies their step; it does not enter the physical ballroom. '+BIBLE),
   ('shot07-strings-wand-motion',state['uploads']['shot07'],'Flexible silver orchestra strings whip and tighten across the floor while Harry raises a slim wooden wand and Draconia shifts with him. Fast but readable motion, no weapons. '+BIBLE),
  ]
  def one(spec):
   name,img,prompt=spec
   payload={'name':'Harry Draconia E01 v4.3 bounded motion test '+name,'end_seconds':4,'model':'minimax-h3','resolution':'480p','audio':False,'style':{'prompt':prompt},'assets':{'image_file_path':img}}
   return {'name':name,'job':req('POST','/v1/image-to-video',json=payload),'payload':prompt,'kind':'video'}
   # unreachable
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex: state['video_jobs']=list(ex.map(one,specs))
  STATE.write_text(json.dumps(state,indent=2))
 return state
def poll(rec):
 kind=rec['kind']; jid=rec['job']['id']
 endpoint=f'/v1/image-projects/{jid}' if kind=='image' else f'/v1/video-projects/{jid}'
 while True:
  d=req('GET',endpoint); rec['details']=d
  if d.get('status') in {'complete','error','canceled'}: break
  time.sleep(5)
 rec['downloaded_paths']=[]
 if d.get('status')=='complete':
  for i,dl in enumerate(d.get('downloads') or [],1):
   ext='.mp4' if kind=='video' else ('.png' if '.png' in dl['url'].split('?')[0].lower() else '.jpg')
   p=OUT/f"{rec.get('name','shot11-table-chandelier-action')}-{i:02d}{ext}"
   rr=requests.get(dl['url'],timeout=240); rr.raise_for_status(); p.write_bytes(rr.content); rec['downloaded_paths'].append(str(p))
 return rec
state=json.loads(STATE.read_text()) if STATE.exists() else {}
state=submit_all(state)
records=[state['still_action']]+state['video_jobs']
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: records=list(ex.map(poll,records))
state['still_action']=records[0]; state['video_jobs']=records[1:]; STATE.write_text(json.dumps(state,indent=2))
print(json.dumps({'still_action':{'id':records[0]['job']['id'],'status':records[0]['details'].get('status'),'credits_charged':records[0]['details'].get('credits_charged'),'downloads':records[0].get('downloaded_paths',[]),'error':records[0]['details'].get('error')},'video_jobs':[{'name':r['name'],'id':r['job']['id'],'status':r['details'].get('status'),'credits_charged':r['details'].get('credits_charged'),'downloads':r.get('downloaded_paths',[]),'error':r['details'].get('error')} for r in records[1:]]},indent=2))
