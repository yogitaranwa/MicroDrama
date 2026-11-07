#!/usr/bin/env python3
import json,os,pathlib,requests,sys,time
KEY=pathlib.Path('/home/sandbox/.vault/magic-hour-api-key-70da61/password').read_text().strip()
BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
OUT=pathlib.Path('/tmp/e01-v43-lipsync-pro'); OUT.mkdir(exist_ok=True)
STATE=OUT/'shot12b-pro-test-job.json'
VIDEO=pathlib.Path('/tmp/e01-v43-remaining-production-720p/shot12b-draconia-reaction-01.mp4')
AUDIO=OUT/'shot12b-line15.wav'
def req(m,p,**kw):
    r=requests.request(m,BASE+p,headers=H,timeout=180,**kw)
    if r.status_code>=400:
        print(m,p,r.status_code,r.text[:2000],file=sys.stderr)
    r.raise_for_status(); return r.json()
def upload(path,typ):
    item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':path.suffix.lstrip('.').lower(),'type':typ}]})['items'][0]
    with path.open('rb') as f:
        r=requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=300); r.raise_for_status()
    return item['file_path']
state=json.loads(STATE.read_text()) if STATE.exists() else {}
if 'uploads' not in state:
    state['uploads']={'video':upload(VIDEO,'video'),'audio':upload(AUDIO,'audio')}
    STATE.write_text(json.dumps(state,indent=2))
if 'job' not in state:
    payload={'name':'Harry Draconia E01 v4.3 shot12b line15 Pro lip sync validation','start_seconds':0,'end_seconds':5.167,'max_fps_limit':24,'assets':{'audio_file_path':state['uploads']['audio'],'video_source':'file','video_file_path':state['uploads']['video']},'style':{'generation_mode':'pro'}}
    state['payload']=payload; state['job']=req('POST','/v1/lip-sync',json=payload); STATE.write_text(json.dumps(state,indent=2))
jid=state['job']['id']
while True:
    d=req('GET',f'/v1/video-projects/{jid}'); state['details']=d
    if d.get('status') in {'complete','error','canceled'}: break
    time.sleep(5)
state['downloaded_paths']=[]
if state['details'].get('status')=='complete':
    for i,dl in enumerate(state['details'].get('downloads') or [],1):
        p=OUT/f'shot12b-line15-pro-{i:02d}.mp4'; rr=requests.get(dl['url'],timeout=300); rr.raise_for_status(); p.write_bytes(rr.content); state['downloaded_paths'].append(str(p))
STATE.write_text(json.dumps(state,indent=2))
print(json.dumps({'id':jid,'status':state['details'].get('status'),'credits_charged':state['details'].get('credits_charged'),'downloads':state.get('downloaded_paths',[]),'error':state['details'].get('error')},indent=2))
