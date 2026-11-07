import json
from pathlib import Path
p=Path('/tmp/harry-yule-audiofirst/story.json')
s=json.loads(p.read_text())
LOC={}
for e in s['episodes']:
 for sh in e['shots']: LOC[sh['location']]=sh['location_description']
WARD={e['shots'][0]['wardrobe'] for e in s['episodes']}
# Exact additions make the established 64s format real: 10 shots and 6 dialogue lines per episode.
X={
'e01':[
 ('great_hall','close dolly around sealed doors','Draconia tests the frozen door handle; green frost spells ONE STEP in her palm',['wand','card'],['draconia'],('draconia','It is not locking us out. It is inviting us back in.','curious, wary')),
 ('great_hall','overhead detail of frost geometry','Harry kneels and maps the cracks against the silent four-beat pulse of the candles',['card','candles'],['harry'],('harry','Every crack lands on a beat. This is choreography, not damage.','curious, controlled')),
 ('courtyard','macro on the dance card','The card flips itself over and stamps BOTH NAMES REQUIRED in silver ink',['card'],[],None),
 ('courtyard','handheld two-shot through snow','Draconia steps onto the first glowing crack before Harry can stop her, daring the floor to answer',['card','wand'],['draconia'],('draconia','Then let us give it a count it did not expect.','excited, impulsive')),
 ('great_hall','wide from the orchestra platform','The doors swing open by themselves and the first candle flame bends toward the hidden stair',['candles','wand'],['harry','draconia'],None)],
'e02':[
 ('mirror_gallery','wide symmetrical shot','The mirrored partners bow to each other while the real Harry and Draconia remain still',['mirror'],['harry','draconia'],('harry','The reflection is half a count ahead. It is showing the next move, not the last one.','curious, analytical')),
 ('courtyard','playful circling camera','Draconia deliberately misses a step; the mirror snaps to the correct one and taps the glass',['mirror','card'],['draconia'],('draconia','Finally, a partner who admits when I am right.','laughs, delighted')),
 ('mirror_gallery','slow tilt down mirror','The reflected ballroom dissolves into the buried undercroft, one stair at a time',['mirror'],['harry','draconia'],None),
 ('courtyard','close on Harry checking the doors','Harry counts the seconds between candle flickers and finds the same rhythm in the lock',['card','candles'],['harry'],('harry','We have nine minutes before the guests are readmitted.','nervous, precise')),
 ('mirror_gallery','low angle behind them','They step through the mirror\'s cold surface as the reflected Draconia curtsies to them',['mirror','wand'],['harry','draconia'],None)],
'e03':[
 ('great_hall','intimate close two-shot','Draconia recognizes the backward lullaby from old Malfoy nursery wards and goes still',['orb'],['draconia'],('draconia','My grandmother sang this when the family vault was about to bite.','sad, unsettled')),
 ('great_hall','close on Harry\'s ear and the orb','The hidden woman\'s humming resolves into Lily\'s name beneath the melody',['orb'],['harry'],('harry','She sang it forward. Someone buried her inside it backward.','whispers, grief-struck')),
 ('great_hall','macro on the cracking orb','A thin fracture crosses the glass orb, leaking silver notes that harden into stairs',['orb'],[],None),
 ('great_hall','close on joined hands','Draconia catches Harry\'s wrist before he can follow the sound alone',['orb','wand'],['harry','draconia'],('draconia','Stay with my voice, not hers. Count my steps.','softly, urgent')),
 ('undercroft','descending crane shot','The hidden stair spirals down around a column of green music',['wand','candles'],['harry','draconia'],None)],
'e04':[
 ('undercroft','fast lateral track','The platforms reverse direction, forcing Harry to read the rhythm three moves ahead',['wand','candles'],['harry'],('harry','Pattern changes on the seventh beat. Wait for my mark.','nervous, strategic')),
 ('undercroft','slow-motion leap','Draconia leaps before the mark and laughs when the stone rises to meet her',['wand'],['draconia'],('draconia','Your seventh beat is late. My sixth is better.','laughs, exhilarated')),
 ('undercroft','close on root and ribbon','The root tightens around the silver ribbon and pulls Draconia toward the carved MALFOY name',['ribbon'],['draconia'],None),
 ('undercroft','over-shoulder rescue','Harry cuts the root only after Draconia anchors her feet on the carved partner mark',['wand','ribbon'],['harry','draconia'],('harry','Do not pull away from it. Step into the mark and make it carry you.','excited, precise')),
 ('undercroft','low static on glowing floor','The carved floor opens a ledger: APOLOGY, DEBT, PARTNER, PRICE',['card','ribbon'],['harry','draconia'],None)],
'e05':[
 ('undercroft','close on frost words','Harry traces the ledger order and realizes the price changes if the apology is mutual',['card','wand'],['harry'],('harry','It does not need your name. It needs a true exchange. That is a loophole.','curious, intent')),
 ('undercroft','tight close on Draconia','Draconia shakes her head as the words reveal MALFOY BETRAYED EVANS',['ribbon'],['draconia'],('draconia','Some loopholes are just prettier traps, Potter.','sad, guarded')),
 ('undercroft','static wide on green fire','The undercroft writes the first debt in fire: WHO LET THE DANCE WAKE?',['wand','candles'],[],None),
 ('undercroft','two-shot in green light','Draconia admits part of the truth without naming the betrayer',['ribbon'],['draconia'],('draconia','My family fed the song a Potter memory. I buried the proof.','whispers, ashamed')),
 ('undercroft','close on Harry lowering his wand','Harry chooses not to demand the rest; the stair seals as the spell retreats upstairs',['wand'],['harry','draconia'],('harry','Then we make it ask for the truth when you are ready, not when it is hungry.','softly, steady'))],
'e06':[
 ('great_hall','rhythmic tracking shot','Draconia counts the frozen dancers aloud and spots the beat before each floor panel moves',['program','candles'],['draconia'],('draconia','Four beats forward, two sideways, one dramatic disaster. I adore a predictable curse.','excited, playful')),
 ('great_hall','close on conductor bow','Harry notices the faceless conductor lag behind the actual music',['orb','candles'],['harry'],('harry','The conductor is not leading. It is copying something under the floor.','curious, analytical')),
 ('great_hall','wide frozen tableau','The frozen guests rotate one exact step, forming a green-and-silver compass around the pair',['candles','program'],[],None),
 ('great_hall','close two-shot mid-spin','Draconia changes the count and forces the compass to open a path',['wand','ribbon'],['harry','draconia'],('draconia','Try to look impressed, Harry. I just outdanced a haunting.','laughs, breathless')),
 ('great_hall','overhead static','The center circle contracts until only one partner mark remains under Harry\'s feet',['card','candles'],['harry','draconia'],None)],
'e07':[
 ('mirror_gallery','quiet close two-shot','Harry asks why Draconia buried the proof instead of asking for help',['mirror','ribbon'],['harry'],('harry','You were a child. Why carry it alone?','softly, direct')),
 ('mirror_gallery','close Draconia profile','Draconia admits pride was the only Malfoy heirloom she wanted to keep',['mirror'],['draconia'],('draconia','Because admitting fear feels like handing someone a knife.','whispers, vulnerable')),
 ('mirror_gallery','reflection flashback','The mirror shows Lily\'s melody being stolen through a green-silver dance card',['mirror','card'],[],None),
 ('mirror_gallery','close on Harry','Harry sees his mother hum the same tune in a memory the curse should not own',['mirror'],['harry'],('harry','It stole the safest thing I had.','sad, barely controlled')),
 ('mirror_gallery','static broken symmetry','Draconia places her hand beside his on the glass, not quite touching',['mirror','ribbon'],['harry','draconia'],('draconia','Then we steal it back. Loudly, badly, together.','excited, fierce'))],
'e08':[
 ('great_hall','combat wide','Harry marks the champion\'s delayed turn and directs Draconia to the open side',['wand','candles'],['harry'],('harry','Break on three. I will hold its pattern; you break its rhythm.','angry, strategic')),
 ('great_hall','fast circling shot','Draconia ignores the count, spins early, and makes the champion copy the wrong partner',['wand','ribbon'],['draconia'],('draconia','Three is so predictable. Try now.','laughs, daring')),
 ('great_hall','slow-motion ribbon burn','The silver ribbon absorbs the curse and reveals the hidden Malfoy seal',['ribbon'],['draconia'],None),
 ('great_hall','intimate close','Draconia completes the confession in front of the champion and the waking guests',['ribbon'],['draconia'],('draconia','I hid the proof because I wanted one choice my family did not make for me.','whispers, breaking open')),
 ('great_hall','low two-shot','Harry reaches through the fading curse and offers his hand without looking away from her',['wand','ribbon'],['harry','draconia'],('harry','Then choose now. Not because the card says it.','softly, certain'))],
'e09':[
 ('great_hall','playful close','Draconia looks at the waking guests and reaches for a joke before courage',['candles','card'],['draconia'],('draconia','If this ends badly, I am blaming your footwork.','nervous, bright')),
 ('great_hall','close on Harry','Harry lets the strategy drop and answers plainly',['card'],['harry'],('harry','For once, I do not want the safest plan. I want this dance.','softly, vulnerable')),
 ('great_hall','overhead full ballroom','The guests wake one by one as the repaired floor turns silver beneath the chosen dance',['candles','program'],[],None),
 ('great_hall','slow push toward near kiss','Draconia leans in as the final candle turns white, then the courtyard doors burst open',['candles'],['harry','draconia'],('draconia','Of course the castle waits for the exact wrong second.','laughs, frustrated')),
 ('courtyard','wide toward forest','A green bow of light rises over the Forbidden Forest and answers the waltz',['wand','ribbon'],['harry','draconia'],None)],
'e10':[
 ('courtyard','playful tracking shot','Draconia tries to turn the almost-kiss into a joke before it becomes real',['program'],['draconia'],('draconia','One dance, one haunting, zero sensible decisions. A perfect evening.','laughs, nervous')),
 ('courtyard','close two-shot','Harry refuses the deflection without pushing her',['ribbon'],['harry'],('harry','I asked for honesty, not a review of my decisions.','softly, dry')),
 ('courtyard','close on ribbon handoff','Draconia presses the silver ribbon into his palm and closes his fingers around it',['ribbon'],['draconia'],None),
 ('forest_edge','wide static','The bowing light retreats between the trees, leaving one silver footprint at a time',['ribbon','wand'],['harry','draconia'],('draconia','That is either an invitation or a threat. Wonderful. My favorite kind.','excited, uneasy')),
 ('forest_edge','macro invitation reveal','The ribbon seals itself with green wax: SECOND DANCE, MIDNIGHT, BRING THE HEIR OF SLYTHERIN',['ribbon','card'],['harry','draconia'],None)]}
