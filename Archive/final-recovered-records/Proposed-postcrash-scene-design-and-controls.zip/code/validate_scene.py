import json,hashlib
from pathlib import Path
def validate(s,root):
 if s['status']!='PROPOSED_NOT_OBSERVED':raise ValueError('Do not authenticate proposed positions as observed')
 if s['paid_enabled'] or s['video_approval']:raise ValueError('Preparation carries no execution authority')
 if not all(v[1]<0 for v in s['cameras'].values()):raise ValueError('Axis crossing')
 expected={'harry':('Draconia. Look at me. What did you do?',3,'Controlled alarm and accusation'),'draconia':('I spent weeks trying to warn you. You never once listened.',4.5,'Genuinely scared but holds her ground')}
 for sh in s['shots']:
  line,dur,intent=expected[sh['actor']]
  if sh['locked_dialogue']!=line or sh['duration_s']!=dur:raise ValueError('Locked dialogue/timing drift')
  if not sh['intent'].startswith(intent):raise ValueError('Dramatic intent drift')
  p=Path(__file__).resolve().parents[1]/'locked-audio'/sh['audio']
  if not p.exists():p=root/'scene-design/locked-audio'/sh['audio']
  if not p.exists():p=root/'locked-audio'/sh['audio']
  if not p.exists():p=root/'hybrid-run/inputs'/sh['audio']
  if hashlib.sha256(p.read_bytes()).hexdigest()!=sh['audio_sha256']:raise ValueError('Locked audio mismatch')
 return True
if __name__=='__main__':
 r=Path(__file__).resolve().parents[1];print(validate(json.load(open(r/'scene-contract.json')),r.parent))
