#!/usr/bin/env python3
import json,pathlib,requests,sys,time
KEY=pathlib.Path(sys.argv[1]).read_text().strip(); BASE='https://api.magichour.ai'; H={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'}
state_path=pathlib.Path('/tmp/e01-base-jobs.json'); state=json.loads(state_path.read_text())
COMMON='Vertical cinematic photorealistic enchanted Yule Ball in the Great Hall, candlelit, realistic skin and fabric, coherent physics, controlled cinematic motion, no anime, no illustration, no readable text, no duplicate foreground people.'
REROLLS=[
 (12,6,'two-shot-dialogue','Harry and Draconia in the SAME formal outfits, Harry in black Gryffindor dress robes and Draconia in the SAME emerald green gown. A masked black-robed figure copies their dance steps in the background while translucent blue ice spreads over the Great Hall doors. Ominous mirrored motion, clear faces, DO NOT change Draconia gown color.'),
 (13,6,'harry-front-close','Close on Harry looking down through the dancers at a faint glowing geometric waltz grid in the marble floor. He realizes the attacker is using the grid and deliberately steps off the marked line. Serious controlled realization, natural mouth movement in the opening second, no smiling, no generic dancing cutaway.'),
]
def req(method,path,**kw):
 r=requests.request(method,BASE+path,headers=H,timeout=180,**kw)
 if r.status_code>=400: print(method,path,r.status_code,r.text[:1000],file=sys.stderr)
 r.raise_for_status(); return r.json()
for shot,dur,ref,action in REROLLS:
 payload={'name':f'Harry Draconia E01 shot {shot:02d} 720p base reroll 1','end_seconds':dur,'model':'minimax-h3','resolution':'720p','audio':False,'style':{'prompt':COMMON+' '+action},'assets':{'image_file_path':state['refs'][ref]['file_path']}}
 job=req('POST','/v1/image-to-video',json=payload)
 state['rerolls'].append({'shot':shot,'duration':dur,'ref':ref,'action':action,'payload':payload,'job':job,'reason':'first base failed continuity/action QA','submitted_at':time.strftime('%Y-%m-%dT%H:%M:%S%z')})
 print('reroll',shot,job)
state_path.write_text(json.dumps(state,indent=2))
