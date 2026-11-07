import json
from pathlib import Path
root=Path('/home/sandbox/e01-repair')
plan=json.loads(Path('/downloads/e01-v43-assembly-plan.json').read_text())
# This replaces the partial audit-derived gate action list with the actual script.
actions={
'1':['Harry enters alone at natural walking speed','black spark opens above Harry in the window reflection'],
'2':['Draconia notices the spark','Draconia drops her programme','Draconia pulls Harry into the dancers','Draconia remains readable while saying line 1'],
'3':['ice arrows strike the space Harry left','a guest stops running and freezes','glowing floor marks spread around her shoes','Harry and Draconia continue moving'],
'4':['masked figure in the window mirrors their first step','Harry notices the reflection','Draconia visibly confirms she sees it'],
'5':['arrows strike after the second orchestra beat','Harry shifts their step early','the next arrow visibly misses'],
'6':['Harry studies the green mark in the arrow holes','Draconia recognizes the ward mark','Draconia visibly loses her composure during lines 7-8'],
'7':['silver orchestra strings tear free','strings whip across the floor','Harry raises a slim wooden wand, not a blade'],
'8':['Harry cuts two strings with a wand charm','third string wraps Harry wrist','Draconia snaps it with her heel','empty armor steps out of the shadows'],
'9':['Draconia kicks the trolley and it strikes armor','Harry turns her stumble into a dance step','masked figure on floor copies them'],
'10':['glowing waltz grid pulls their feet','Harry points to the red table','Harry and Draconia deliver lines 11-12 with readable faces'],
'11a':['Draconia flips table as a shield, not a glide','Harry redirects charm with wooden wand','chandelier falls and strikes ice at natural speed'],
'11b':['green and silver marks burn around joined hands','Draconia says line 13 with visible fear'],
'12a':['doors seal','faceless masked figure bows','Harry looks hurt and suspicious at Draconia','Harry visibly says line 14 on camera'],
'12b':['Draconia maintains eye contact','Draconia visibly says line 15 somberly']}
manifest={'episode':'E01','status':'PREPARATION_ONLY_NO_GENERATION','source':'E01_script_v3.md, actual shot script; shot 11/12 split into 11a/11b and 12a/12b',
 'note':'Timing will be recut only to fit accepted action and unchanged dialogue. No missing action can be satisfied by crop, retime, synthetic camera motion, or a motion score. Script actions are mapped to their original narrative beats, not to the mistaken audit shot numbering.',
 'beats':[]}
for b in plan['beats']:
 b=dict(b); b['required_actions']=actions[b['beat']]
 # Correct the workaround: line14 belongs on Harry, not the hands crop.
 if b['beat']=='11b':b['lines']=[w for w in b['lines'] if w['line']!=14]
 if b['beat']=='12a':b['lines']=[{'line':14,'start':85.295,'end':87.055}]
 b['status']='REPLACE_OR_REVIEW_REQUIRED'
 manifest['beats'].append(b)
manifest['dialogue_change']='Only line14 placement is proposed for repair: move to Harry close-up 85.295-87.055; words, duration and order unchanged. Original v3 audio candidate deliberately retains old timing until new shots exist.'
Path('/home/sandbox/e01-repair/work/E01-v44-repair-requirements.json').write_text(json.dumps(manifest,indent=2))
