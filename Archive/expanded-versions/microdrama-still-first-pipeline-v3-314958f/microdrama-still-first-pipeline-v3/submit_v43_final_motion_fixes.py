#!/usr/bin/env python3
import concurrent.futures,json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
ROOT=pathlib.Path('/tmp/e01-v43-timed-reconciled-sequence'); OUT=pathlib.Path('/tmp/e01-v43-final-motion-fixes'); OUT.mkdir(exist_ok=True); STATE=pathlib.Path('/tmp/e01-v43-final-motion-fixes-jobs.json')
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
def submit(state):
 if 'uploads' not in state:
  state['uploads']={k:upload(ROOT/f'{k}.png') for k in ['shot01-entry-spark','shot01-entry-push-end','shot10-floor-grid-red-table','shot11a-table-chandelier-action']}; STATE.write_text(json.dumps(state,indent=2))
 if 'jobs' not in state:
  u=state['uploads']
  specs=[
   {'name':'shot01-monotonic-push-7s','seconds':7,'start':u['shot01-entry-spark'],'end':u['shot01-entry-push-end'],'prompt':'One monotonic slow forward push-in as Harry walks alone through the candlelit Yule Ball. Do not reverse direction or loop the walk. He remains the only foreground person. The black curse spark flickers only in the window reflection. '+BIBLE},
   {'name':'shot11-action-transition-shoes-fixed','seconds':4,'start':u['shot10-floor-grid-red-table'],'end':u['shot11a-table-chandelier-action'],'prompt':'Advance from the red-table setup into the action anchor: Draconia pulls the red banquet table up as a shield while the chandelier drops toward the ice and the green and silver marks ignite around their joined hands. Preserve geography and wardrobe, including Harry\'s sleek polished black formal shoes. '+BIBLE},
  ]
  def one(s):
   payload={'name':'Harry Draconia E01 v4.3 final motion fix '+s['name'],'end_seconds':s['seconds'],'model':'minimax-h3','resolution':'480p','audio':False,'style':{'prompt':s['prompt']},'assets':{'image_file_path':s['start'],'end_image_file_path':s['end']}}
   return {'name':s['name'],'job':req('POST','/v1/image-to-video',json=payload),'payload':s['prompt']}
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: state['jobs']=list(ex.map(one,specs))
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
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: state['jobs']=list(ex.map(poll,state['jobs']))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps([{'name':r['name'],'id':r['job']['id'],'status':r['details'].get('status'),'credits_charged':r['details'].get('credits_charged'),'downloads':r.get('downloaded_paths',[]),'error':r['details'].get('error')} for r in state['jobs']],indent=2))
