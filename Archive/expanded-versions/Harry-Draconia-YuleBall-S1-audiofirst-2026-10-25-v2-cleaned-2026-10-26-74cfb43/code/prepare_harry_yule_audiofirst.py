import json, sys, shutil
from pathlib import Path
sys.path.insert(0,'/tmp/avfix-roundtrip/DramaSaga-main')
from magicdrama.audiofirst.runner import run

OUT=Path('/tmp/harry-yule-audiofirst')
if OUT.exists(): shutil.rmtree(OUT)
brief={
 'series_id':'harry_draconia_yule_ball_s1','season':1,'character_count':2,'episodes_per_season':10,
 'genres':['fantasy','romance','action'],
 'setting':'An original alternate Hogwarts story for adults: a new Yule Ball is held after the old war, and Harry Potter is forced to partner with Draconia Malfoy, a sharp female version of Draco, when an old enchantment under the Great Hall turns dance music into dangerous spell-work. Cinematic photorealistic realism, candlelit castle, snowy courtyard, Forbidden Forest edge, dynamic wand action and emotional restraint. English only, vertical 9:16, no anime, no direct copying of supplied reels, no explicit sexual content.',
 'language':'en-GB','target_season_seconds':300,'max_episode_seconds':30,
 'characters':[
  {'id':'harry','name':'Harry Potter','description':'Adult British wizard, early 30s, protective, dry humor, guarded grief, quick under pressure','image':{'mode':'generate','model':'nano-banana-2.1','prompt':'Cinematic photorealistic adult Harry Potter identity sheet, dark messy hair, glasses, green eyes, formal black Yule Ball dress robes, subtle lightning scar, front and three-quarter view, neutral candlelit background'}},
  {'id':'draconia','name':'Draconia Malfoy','description':'Adult British witch, early 30s, female Malfoy, platinum blonde, sharp wit, defiant vulnerability, controlled elegance','image':{'mode':'generate','model':'nano-banana-2.1','prompt':'Cinematic photorealistic adult Draconia Malfoy identity sheet, female Malfoy, platinum blonde hair, pale gray eyes, emerald-silver Yule Ball gown and robes, poised but guarded expression, front and three-quarter view, neutral candlelit background'}}
 ]}
LOC={
 'great_hall':'The candlelit Great Hall dressed for a new Yule Ball: enchanted ceiling snowfall, long green and silver garlands, polished dance floor and floating candles.',
 'courtyard':'A moonlit stone courtyard outside the Great Hall, snow gathering on arches, frosted windows glowing warm from the ball.',
 'mirror_gallery':'A narrow castle gallery of tall antique mirrors, cold blue moonlight, dark frames reflecting the Yule Ball below.',
 'undercroft':'A forgotten stone undercroft beneath the Great Hall, carved dance steps in the floor, roots in the cracks and old green spell-light.',
 'forest_edge':'The snowy edge of the Forbidden Forest at night, black trees, ground mist and distant castle lights.'}
WARD={'harry':'Harry wears the same formal black Yule Ball dress robes, white shirt, dark trousers, glasses and polished shoes in every shot','draconia':'Draconia wears the same emerald-silver Yule Ball gown under formal dark robes, platinum hair in a low twisted style, silver earrings and wand holster'}
PROPS={'wand':('wand','slender wizard wand'),'card':('dance-card','enchanted Yule Ball dance card with moving green ink'),'ribbon':('silver-ribbon','silver ribbon sealed with green wax'),'candles':('floating-candles','floating wax candles used as ball lights'),'mirror':('tall-mirror','tall antique mirror in a black frame'),'program':('ball-program','folded Yule Ball programme'),'candelabra':('silver-candelabra','silver candelabra with green-flamed candles'),'orb':('glass-orb','small glass music orb containing the waltz spell')}

def ep(n,title,setup,turn,cliff,beats):
    eid=f'e{n:02d}'; lines=[]; shots=[]
    for i,b in enumerate(beats,1):
        sid=f'{eid}s{i:02d}'; line_ids=[]
        if b.get('line'):
            lid=f'{sid}l1'; lines.append({'id':lid,'speaker':b['line'][0],'text':b['line'][1],'performance':b['line'][2]}); line_ids=[lid]
        propnames=b.get('props',['wand'])
        shots.append({'id':sid,'seconds':6,'line_ids':line_ids,'location':b['loc'],'location_description':LOC[b['loc']],
            'visible_characters':b.get('chars',['harry','draconia']),'camera':b['camera'],'action':b['action'],
            'wardrobe':'; '.join(WARD[c] for c in b.get('chars',['harry','draconia'])),'props':propnames,
            'recurring_props':[{'id':PROPS[p][0],'description':PROPS[p][1]} for p in propnames if p in PROPS]})
    return {'id':eid,'title':title,'draft_seconds':30,'setup':setup,'turn':turn,'cliffhanger':cliff,'shots':shots,'lines':lines}
