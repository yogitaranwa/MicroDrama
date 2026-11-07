"""Offline adapter from the current production schema to a reviewable comparison plan.
No third-party imports or execution, network, production writes or implicit acceptance.
"""
import argparse, hashlib, json
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(root):
 m=root/'shot-manifest-wan30.json';data=json.loads(m.read_text());bank=json.loads((root/'harry-draconia-reference-bank.json').read_text());byname={r['name']:r for r in bank['references']}
 lock=json.loads((root/'production-2026-10-26/accepted-audio-sha256-lock.json').read_text());rows=[]
 for shot in data['shots']:
  if shot['episode']!='e01':continue
  take=None
  if shot.get('audio'):
   audio=root/'accepted-audio'/shot['audio'];digest=sha(audio)
   if digest!=lock.get(shot['audio']):raise ValueError('Locked audio mismatch: '+shot['audio'])
   take={'file':shot['audio'],'sha256':digest,'status':'locked_bytes_verified'}
  elapsed=0.0
  for beat in shot['beats']:
   refs=[]
   for name in beat.get('frame',{}).get('refs',[]):
    if name not in byname:raise ValueError('Reference not banked: '+name)
    rec=byname[name];refs.append({'name':name,'bank_id':rec['id'],'sha256':rec['sha256'],'views':rec['views'],'pixel_status':'not_in_transfer_not_inspected'})
   row={'id':f"e01s{shot['shot']:02d}b{beat['id']}",'parent_shot':shot['shot'],'start_in_shot_s':round(elapsed,6),'duration_s':beat['dur_s'],
        'aspect_ratio':'9:16','resolution':'720p','fps':30,'frame_description':beat.get('frame',{}).get('prompt'),
        'reference_bindings':refs,'audio_intent':beat['audio_intent'],'speaker':shot.get('speaker') if beat.get('carries_line') else None,
        'approved_take':take,'on_screen_speech_carrier':bool(beat.get('carries_line')),
        'camera_group':None,'parent_camera_frame':None,
        'render_enabled':False,'required_before_render':['review camera grouping and axis against actual pixels','inspect referenced source images and candidate keyframe','audio-conditioned performance route for readable speech; no text-only substitute'],
        'status':'comparison_plan_only_not_renderable'}
   row['input_sha256']=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest();rows.append(row);elapsed+=beat['dur_s']
 return {'manifest_sha256':sha(m),'source_scope':'current untrimmed113s planning manifest; recorded trim override not applied','source_license':'original local adapter; no third-party code copied',
         'shots':rows,'status':'prepared_for_review_not_generated','render_enabled':False,'note':'Camera relationships deliberately unset. Approved take belongs to whole shot, can continue over inserts; this is not per-beat copied speech.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=prepare(a.root);a.out.write_text(json.dumps(r,indent=2));print(len(r['shots']),'current beat rows prepared; render disabled')
