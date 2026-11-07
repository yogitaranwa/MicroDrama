import json,sys
from pathlib import Path
sys.path.insert(0,'/tmp/avfix-roundtrip/DramaSaga-main')
from magicdrama.audiofirst.original_h3 import build_original_h3_plan
root=Path('/tmp/avfix-roundtrip/DramaSaga-main')
graph=root/'vendor/h3-film-reference/research/h3/runpod/r2v_v1.json'
refs=[
 'ref-harry-front-close.png','ref-harry-speaking-profile.png','ref-harry-fullbody.png',
 'ref-draconia-front-close.png','ref-draconia-speaking-profile.png','ref-draconia-fullbody.png',
 'ref-two-shot-dialogue.png','ref-two-shot-action.png','ref-yule-ball-location.png']
speaker_assets={'harry':'ref-harry-speaking-profile.png','draconia':'ref-draconia-speaking-profile.png'}
lines=[
 {'id':'L1','speaker':'draconia','start':0.00,'end':1.68,'text':"Potter, don't turn around."},
 {'id':'L2','speaker':'draconia','start':1.68,'end':4.24,'text':'Dance now, insult me later.'},
 {'id':'L3','speaker':'harry','start':4.24,'end':6.80,'text':'This is how Slytherins ask?'},
 {'id':'L4','speaker':'draconia','start':6.80,'end':8.88,'text':"It's how they keep you alive."},
 {'id':'L5','speaker':'harry','start':8.88,'end':11.20,'text':'They follow the offbeat.'},
 {'id':'L6','speaker':'draconia','start':11.20,'end':13.12,'text':'Then count faster.'},
]
prompt='''Vertical cinematic photorealistic Yule Ball action-dialogue shot, 24 fps, 9:16. The supplied full soundtrack is the exact timing source; each active-speaker guide also carries the matching line-audio segment. Draw mouth motion from those line guides and do not invent dialogue.
Reference identity anchors: Image 1 Harry front close, Image 2 Harry speaking profile, Image 3 Harry full body, Image 4 Draconia front close, Image 5 Draconia speaking profile, Image 6 Draconia full body, Image 7 Harry and Draconia dialogue two-shot, Image 8 Harry and Draconia action two-shot, Image 9 the empty candlelit Yule Ball location.
Keep Harry as the same black-haired man with round glasses and black/red formal robes. Keep Draconia as the same platinum-blonde braided woman in the emerald gown. Preserve both identities, costumes, realistic faces and cinematic lighting.
Whole-line framing:
0.00-1.68s: Draconia is clearly visible and urgently warns Harry; keep her face and unobstructed mouth framed for the whole line.
1.68-4.24s: Draconia pulls Harry into a fast dance turn; keep her face and unobstructed mouth framed for the whole line while ice arrows flash past.
4.24-6.80s: Harry is clearly visible as he challenges her; keep his face and unobstructed mouth framed for the whole line and do not cut away to Draconia until his line ends.
6.80-8.88s: Draconia answers; keep her face and unobstructed mouth framed for the whole line.
8.88-11.20s: Harry follows the offbeat step; keep his face and unobstructed mouth framed for the whole line.
11.20-13.12s: Draconia corrects the count and pulls him clear; keep her face and unobstructed mouth framed for the whole line and do not let Harry's back occlude her mouth.
The ballroom location matches Image 9. Dynamic motion is allowed only while the active speaker remains visible.'''
pins=[]
for line in lines:
 start,end=line['start'],line['end'];mid=(start+end)/2;speaker=line['speaker'];asset=speaker_assets[speaker]
 for label,t in [('start',start),('mid',mid)]:
  pins.append({'seconds':round(t,4),'asset':asset,'role':f'line_{label}_image_audio_guide','line_id':line['id'],'speaker':speaker,'audio_asset':f"guide-{line['id']}-{label}.wav"})
result=build_original_h3_plan(
 graph,prompt=prompt,seconds=13.12,audio_asset='dialogue.wav',reference_images=refs,pins=pins,
 dialogue_lines=lines,speaker_pin_assets=speaker_assets)
result['clip_id']='harry-draconia-e01-original-h3-line-audio-guides-v4'
result['root_cause_fix']='Boundary or midpoint image-only guides anchored identity/framing at isolated frames but supplied no mouth dynamics. Attach the active speaker line-audio segment to each H3 guide at the line start and midpoint so the audited source-supported cond_audio path carries speech through the line while the full soundtrack remains exact.'
result['proposed_not_executed']=True
result['validation_required_before_any_future_render']=[
 'staged input SHA verification against INPUT_MANIFEST.json',
 'provider-side hard usage and spend limits verified before job creation',
 'explicit one-job spend approval',
 'post-render dense real-video whole-line QA',
 'reject on any speaker identity ambiguity, missing face, occluded mouth, or failed calibrated motion screen'
]
Path('/tmp/harry-original-h3-plan-v4.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'workflow_sha256':result['compiled']['workflow_sha256'],'frames':result['compiled']['frames'],'pins':len(pins),'pin_frames':[round(p['seconds']*24) for p in pins]},indent=2))