E=[]
E.append(ep(1,'A Name in Ice','At the first new Yule Ball, an enchanted dance card writes Harry and Draconia as partners.','The card freezes the floor when they refuse.','The first crack opens under the orchestra.',[
 {'loc':'great_hall','camera':'wide slow push through floating candles','action':'Harry enters the glittering Yule Ball alone while Draconia crosses the floor from the opposite doors','props':['candles','program'],'line':('harry','I came for ten quiet minutes, not a war reunion.','sighs, dry and guarded')},
 {'loc':'great_hall','camera':'close insert on enchanted card','action':'A silver dance card snaps open and green ink writes their names together','props':['card'],'line':('draconia','Tell your scar to stop picking my partners.','angry, sharp wit')},
 {'loc':'great_hall','camera':'two-shot circling them','action':'The orchestra stops as frost races across the dance floor around their shoes','props':['card','candles'],'line':('harry','That was not my spell.','curious, alarmed')},
 {'loc':'great_hall','camera':'low angle on cracked floor','action':'The polished floor splits in a perfect dance-step pattern and green light breathes through it','props':['card'],'line':('draconia','Then congratulations, Potter. The floor hates both of us.','nervous, controlled')},
 {'loc':'courtyard','camera':'static wide through snowy arch','action':'Harry and Draconia look back at the sealed ballroom doors as candle flames turn green behind the glass','props':['candles']}]))
E.append(ep(2,'The Rehearsal','The card will not open the hall until its chosen partners practice the old waltz.','Their forced steps awaken mirror images below them.','The mirrored Draconia dances after the real one stops.',[
 {'loc':'courtyard','camera':'tracking shot around snowy colonnade','action':'The card pulls Harry and Draconia into a practice frame beneath the arches','props':['card'],'line':('harry','One rehearsal. Then we burn the card.','angry, clipped')},
 {'loc':'courtyard','camera':'close-up hands and wands','action':'Their wands spark green and gold when they take formal dance positions','props':['wand','card'],'line':('draconia','Try not to lead like you are chasing a Snitch.','whispers, tense humor')},
 {'loc':'courtyard','camera':'overhead crane looking down','action':'Their shadows complete a perfect waltz even while their bodies stumble apart','props':['card'],'line':('harry','The steps are older than the school.','curious, uneasy')},
 {'loc':'mirror_gallery','camera':'rack focus from real faces to mirror faces','action':'A tall mirror shows the pair dancing flawlessly, but the reflected Draconia keeps moving alone','props':['mirror'],'line':('draconia','Potter, why is she still dancing?','nervous, whispered')},
 {'loc':'mirror_gallery','camera':'static close on mirror surface','action':'The mirrored Harry turns and points beneath the floor','props':['mirror','wand']}]))
E.append(ep(3,'Green and Silver','Draconia recognizes the music as an old house ward, not a dance tune.','Harry hears a familiar voice hidden inside the spell.','The melody writes his mother\'s name in frost.',[
 {'loc':'great_hall','camera':'macro on vibrating glass orb','action':'A glass music orb plays the waltz backward while frost curls over the tables','props':['orb','candelabra'],'line':('draconia','This is not music. It is a Slytherin warning.','curious, urgent')},
 {'loc':'great_hall','camera':'close on Harry as sound drops away','action':'Harry touches the orb and the hall becomes silent except for a woman humming','props':['orb'],'line':('harry','I know that voice. I have heard it my whole life.','sad, stunned')},
 {'loc':'great_hall','camera':'side tracking between them','action':'Draconia steadies the orb while Harry\'s wand hand trembles','props':['orb','wand'],'line':('draconia','Then listen, but do not follow it alone.','softly, protective')},
 {'loc':'great_hall','camera':'low dolly over frosted floor','action':'Green frost writes Lily across the dance steps, then scratches it out','props':['orb','card'],'line':('harry','It knows her name.','whispers, shaken')},
 {'loc':'undercroft','camera':'static shaft of green light','action':'A hidden stair opens beneath the final dance step','props':['wand']}]))
