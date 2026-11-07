#!/usr/bin/env python3
raise RuntimeError("Historical one-off paid submission script retired. No network call made. Use reviewed manifest/ledger execution after separate approval.")
import json, pathlib, requests, sys, time

import os
KEY = pathlib.Path(os.environ['MH_KEYFILE']).read_text().strip()
BASE = 'https://api.magichour.ai'
H = {'Authorization': 'Bearer '+KEY, 'Content-Type': 'application/json'}
ROOT = pathlib.Path('/tmp/harry-original-h3-v4-staged')
OUT = pathlib.Path('/tmp/e01-v3-still-batch-01')
OUT.mkdir(parents=True, exist_ok=True)
STATE_PATH = pathlib.Path('/tmp/e01-v3-still-jobs.json')

REFS = [
    ROOT/'ref-harry-front-close.png',
    ROOT/'ref-harry-fullbody.png',
    ROOT/'ref-draconia-front-close.png',
    ROOT/'ref-draconia-fullbody.png',
    ROOT/'ref-yule-ball-location.png',
]

PROMPT = """Vertical cinematic photorealistic Yule Ball continuity still, candlelit Great Hall with cool blue shadows. Harry Potter and Draconia Malfoy must preserve the exact faces, hairstyles, formal outfits and body proportions from the supplied references. Shot 7 action peak: silver orchestra strings tear free and whip toward them while Harry raises a slim wooden wand in his right hand; Draconia stays close, urgent and ready to move. Restrained realistic expressions, shallow depth of field, natural skin and fabric texture, coherent hands. The wand is clearly a slim wooden wand, not a sword, rapier, blade, knife or metal object. The silver strings are flexible magical ribbons, not rigid rods or weapons. No metal cuffs, no anime, no illustration, no readable text, no extra fingers, no distorted face."""

def req(method, path, **kw):
    r = requests.request(method, BASE+path, headers=H, timeout=180, **kw)
    if r.status_code >= 400:
        print(method, path, r.status_code, r.text[:1000], file=sys.stderr)
    r.raise_for_status()
    return r.json()

def upload(path):
    ext = path.suffix.lstrip('.').lower()
    item = req('POST', '/v1/files/upload-urls', json={'items':[{'extension': ext, 'type': 'image'}]})['items'][0]
    with path.open('rb') as f:
        r = requests.put(item['upload_url'], data=f, headers={'Content-Type':'application/octet-stream'}, timeout=180)
        r.raise_for_status()
    return item['file_path']

state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {'refs': {}, 'jobs': []}
for p in REFS:
    if p.name not in state['refs']:
        state['refs'][p.name] = {'local': str(p), 'file_path': upload(p)}
        STATE_PATH.write_text(json.dumps(state, indent=2))

payload = {
    'name': 'Harry Draconia E01 v3 still batch 01 shot07 action peak',
    'image_count': 1,
    'model': 'seedream-v4.5',
    'aspect_ratio': '9:16',
    'resolution': '1k',
    'style': {'prompt': PROMPT},
    'assets': {'image_file_paths': [state['refs'][p.name]['file_path'] for p in REFS]},
}

if not state['jobs']:
    job = req('POST', '/v1/ai-image-editor', json=payload)
    state['jobs'].append({'job': job, 'payload': payload, 'submitted_at': time.strftime('%Y-%m-%dT%H:%M:%S%z')})
    STATE_PATH.write_text(json.dumps(state, indent=2))

job_id = state['jobs'][-1]['job']['id']
while True:
    details = req('GET', f'/v1/image-projects/{job_id}')
    state['jobs'][-1]['details'] = details
    STATE_PATH.write_text(json.dumps(state, indent=2))
    if details.get('status') in {'complete','error','canceled'}:
        break
    time.sleep(5)

if details.get('status') != 'complete':
    print(json.dumps({'id': job_id, 'status': details.get('status'), 'credits_charged': details.get('credits_charged'), 'error': details.get('error')}, indent=2))
    raise SystemExit(2)

paths=[]
for i,d in enumerate(details.get('downloads') or [],1):
    url=d['url']
    ext='.png' if '.png' in url.split('?')[0].lower() else '.jpg'
    p=OUT/f'shot07-action-peak-candidate-{i:02d}{ext}'
    r=requests.get(url,timeout=180); r.raise_for_status(); p.write_bytes(r.content)
    paths.append(str(p))
state['jobs'][-1]['downloaded_paths']=paths
STATE_PATH.write_text(json.dumps(state, indent=2))
print(json.dumps({'id': job_id, 'status': details.get('status'), 'image_count': details.get('image_count'), 'credits_charged': details.get('credits_charged'), 'downloads': paths}, indent=2))
