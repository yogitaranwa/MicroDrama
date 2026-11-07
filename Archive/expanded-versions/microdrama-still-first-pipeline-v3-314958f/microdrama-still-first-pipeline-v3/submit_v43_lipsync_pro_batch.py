#!/usr/bin/env python3
import concurrent.futures,json,pathlib,requests,sys,time
KEY=pathlib.Path('/home/sandbox/.vault/magic-hour-api-key-70da61/password').read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
OUT=pathlib.Path('/tmp/e01-v43-lipsync-pro'); OUT.mkdir(exist_ok=True); STATE=OUT/'pro-batch-jobs.json'
SPECS=[
 {'name':'shot02-line01','video':'/tmp/e01-v43-remaining-production-720p/shot02-draconia-pull-01.mp4','audio':str(OUT/'shot02-line01.wav'),'seconds':6.583},
 {'name':'shot04-line04','video':'/tmp/e01-v43-production-cleared/shot04-reflection-production-720p-01.mp4','audio':str(OUT/'shot04-line04.wav'),'seconds':8.0},
 {'name':'shot05-lines05-06','video':'/tmp/e01-v43-local-motion-fixes/shot05-arrow-volley-local-6s.mp4','audio':str(OUT/'shot05-lines05-06.wav'),'seconds':6.042},
 {'name':'shot06-lines07-08','video':'/tmp/e01-v43-remaining-production-720p/shot06-ward-mark-01.mp4','audio':str(OUT/'shot06-lines07-08.wav'),'seconds':9.0},
 {'name':'shot07-line09','video':'/tmp/e01-v43-remaining-production-720p/shot07-strings-wand-01.mp4','audio':str(OUT/'shot07-line09.wav'),'seconds':6.583},
 {'name':'shot10-lines11-12','video':'/tmp/e01-v43-remaining-production-720p/shot10-floor-grid-01.mp4','audio':str(OUT/'shot10-lines11-12.wav'),'seconds':9.0},
 {'name':'shot12a-line14','video':'/tmp/e01-v43-remaining-production-720p/shot12a-marks-close-01.mp4','audio':str(OUT/'shot12a-line14.wav'),'seconds':4.458},
]
def req(m,p,**kw):
 r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(m,p,r.status_code,r.text[:2000],file=sys.stderr)
 r.raise_for_status(); return r.json()
def upload(path,typ):
 path=pathlib.Path(path); item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':path.suffix.lstrip('.').lower(),'type':typ}]})['items'][0]
 with path.open('rb') as f:
  r=requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=300); r.raise_for_status()
 return item['file_path']
def save(): STATE.write_text(json.dumps(state,indent=2))
state=json.loads(STATE.read_text()) if STATE.exists() else {'items':{}}
for s in SPECS:
 rec=state['items'].setdefault(s['name'],{})
 rec.update({k:s[k] for k in ('video','audio','seconds')})
 if 'uploads' not in rec:
  rec['uploads']={'video':upload(s['video'],'video'),'audio':upload(s['audio'],'audio')}; save()
 if 'job' not in rec:
  payload={'name':'Harry Draconia E01 v4.3 '+s['name']+' Pro lip sync','start_seconds':0,'end_seconds':s['seconds'],'max_fps_limit':24,'assets':{'audio_file_path':rec['uploads']['audio'],'video_source':'file','video_file_path':rec['uploads']['video']},'style':{'generation_mode':'pro'}}
  rec['payload']=payload; rec['job']=req('POST','/v1/lip-sync',json=payload); save()
print(json.dumps({'submitted':[{ 'name':s['name'], 'job':state['items'][s['name']].get('job')} for s in SPECS]},indent=2))