E.append(ep(4,'Steps in the Dark','Harry and Draconia descend into the undercroft where the first Yule Ball was buried.','The spell forces them through a vertical dance over broken stone.','The carved floor calls Draconia by the Malfoy name.',[
 {'loc':'undercroft','camera':'handheld follow down spiral stairs','action':'Harry lights the stairway while Draconia tests each step with her wand','props':['wand'],'line':('harry','Stay on the carved steps. The gaps are moving.','nervous, focused')},
 {'loc':'undercroft','camera':'wide vertical shot','action':'Stone platforms rise and turn like dancers, forcing the pair to leap in time with the music','props':['wand','candles'],'line':('draconia','If I fall, I am taking your reputation with me.','laughs, frightened wit')},
 {'loc':'undercroft','camera':'spinning two-shot','action':'Harry catches Draconia mid-turn as a platform drops away under her','props':['wand'],'line':('harry','I have you. Move on my count.','excited, commanding')},
 {'loc':'undercroft','camera':'close on carved names','action':'The floor illuminates old partner names, ending with MALFOY in green','props':['card'],'line':('draconia','No. My family paid for this dance in secrets.','sad, angry')},
 {'loc':'undercroft','camera':'static low angle','action':'A root splits the carved MALFOY name and wraps around the silver ribbon on Draconia\'s wrist','props':['ribbon']}]))
E.append(ep(5,'The House Debt','The undercroft demands a truthful apology from each chosen partner.','Draconia\'s apology would expose a Malfoy betrayal tied to Harry\'s family.','She chooses silence and the spell returns to the ball above.',[
 {'loc':'undercroft','camera':'close two-shot lit by wand tips','action':'The carved floor asks for a debt, each word appearing as frost on stone','props':['wand','card'],'line':('harry','What does it want from us?','curious, wary')},
 {'loc':'undercroft','camera':'slow push on Draconia','action':'Draconia reads the green words and hides them with her sleeve','props':['ribbon'],'line':('draconia','A confession. Mine would burn what is left of my name.','whispers, afraid')},
 {'loc':'undercroft','camera':'over-shoulder Harry','action':'Harry lowers his wand instead of pressing her','props':['wand'],'line':('harry','Then we find another way. No one gets sacrificed tonight.','softly, resolute')},
 {'loc':'undercroft','camera':'low angle as steps collapse upward','action':'Draconia seals the stair with green fire and chooses the ballroom over the truth','props':['wand','ribbon'],'line':('draconia','Remember that choice when you hate me tomorrow.','sad, controlled')},
 {'loc':'great_hall','camera':'wide rush through frozen dancers','action':'The music snaps back on above them and every candle flares green','props':['candles','orb']}]))
E.append(ep(6,'The Broken Bow','The enchantment freezes the Yule Ball guests in the middle of the first dance.','Harry and Draconia cross the moving floor while spell-light hunts them.','The faceless orchestra chooses Harry as the final partner.',[
 {'loc':'great_hall','camera':'tracking low over moving floorboards','action':'Frozen couples tilt like statues while Harry and Draconia weave between them','props':['candles','program'],'line':('draconia','Do not break the rhythm. It is counting us.','nervous, urgent')},
 {'loc':'great_hall','camera':'whip pan with spell streaks','action':'Green bolts chase them across the floor; Harry deflects one into a floating candle','props':['wand','candles'],'line':('harry','Left spin, now. Do not let go.','excited, protective')},
 {'loc':'great_hall','camera':'slow-motion two-shot','action':'Draconia pulls Harry through a falling ribbon of silver light and lands in the correct step','props':['ribbon','wand'],'line':('draconia','You are heavy for a savior.','laughs, breathless')},
 {'loc':'great_hall','camera':'close on faceless conductor','action':'The orchestra conductor turns without a face and points its bow at Harry','props':['orb'],'line':('harry','It wants me alone.','whispers, realizing')},
 {'loc':'great_hall','camera':'static overhead','action':'The dancers rotate outward, leaving Harry and Draconia isolated in the center circle','props':['candles','card']}]))
E.append(ep(7,'What the Mirror Saw','The mirror gallery reveals the memory Draconia tried to bury.','Harry learns she sabotaged the old curse years ago, not helped it.','The mirror accuses Harry of bringing the curse back.',[
 {'loc':'mirror_gallery','camera':'slow dolly past mirrors','action':'Every mirror shows a different year of the Yule Ball spell, ending with a younger Draconia breaking a green seal','props':['mirror'],'line':('harry','You tried to stop this before I ever knew it existed.','softly, stunned')},
 {'loc':'mirror_gallery','camera':'close Draconia and reflection','action':'Draconia faces the reflected version of herself refusing to look away','props':['mirror','ribbon'],'line':('draconia','I failed. In my family, that is the same as helping.','sad, bitter')},
 {'loc':'mirror_gallery','camera':'over-shoulder Harry','action':'Harry touches the mirror and sees his own childhood bedroom flash inside','props':['mirror','wand'],'line':('harry','Why does it have my memories?','curious, afraid')},
 {'loc':'mirror_gallery','camera':'static symmetrical two-shot','action':'Green cracks spread from Harry\'s scar across the mirror surface','props':['mirror'],'line':('draconia','Because it did not wake for me. It woke for you.','whispers, shaken')},
 {'loc':'mirror_gallery','camera':'macro on breaking glass','action':'The mirror writes POTTER in green and shatters inward without falling','props':['mirror','wand']}]))
