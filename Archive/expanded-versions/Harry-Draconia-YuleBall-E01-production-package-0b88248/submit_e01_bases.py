#!/usr/bin/env python3
import json, pathlib, requests, sys, time
key_path = sys.argv[1]
KEY = pathlib.Path(key_path).read_text().strip()
BASE = 'https://api.magichour.ai'
H = {'Authorization': 'Bearer '+KEY, 'Content-Type': 'application/json'}
ROOT = pathlib.Path('/tmp/harry-original-h3-v4-staged')
COMMON = ('Vertical cinematic photorealistic enchanted Yule Ball in the Great Hall, candlelit, snow beneath the enchanted ceiling, realistic skin, hair, fabric and wand action, coherent physics, dynamic but controlled camera, no anime, no illustration, no readable text, no cutaway, no duplicate foreground people.')
SHOTS = [
 (1,5,'two-shot-dialogue','Harry enters the crowded Yule Ball alone in plain formal robes, watching window reflections while Draconia is visible only in reflections watching him back. Slow restrained entrance, floating candles, snow suspended in the enchanted ceiling.'),
 (3,6,'two-shot-action','Ice arrows strike the floor where Harry stood as Draconia grabs his hand and pulls him into the dance. Fast rescue, dancers recoil, camera tracks the pull into the waltz, both faces recognizable from the reference.'),
 (4,5,'harry-speaking-profile','Close on Harry letting Draconia lead while he scans the floor, ceiling and wand positions. Controlled expression, natural visible mouth movement in the opening second as if beginning a clipped remark, subtle camera push-in.'),
 (5,6,'draconia-speaking-profile','Close on Draconia spinning Harry out of an ice-arrow impact line, platinum hair whipping across her face, urgent defiant expression, natural visible mouth movement in the opening second, candlelit motion.'),
 (6,5,'harry-speaking-profile','Close on Harry noticing the arrows landing on the orchestra offbeat. He changes their dance steps by half a beat as the next arrows miss by inches. Analytical expression, natural visible mouth movement in the opening second.'),
 (7,4,'draconia-speaking-profile','Close on Draconia grinning despite the chaos, thrilled that Harry saw the pattern. Bright urgent expression, natural visible mouth movement in the opening second, quick camera push.'),
 (8,7,'two-shot-action','Orchestra instruments split apart and silver strings whip across the Great Hall. Harry cuts two strings with a precise slashing charm while a third wraps his wrist. Fast action, clear faces, no gore.'),
 (9,5,'two-shot-action','Draconia snaps the silver string with her heel, pulls Harry upright, and keeps dancing because the floor punishes stillness. Athletic rescue, controlled camera, clear identities.'),
 (10,7,'two-shot-action','Six empty suits of armor march from the shadows. Draconia kicks a polished drinks trolley into the first armor, laughs and ducks as it swings. Dynamic action comedy, clear identities.'),
 (11,5,'two-shot-action','Harry catches Draconia before she falls and turns the rescue into the next dance step while a masked figure forms at the center of the floor. Elegant motion, clear identities.'),
 (12,6,'two-shot-action','The masked figure copies Harry and Draconia\'s movements. Each copied step seals another exit with ice spreading over the doors. Ominous mirrored motion, clear faces.'),
 (13,6,'harry-speaking-profile','Close on Harry seeing the waltz grid in the floor and deliberately breaking form. Tactical realization, natural visible mouth movement in the opening second, subtle push-in.'),
 (14,6,'two-shot-action','Harry and Draconia improvise off the waltz grid. Draconia spins under Harry\'s shield charm; the redirected spell hits the chandelier chain, making it groan above the students. Fast but readable action.'),
 (15,5,'harry-speaking-profile','Close on Harry pointing toward a red velvet banquet table, giving a tactical instruction in clipped beats. Controlled alarm, natural visible mouth movement in the opening second.'),
 (16,5,'two-shot-dialogue','The chandelier crashes into the frozen floor and ice swallows it. Green and silver ribbons burn onto Harry and Draconia\'s hands as they look at the marks. Dramatic close two-shot, clear identities.'),
 (17,5,'harry-speaking-profile','Close on Harry as the doors seal and the Forbidden Forest answers outside the windows with a bow-shaped green light. He turns toward Draconia, controlled but alarmed, natural visible mouth movement in the opening second.'),
 (18,3,'draconia-front-close','Extreme close on Draconia, scared for the first time but refusing to step back. Green and silver light catches her face, natural visible mouth movement in the opening second, restrained final-beat camera hold.'),
]

def req(method,path,**kw):
    r=requests.request(method,BASE+path,headers=H,timeout=180,**kw)
    if r.status_code>=400:
        print(method,path,r.status_code,r.text[:1200],file=sys.stderr)
    r.raise_for_status(); return r.json()

def upload(path):
    ext=path.suffix.lstrip('.').lower()
    item=req('POST','/v1/files/upload-urls',json={'items':[{'extension':ext,'type':'image'}]})['items'][0]
    with open(path,'rb') as f:
        r=requests.put(item['upload_url'],data=f,headers={'Content-Type':'application/octet-stream'},timeout=180)
        r.raise_for_status()
    return item['file_path']

state_path=pathlib.Path('/tmp/e01-base-jobs.json')
state=json.loads(state_path.read_text()) if state_path.exists() else {'refs':{},'jobs':[]}
refnames=sorted({ref for _,_,ref,_ in SHOTS})
for ref in refnames:
    if ref not in state['refs']:
        local=ROOT/f'ref-{ref}.png'
        print('upload ref',ref)
        state['refs'][ref]={'local':str(local),'file_path':upload(local)}
        state_path.write_text(json.dumps(state,indent=2))
existing={j['shot'] for j in state['jobs']}
for shot,dur,ref,action in SHOTS:
    if shot in existing: continue
    payload={'name':f'Harry Draconia E01 shot {shot:02d} 720p base','end_seconds':dur,'model':'minimax-h3','resolution':'720p','audio':False,'style':{'prompt':COMMON+' '+action},'assets':{'image_file_path':state['refs'][ref]['file_path']}}
    print('submit shot',shot,dur)
    job=req('POST','/v1/image-to-video',json=payload)
    state['jobs'].append({'shot':shot,'duration':dur,'ref':ref,'action':action,'payload':payload,'job':job,'submitted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')})
    state_path.write_text(json.dumps(state,indent=2))
print(json.dumps({'submitted':len(state['jobs']),'credits':sum(j['job'].get('credits_charged',0) for j in state['jobs'])},indent=2))
