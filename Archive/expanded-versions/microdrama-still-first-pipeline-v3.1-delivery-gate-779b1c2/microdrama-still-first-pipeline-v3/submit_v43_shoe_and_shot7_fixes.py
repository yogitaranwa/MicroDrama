#!/usr/bin/env python3
import concurrent.futures,json,os,pathlib,requests,sys,time
KEY=pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
STATE=pathlib.Path('/tmp/e01-v43-shoe-shot7-fix-jobs.json')
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
  state['uploads']={'shot11':upload(pathlib.Path('/tmp/e01-v43-shot11-chandelier-fall-edit/shot11-chandelier-midfall-01.png')),'shot07':upload(pathlib.Path('/tmp/e01-v43-timed-reconciled-sequence/shot07-strings-wand.png'))}
  STATE.write_text(json.dumps(state,indent=2))
 if 'jobs' not in state:
  prompt="""Edit only Harry's footwear. Replace the silver blade/runner-like shapes under his shoes with ordinary polished black formal dress shoes with natural thin leather soles, appropriate for a ballroom. Preserve the same shoe positions, black trousers, Harry's canonical black robe with thin red inner lining, accepted face, glasses, hair, hands, green and silver marks, Draconia, emerald gown and formal shoes, flipped red table shield, mid-fall chandelier, snapped chain, crystals, floor grid, candles, background, lighting and composition exactly. Cinematic photorealistic only. No skates, blades, runners, weapons, text, tiara, crown, long braid, or extra people."""
  p1={'name':'Harry Draconia E01 v4.3 shot11 formal shoe fix','image_count':1,'model':'seedream-v4.5','aspect_ratio':'9:16','resolution':'1k','style':{'prompt':prompt},'assets':{'image_file_paths':[state['uploads']['shot11']]}}
  j1={'name':'shot11-formal-shoe-fix','kind':'image','job':req('POST','/v1/ai-image-editor',json=p1),'payload':prompt}
  prompt2="""Flexible silver orchestra strings tighten subtly while Harry keeps his slim wooden wand raised and Draconia keeps her braided updo and emerald gown exactly. Keep the same camera composition and preserve the start/end anchors. Do not create musical symbols, treble clefs, notes, signs, props, readable text, weapons, extra people, or loose hair. Cinematic photorealistic ballroom magic only."""
  p2={'name':'Harry Draconia E01 v4.3 shot07 no-symbol recovery','end_seconds':2,'model':'minimax-h3','resolution':'480p','audio':False,'style':{'prompt':prompt2},'assets':{'image_file_path':state['uploads']['shot07'],'end_image_file_path':state['uploads']['shot07']}}
  j2={'name':'shot07-no-symbol-recovery','kind':'video','job':req('POST','/v1/image-to-video',json=p2),'payload':prompt2}
  state['jobs']=[j1,j2]; STATE.write_text(json.dumps(state,indent=2))
 return state
def poll(rec):
 jid=rec['job']['id']; endpoint=f"/v1/image-projects/{jid}" if rec['kind']=='image' else f"/v1/video-projects/{jid}"
 while True:
  d=req('GET',endpoint); rec['details']=d
  if d.get('status') in {'complete','error','canceled'}: break
  time.sleep(5)
 rec['downloaded_paths']=[]
 if d.get('status')=='complete':
  out=pathlib.Path('/tmp/e01-v43-shoe-shot7-fixes'); out.mkdir(exist_ok=True)
  for i,dl in enumerate(d.get('downloads') or [],1):
   ext='.mp4' if rec['kind']=='video' else ('.png' if '.png' in dl['url'].split('?')[0].lower() else '.jpg')
   p=out/f"{rec['name']}-{i:02d}{ext}"; rr=requests.get(dl['url'],timeout=240); rr.raise_for_status(); p.write_bytes(rr.content); rec['downloaded_paths'].append(str(p))
 return rec
state=json.loads(STATE.read_text()) if STATE.exists() else {}
state=submit(state)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: state['jobs']=list(ex.map(poll,state['jobs']))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps([{'name':r['name'],'id':r['job']['id'],'status':r['details'].get('status'),'credits_charged':r['details'].get('credits_charged'),'downloads':r.get('downloaded_paths',[]),'error':r['details'].get('error')} for r in state['jobs']],indent=2))
