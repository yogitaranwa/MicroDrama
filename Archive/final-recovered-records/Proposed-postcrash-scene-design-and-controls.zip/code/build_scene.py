"""Free local scene contract and blocking boards. No network/generation endpoint."""
import json,hashlib,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];ROOT=R.parent
FONT='/skills/platform/files/assets/fonts/melange-grotesk-350.ttf'
HEAD='/skills/platform/files/assets/fonts/Aime-Light.ttf'
SOURCE=R/'source/aftermath-existing-frame-0.7s.png'
if not SOURCE.exists():SOURCE=ROOT/'next-comparison/inputs/aftermath-existing-frame-0.7s.png'
AUDIO=R/'locked-audio'
if not AUDIO.exists():AUDIO=ROOT/'hybrid-run/inputs'
C=json.load(open('/skills/platform/files/assets/tokens.json'))['colors']
def font(n,b=False):return ImageFont.truetype(HEAD if b else FONT,n)
def text(d,xy,t,size=25,fill=None,b=False):d.text(xy,t,font=font(size,b),fill=fill or C['ink'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def arrow(d,a,b,color,width=5):
 d.line([a,b],fill=color,width=width);dx=b[0]-a[0];dy=b[1]-a[1];l=math.hypot(dx,dy);ux,uy=dx/l,dy/l;tip=[b,(b[0]-16*ux+8*uy,b[1]-16*uy-8*ux),(b[0]-16*ux-8*uy,b[1]-16*uy+8*ux)];d.polygon(tip,fill=color)
S={'id':'e01-s17-s18-proposed-blocking-v1','status':'PROPOSED_NOT_OBSERVED','units':'relative layout units, not measured room dimensions','paid_enabled':False,'source_aftermath_sha256':sha(SOURCE),'actors':{'harry':[-1,0],'draconia':[1,0]},'landmarks':{'window':[0,6],'wreckage':[0,3],'icy_table':[-1.4,-.6]},'cameras':{'master':[0,-4],'harry_close':[1,-2],'draconia_close':[-1,-2]},'camera_height':'same eye level; target actor eyes, not lens','axis':'Harry to Draconia, y=0; every camera y<0','spatial_approval':False,'video_approval':False,'shots':[]}
for who,line,audio,dur,emotion,gaze in [('harry','Draconia. Look at me. What did you do?','e01-l16-harry.mp3',3,'Controlled alarm and accusation, not relief or humor. Turns attention to Draconia, demands an answer.','screen-right'),('draconia','I spent weeks trying to warn you. You never once listened.','e01-l17-draconia.mp3',4.5,'Genuinely scared but holds her ground. Hurt and defensive resolve, not wry disbelief or relief.','screen-left')]:
 p=AUDIO/audio;S['shots'].append({'actor':who,'duration_s':dur,'locked_dialogue':line,'audio':audio,'audio_sha256':sha(p),'camera':who+'_close','eyeline':gaze,'intent':emotion,'mouth_requirement':'readable actual mouth performance must match locked take; unverified','wardrobe':('black red-lined robes, white shirt, straight dark necktie, round glasses' if who=='harry' else 'emerald gold-embroidered gown, braided blonde updo, earrings')})
(R/'scene-contract.json').write_text(json.dumps(S,indent=2))
# Source overlay: illustrative actor marks only, never photoreal actor composites.
im=Image.new('RGB',(1000,1560),C['raised']);d=ImageDraw.Draw(im);d.rounded_rectangle((24,24,976,1536),radius=24,fill='white')
text(d,(62,54),'Proposed scene blocking',42,b=True);text(d,(62,112),'NOT observed coverage  |  E01 s17 / s18  |  26 Oct 2026',23)
a=Image.open(SOURCE);a.thumbnail((690,1150));x=(1000-a.width)//2;im.paste(a,(x,177));d=ImageDraw.Draw(im)
for label,pt in [('H',(300,1180)),('D',(700,1180))]:
 d.ellipse((pt[0]-35,pt[1]-35,pt[0]+35,pt[1]+35),fill=C['teal'],outline='white',width=3);text(d,(pt[0]-10,pt[1]-18),label,28)
arrow(d,(342,1180),(658,1180),C['teal']);text(d,(285,1235),'Illustrative foreground actor marks',24,fill='white')
text(d,(62,1370),'Source: s18b2 at 0.7s. Room state is observed.',25)
text(d,(62,1412),'H / D marks and conversational axis are proposed.',25)
text(d,(62,1454),'Not a camera calibration or a finished frame.',25)
im.save(R/'01-source-proposal.png')
# Top-down illustrative map. Separate proposal from source pixels.
im=Image.new('RGB',(1000,1410),C['raised']);d=ImageDraw.Draw(im);d.rounded_rectangle((24,24,976,1386),radius=24,fill='white')
text(d,(62,55),'One axis, three planned views',40,b=True);text(d,(62,112),'PROPOSAL ONLY  |  relative layout, not a measured floor plan',23)
box=(100,175,900,1040);d.rounded_rectangle(box,12,outline=C['hairline'],width=3)
def p(v):return (500+v[0]*155,700-v[1]*75)
for name in ['window','wreckage','icy_table']:
 q=p(S['landmarks'][name]);d.rectangle((q[0]-120,q[1]-22,q[0]+120,q[1]+22),fill=C['raised']);text(d,(q[0]-106,q[1]-17),name.replace('_',' '),24)
h=p([-1,0]);dd=p([1,0]);d.line((150,h[1],850,h[1]),fill=C['ink-3'],width=3)
for label,pt in [('H',h),('D',dd)]:d.ellipse((pt[0]-25,pt[1]-25,pt[0]+25,pt[1]+25),fill=C['teal']);text(d,(pt[0]-9,pt[1]-17),label,25)
text(d,(135,650),'Conversation axis',22);arrow(d,(h[0]+30,h[1]),(dd[0]-30,dd[1]),C['teal'])
for name,label,target in [('master','M',[0,0]),('harry_close','C-H',[-1,0]),('draconia_close','C-D',[1,0])]:
 q=p(S['cameras'][name]);z=p(target);arrow(d,q,z,C['ink-2'],3);d.rounded_rectangle((q[0]-34,q[1]-22,q[0]+34,q[1]+22),5,fill='white',outline=C['ink'],width=2);text(d,(q[0]-29,q[1]-16),label,21)
# Same-side rule stated below the map; keep camera M label unobscured.
text(d,(62,1090),'M: common master must establish BOTH positions.',26)
text(d,(62,1140),'C-H: Harry looks right. C-D: Draconia looks left.',26)
text(d,(62,1190),'Same eye height. Match light, depth and lens scale.',26)
text(d,(62,1250),'No observed master currently proves these marks.',24)
text(d,(62,1295),'No image, motion or lip call enabled by this design.',24)
im.save(R/'02-camera-plan.png')
# Compile coherent prep, not provider payload.
prep={'status':'PREPARATION_ONLY','source_contract':S['id'],'network_allowed':False,'master_requirement':'both actors at proposed marks with room/wreckage/table and mutual eyelines readable','shots':[]}
for s in S['shots']:
 prep['shots'].append({'actor':s['actor'],'locked_audio_sha256':s['audio_sha256'],'duration_s':s['duration_s'],'direction':s['intent'],'spatial_control':{'camera':S['cameras'][s['camera']],'actor':S['actors'][s['actor']],'look_target':S['actors']['draconia' if s['actor']=='harry' else 'harry'],'eyeline':s['eyeline'],'axis_side':'near-side negative y','height':'matched eye height'},'wardrobe':s['wardrobe'],'aftermath':'fallen principal chandelier remains on floor, broken overhead suspension, ice and surviving side candles; opposite camera must see consistent side-specific architecture, not duplicate frontal window backdrop','acceptance':['common master positions approved','matched eyeline/scale/state/wardrobe','correct accusation/fear intent','mouth follows exact locked take','continuous video/audio review before release']})
(R/'compiled-preparation.json').write_text(json.dumps(prep,indent=2))
# Executable refusal/consistency checks.
checks=[]
assert S['status']=='PROPOSED_NOT_OBSERVED';checks.append('proposal provenance retained')
assert all(v[1]<0 for v in S['cameras'].values());checks.append('all cameras same side of conversational axis')
assert all(sha(AUDIO/s['audio'])==s['audio_sha256'] for s in S['shots']);checks.append('both locked takes unchanged')
assert [s['duration_s'] for s in S['shots']]==[3,4.5];checks.append('dialogue windows retained')
assert not S['paid_enabled'] and not S['video_approval'] and not prep['network_allowed'];checks.append('no execution authority implied')
for s in S['shots']:
 pos=S['actors'][s['actor']];target=S['actors']['draconia' if s['actor']=='harry' else 'harry'];cam=S['cameras'][s['camera']];forward=(pos[0]-cam[0],pos[1]-cam[1]);right=(forward[1],-forward[0]);dot=(target[0]-pos[0])*right[0]+(target[1]-pos[1])*right[1];assert (dot>0)==(s['eyeline']=='screen-right')
checks.append('proposed camera/target projection gives opposing screen directions')
(R/'local-checks.json').write_text(json.dumps({'checks_passed':checks,'quality_pass':False,'production_modified':False,'paid_calls':0},indent=2));print('\n'.join(checks))