for e in s['episodes']:
    e['draft_seconds']=64
    e['cliffhanger']=X[e['id']][-1][2] if X[e['id']][-1][2] else e['cliffhanger']
    for idx,sh in enumerate(e['shots'],1): sh['seconds']=6.4
    lines=e['lines']; shots=e['shots']
    for j,(loc,camera,action,props,chars,line) in enumerate(X[e['id']],6):
        sid=f"{e['id']}s{j:02d}"; line_ids=[]
        if line:
            lid=f'{sid}l1'; lines.append({'id':lid,'speaker':line[0],'text':line[1],'performance':line[2]}); line_ids=[lid]
        shots.append({'id':sid,'seconds':6.4,'line_ids':line_ids,'location':loc,'location_description':LOC[loc],
            'visible_characters':chars,'camera':camera,'action':action,
            'wardrobe':'; '.join(x for x in e['shots'][0]['wardrobe'].split('; ') if (('Harry' in x) == ('harry' in chars) and (('Draconia' in x) == ('draconia' in chars)))) or e['shots'][0]['wardrobe'],
            'props':props,'recurring_props':[r for r in e['shots'][0].get('recurring_props',[]) if r['description'].split()[0] in ' '.join(props)]})
s['source']='Original agent-written 10-episode alternate Yule Ball arc, expanded to the established 64-second episode format after latest user steering; not model or reel copied'
p.write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'episodes':len(s['episodes']),'seconds':sum(e['draft_seconds'] for e in s['episodes']),'shots':sum(len(e['shots']) for e in s['episodes']),'lines':sum(len(e['lines']) for e in s['episodes'])}))