E.append(ep(8,'The Uninvited','A faceless champion forms from the broken mirror and claims the final waltz.','Draconia shields Harry, reversing the role the curse expects.','Her confession begins to break the spell.',[
 {'loc':'great_hall','camera':'wide hero shot amid green sparks','action':'Mirror shards assemble into a faceless dancer in antique black robes','props':['mirror','candles'],'line':('harry','It is using the old champion. Wand up.','angry, focused')},
 {'loc':'great_hall','camera':'fast circling combat shot','action':'The champion and Harry trade green and gold spell arcs over the moving floor','props':['wand'],'line':('draconia','Its left turn is late. Break on three.','excited, precise')},
 {'loc':'great_hall','camera':'slow-motion impact frame','action':'Draconia steps in front of Harry and catches a curse on her silver ribbon','props':['ribbon','wand'],'line':('draconia','Not him. Not again.','angry, desperate')},
 {'loc':'great_hall','camera':'close on her face in green light','action':'Draconia faces the champion as her ribbon burns without harming her','props':['ribbon'],'line':('draconia','I hid the debt because I was ashamed. I am not hiding now.','softly, breaking')},
 {'loc':'great_hall','camera':'low static wide','action':'The champion freezes mid-step and the frozen guests breathe again for one heartbeat','props':['candles','card']}]))
E.append(ep(9,'The Last Dance','The curse can only end if both partners choose the dance without being forced.','Harry answers Draconia\'s confession with his own.','Their chosen waltz breaks the champion but opens the forest door.',[
 {'loc':'great_hall','camera':'slow circle around center floor','action':'Harry offers his hand to Draconia while the card burns between them','props':['card','wand'],'line':('harry','I spent years blaming easy targets because the real ones were dead.','sad, honest')},
 {'loc':'great_hall','camera':'close on joined hands','action':'Draconia takes his hand and the green card turns silver','props':['card','ribbon'],'line':('draconia','Then we are both done being haunted by other people\'s names.','softly, vulnerable')},
 {'loc':'great_hall','camera':'sweeping overhead waltz shot','action':'They dance one clean turn and the floor repairs beneath every step','props':['candles'],'line':('harry','One dance. No prophecy, no debt. Just us.','whispers, tender')},
 {'loc':'great_hall','camera':'impact zoom on shattering champion','action':'The faceless champion bows, then shatters into harmless mirror dust','props':['mirror','wand'],'line':('draconia','I hate that you dance better when terrified.','laughs, relieved')},
 {'loc':'courtyard','camera':'static wide through opening doors','action':'Every candle turns white as the courtyard doors blow open toward the dark forest','props':['candles']}]))
E.append(ep(10,'Midnight Candles','The ball is saved, but the forest sends one final answer.','Draconia leaves before anyone can define what changed.','Harry finds her silver ribbon and an invitation she did not write.',[
 {'loc':'courtyard','camera':'handheld follow through snow','action':'Guests wake behind them while Harry follows Draconia into the snow','props':['program'],'line':('draconia','Do not make this noble, Potter. It was one dance.','nervous, defensive')},
 {'loc':'courtyard','camera':'close two-shot under arch','action':'Harry stops her gently as snow gathers on their robes','props':['ribbon'],'line':('harry','Then give me one honest thing before you go.','softly, earnest')},
 {'loc':'courtyard','camera':'close on Draconia\'s expression','action':'Draconia almost steps closer, then pulls back and presses the silver ribbon into his hand','props':['ribbon'],'line':('draconia','I wanted the card to choose us.','whispers, exposed')},
 {'loc':'forest_edge','camera':'wide static from behind Harry','action':'Green light moves between the Forbidden Forest trees in the shape of a bowing dancer','props':['ribbon','wand'],'line':('harry','Draconia, the forest is answering.','curious, alarmed')},
 {'loc':'forest_edge','camera':'macro on ribbon','action':'The ribbon unfolds into a new invitation: SECOND DANCE, MIDNIGHT, BRING THE HEIR OF SLYTHERIN','props':['ribbon','card']}]))
story={'series_id':brief['series_id'],'season':1,'source':'Original agent-written season from the user-approved Harry/female Malfoy/new Yule Ball premise; no copied reel beats','episodes':E}
voices={'draconia':'ZF6FPAbjXT4488VcRRnw','harry':'4dZr8J4CBeokyRkTRpoN'}
result=run(brief,OUT,story=story,voices=voices,image_cap=60)
print(json.dumps({'result':result,'episodes':len(E),'seconds':sum(e['draft_seconds'] for e in E),'shots':sum(len(e['shots']) for e in E),'lines':sum(len(e['lines']) for e in E)},indent=2))
