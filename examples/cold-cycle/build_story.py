"""Builds examples/cold-cycle/directed-story.json from the director's script (DIRECTORS_SCRIPT.md). Run from the repo root: python examples/cold-cycle/build_story.py"""
import json
from pathlib import Path

NORA_V = 'calm, low, warm woman in her early thirties, gentle and a little tired, speaking softly'
DEV_V = 'quiet, hoarse man in his late thirties, tired, restrained, every word careful'
LOOK = 'cold overhead fluorescent light (about 5000 K) from above, warm red neon wash through the south window on the floor and the near edge of the table, a blue glow from the vending machine on anything near the east end; the same in every shot'
AMB = 'rain on the shop window, a steady fluorescent hum, a distant machine rumble'

bible = {
    'format': '16:9, 24 fps, 35 mm lens equivalent, shallow depth of field, soft natural film grain, restrained naturalistic colour, no stylised grading, handheld-steady realism',
    'set': ('a small 24-hour laundromat at 2 a.m. in the rain: south wall with a glass front door at the left end and a large rain-streaked shop window with a red neon glow; north wall with a row of five '
            'white front-loading washing machines numbered 3 to 7 (7 at the right end), a notice board with a yellow LOST CAT flyer above machines 3 and 4, a glowing blue vending machine and a green wall clock '
            'reading 2:04 at the east end; east wall with stacked steel dryers; west wall with a WASH & FOLD price sign and two orange plastic chairs; a steel folding table in the middle; pale grey vinyl floor'),
    'geography': ('NORA stands on the north side of the steel folding table, in the aisle in front of washing machines 5 and 6, and stays on that spot. DEV stands at washing machine 7 at the east end of the aisle '
                  'and stays on that spot. They are about one metre apart. Shots from NORA\'S SIDE look west-south-west from just behind Dev\'s shoulder: behind Nora is the west wall with the WASH & FOLD sign '
                  'and the two orange chairs. Shots from DEV\'S SIDE look east-north-east from just behind Nora\'s shoulder: behind Dev are washing machines 6 and 7, the blue-glowing vending machine, the green wall clock and the stacked steel dryers. '
                  'Never swap the two backgrounds. Keep every object where it is.'),
    'lighting': 'The light never changes: ' + LOOK + '. Nobody touches a light switch. Only the red neon outside flickers once, in the first shot.',
    'performance': 'Naturalistic and restrained, like a film: micro-expressions, small hand movements, no grins, no wide-eyed shock, no big gestures. Nora is gentle and observant; Dev is hollowed out and polite. Nobody raises their voice and nobody cries openly.',
    'wardrobe_props': ('Nora: mustard raincoat worn open over a cream knit sweater, dark jeans, white trainers, dark hair in a loose bun with one strand free on the left, a pale blue towel in her hands. '
                       'Dev: grey zip hoodie (hood down), dark jeans, wet black trainers, short damp dark hair, two-day stubble. Prop: one folded deep-red wool scarf with a frayed end, three brass laundromat tokens.'),
    'set_short': 'a small laundromat at night: steel folding table in the middle, a row of white washing machines numbered 3 to 7 on the north wall, blue vending machine and green clock at the east end, stacked dryers on the east wall, WASH & FOLD sign and two orange chairs on the west wall, rain on the south window with red neon',
    'geography_short': 'Nora stands north of the table in front of machines 5-6; Dev stands at machine 7, about a metre away. Nora\'s side looks toward the west wall (sign and orange chairs behind her); Dev\'s side looks toward machines 6-7, the vending machine and clock behind him. Never swap backgrounds.',
    'lighting_rule': 'Unchanging cold fluorescent light from above, red neon wash from the south window, blue vending-machine glow at the east end. No switch is touched.',
    'wardrobe_short': 'Nora: mustard raincoat open over a cream sweater, jeans, white trainers, hair in a bun. Dev: grey zip hoodie (hood down), dark jeans, damp dark hair, stubble.',
    'performance_short': 'Naturalistic and restrained: micro-expressions only, no grins, no shock, no big gestures.',
}


def beats(*rows):
    return [{'t0': a, 't1': b, 'text': t} for a, b, t in rows]


def shot(id_, title, cast, intent, size, angle, move, lens, start, end, bts, perf, effects, line=None, speaker=None, delivery=None, keyframe=None, refs=None, light_extra=None):
    d = [{'speaker': speaker, 'voice': NORA_V if speaker == 'Nora' else DEV_V, 'line': line, 'delivery': delivery}] if line else []
    return {'id': id_, 'title': title, 'seconds': 4, 'cast': cast, 'intent': intent, 'start_state': start, 'end_state': end,
            'camera': {'size': size, 'angle': angle, 'movement': move, 'lens': lens}, 'lighting': light_extra or 'Unchanging, as in every shot.',
            'beats': bts, 'performance': perf, 'sound': {'ambience': AMB, 'effects': effects, 'dialogue': d},
            'keyframe': keyframe or start, 'keyframe_refs': refs or ['laundromat-plate'] + cast}


NA = 'Nora, standing north of the folding table in front of washing machines 5 and 6, mustard raincoat open, pale blue towel in her hands'
SH = [
    shot('c1-wide', 'Rain', ['Nora'], 'Establish the empty laundromat and Nora alone, folding.', 'wide', 'eye level', 'very slow push in about 5%', '24 mm',
         'From the front door looking north-east across the whole laundromat: Nora at the steel table folding a towel, the row of washing machines on the far wall, the vending machine glow at the right, rain on the window.',
         'Nora has turned her head a few degrees toward the sound of footsteps outside.',
         beats((0.0, 1.0, 'Nora folds a pale blue towel in thirds in a steady rhythm.'), (1.0, 2.0, 'She smooths it flat with both palms and pauses, listening to the rain.'),
               (2.0, 2.2, 'The red neon outside flickers once.'), (2.2, 3.2, 'She lifts the towel, shakes it out and starts a new fold.'), (3.2, 4.0, 'Her head turns a few degrees toward the door as a faint bell jingle sounds outside. No one speaks.')),
         'Quiet, unhurried, alone.', ['a faint bell jingle just before the door opens'],
         light_extra='Unchanging; the red neon flickers once at 2.0 s.'),
    shot('c2-look', 'The Bell', ['Nora'], 'Nora notices someone coming in.', 'medium close-up', 'eye level', 'slow push in about 4%', '35 mm',
         NA + ', alone in frame, the west wall with the WASH & FOLD sign and two orange chairs behind her, the glass front door at the left edge.',
         'Nora looks back down at the towel.',
         beats((0.0, 0.8, 'Her hands keep folding while her eyes lift toward the door.'), (0.8, 1.4, 'The door bell rings; her hands stop mid-fold.'),
               (1.4, 2.6, 'Her eyes follow someone entering, tracking slowly across the room.'), (2.6, 4.0, 'She breathes out slowly, looks back down at the towel and resumes folding. No one speaks.')),
         'Mild surprise, no smile.', ['the door bell rings', 'wet hurried footsteps on vinyl']),
    shot('c3-enter', 'Dev Enters', ['Dev'], 'A wet stranger comes in.', 'wide', 'eye level', 'slow drift about 3%', '24 mm',
         'From the dryer end of the room looking west: the glass front door in the middle distance with Dev just inside it, hood up, rain on his shoulders, a clear plastic bag in his left hand; the shop window at the left; the WASH & FOLD sign and two orange chairs on the far wall.',
         'Dev walks east across the room toward the washing machines, hood down.',
         beats((0.0, 1.0, 'Dev shakes rain off his shoulders and lowers his hood; wet footprints on the floor.'), (1.0, 2.4, 'He looks around the room once, avoiding eye contact.'),
               (2.4, 4.0, 'He walks east into the room toward the washing machines, clutching the bag. No one speaks.')),
         'Weary, polite, self-contained.', ['the door bell settles', 'wet footsteps']),
    shot('c4-tokens-offer', 'Spare Tokens', ['Nora'], 'Nora offers help.', 'medium close-up', 'eye level', 'slow push in about 4%', '35 mm',
         NA + '; the back of Dev\'s shoulder in a grey hoodie soft in the right foreground; behind her the west wall with the WASH & FOLD sign and two orange chairs.',
         'Nora holds the towel against her chest, waiting for his answer.',
         beats((0.0, 1.0, 'Nora watches him come to the machine, the towel in her hands.'), (1.0, 3.0, 'She speaks softly and kindly; her eyes soften and she holds the towel against her chest.'), (3.0, 4.0, 'She waits for his answer.')),
         'Kind, unhurried.', ['a faint breath'], line='Cards only. I have spare tokens.', speaker='Nora', delivery='soft, kind, unhurried'),
    shot('c5-thank', 'Thank You', ['Dev'], 'Dev accepts, surprised by the kindness.', 'medium close-up', 'eye level', 'slow push in about 4%', '35 mm',
         'Dev, standing at washing machine 7, grey hoodie, looking toward the camera; Nora\'s mustard shoulder soft in the left foreground; behind him washing machines 6 and 7, the blue-glowing vending machine, the green wall clock and the stacked steel dryers.',
         'Dev looks down at the plastic bag in his hand.',
         beats((0.0, 0.8, 'Dev turns his head toward Nora, caught off guard.'), (0.8, 3.0, 'He speaks quietly and hoarsely and gives a small nod.'), (3.0, 4.0, 'His eyes drop to the bag in his hand.')),
         'Tired gratitude, small movements.', ['a quiet breath'], line='That would help. Thank you.', speaker='Dev', delivery='quiet, hoarse, grateful'),
    shot('c6-tokens', 'Tokens', ['Nora', 'Dev'], 'The tokens change hands.', 'close-up insert', 'high angle over the table edge', 'tiny drift in about 1%', '50 mm',
         'Close on two hands over the steel table\'s north edge: Nora\'s right hand holds out three brass tokens, palm up; Dev\'s hand comes in from the right.',
         'Dev\'s hand closes around the tokens.',
         beats((0.0, 1.0, 'Nora\'s hand offers the tokens, palm up.'), (1.0, 2.0, 'His hand takes them; their fingers do not touch.'), (2.0, 3.2, 'He closes his fist around the tokens.'), (3.2, 4.0, 'His thumb strokes once over a token. No one speaks.')),
         'Delicate, careful hands.', ['tokens clink in a palm', 'a soft clink as the fist closes']),
    shot('c7-scarf', 'The Scarf', ['Dev'], 'The audience sees the one thing he brought.', 'close-up insert', 'eye level', 'tiny drift in about 1%', '50 mm',
         'Close on washing machine 7\'s round glass door with a white "7", and Dev\'s two hands at chest height opening a clear plastic bag.',
         'The drum door is closed and Dev\'s hand rests flat on the glass.',
         beats((0.0, 1.0, 'He unrolls the top of the bag.'), (1.0, 2.4, 'He draws out a deep-red wool scarf, folded, and holds it, his thumb on the frayed end, a beat too long.'),
               (2.4, 3.4, 'He lowers the scarf into the open drum.'), (3.4, 4.0, 'He closes the door; the latch clicks; his hand stays flat on the glass. No one speaks.')),
         'Gentle, reverent.', ['plastic bag rustle', 'the drum door latch clunk']),
    shot('c8-just-one', 'Just One', ['Nora'], 'Nora sees something is off.', 'medium close-up', 'eye level', 'slow push in about 4%', '35 mm',
         NA + '; Dev\'s shoulder soft in the right foreground; behind her the WASH & FOLD sign and two orange chairs.',
         'Nora waits, the towel still in her hands.',
         beats((0.0, 1.0, 'She watches him; her expression changes slowly from polite to curious.'), (1.0, 3.0, 'She speaks gently, her head tilting a few degrees.'), (3.0, 4.0, 'She waits.')),
         'Curious, gentle.', ['a faint breath'], line='Just the one scarf?', speaker='Nora', delivery='gentle, curious'),
    shot('c9-smells', 'Still Smells', ['Dev'], 'The emotional line.', 'medium close-up', 'eye level', 'very slow push in about 4%', '35 mm',
         'Dev at washing machine 7, one hand flat on the closed round glass door, face toward the camera; Nora\'s mustard shoulder soft in the left foreground.',
         'Dev\'s eyes close once and open again.',
         beats((0.0, 1.0, 'He stares at the drum, then turns his face toward the camera.'), (1.0, 3.0, 'He speaks very quietly; his jaw tightens on the last word.'), (3.0, 4.0, 'His eyes close once, then open.')),
         'Restrained, almost no movement.', ['a slow breath'], line='It still smells like her.', speaker='Dev', delivery='very quiet, breaking on the last word'),
    shot('c10-understands', 'Understanding', ['Nora'], 'Nora understands.', 'medium close-up', 'eye level', 'slow push in about 4%', '35 mm',
         NA + '; Dev\'s shoulder soft in the right foreground; behind her the WASH & FOLD sign and two orange chairs.',
         'Nora presses her lips together and gives a small nod to herself.',
         beats((0.0, 1.2, 'She has stopped folding; her hands rest on the towel.'), (1.2, 2.6, 'Her eyes move toward the drum and her breath catches.'), (2.6, 4.0, 'She presses her lips together and nods once to herself. No one speaks.')),
         'Quiet realisation, no tears.', ['one slow drip from Dev\'s sleeve off-screen']),
    shot('c11-cold-slow', 'Cold and Slow', ['Nora'], 'She offers him something to do with his grief.', 'medium close-up', 'eye level', 'slow push in about 4%', '35 mm',
         NA + '; Dev\'s shoulder soft in the right foreground; behind her the WASH & FOLD sign and two orange chairs.',
         'Nora has put the towel on the stack and keeps her eyes on him.',
         beats((0.0, 1.0, 'She sets the pale blue towel on the stack at the table and squares its edge.'), (1.0, 3.0, 'She speaks warmly with a very small smile.'), (3.0, 4.0, 'She keeps her eyes on him.')),
         'Warm, quiet.', ['a soft pat of the towel on the stack'], line='Then wash it cold and slow.', speaker='Nora', delivery='warm, quiet'),
    shot('c12-always', 'She Always Said', ['Dev'], 'A crack of warmth.', 'medium close-up', 'eye level', 'slow push in about 4%', '35 mm',
         'Dev at washing machine 7, face toward the camera; Nora\'s mustard shoulder soft in the left foreground; behind him washing machines 6 and 7, the blue-glowing vending machine, the green wall clock and the stacked steel dryers.',
         'Dev wipes under one eye with the heel of his hand.',
         beats((0.0, 1.0, 'He listens, then a breath that is almost a laugh.'), (1.0, 3.0, 'He speaks; his mouth trembles into a small broken smile.'), (3.0, 4.0, 'He wipes under one eye with the heel of his hand.')),
         'Bittersweet, restrained.', ['a short exhale'], line='She always said that.', speaker='Dev', delivery='soft, bittersweet'),
    shot('c13-drum', 'The Drum', ['Dev'], 'The scarf turns.', 'close-up insert', 'eye level', 'slow push in about 5%', '50 mm',
         'Close on washing machine 7\'s round glass door, the red scarf behind the glass, water beginning to enter.',
         'The red scarf rolls slowly behind the glass as red neon light slides across it.',
         beats((0.0, 1.2, 'Water starts to enter the drum; the scarf is a red shape behind the glass.'), (1.2, 3.0, 'The drum starts to turn slowly; the scarf rolls over once and settles.'), (3.0, 4.0, 'Red neon light slides across the glass as it turns. No one speaks.')),
         'No people, only the machine.', ['water filling the drum', 'the motor starting', 'a slow rhythmic turning']),
    shot('c14-wait', 'I Will Wait', ['Nora'], 'She decides to stay.', 'medium close-up', 'eye level', 'slow push in about 4%', '35 mm',
         NA + '; Dev\'s shoulder soft in the right foreground; behind her the WASH & FOLD sign and two orange chairs.',
         'Nora holds his gaze with a small honest look.',
         beats((0.0, 1.0, 'She glances at the orange chairs behind her.'), (1.0, 3.0, 'She speaks softly and nods toward the chairs.'), (3.0, 4.0, 'She holds his eyes.')),
         'Soft, sincere.', ['a faint breath'], line='I will wait with you.', speaker='Nora', delivery='soft, sincere'),
    shot('c15-wait-wide', 'Together', ['Nora', 'Dev'], 'They sit and watch the scarf turn.', 'wide', 'eye level', 'slow pull back about 5%', '24 mm',
         'From the front door looking north-east: Nora and Dev sit side by side on two orange chairs in front of washing machine 7, seen from behind, watching the drum turn; the table, the row of washers, the vending machine glow.',
         'The camera holds on the two of them as the end card appears.',
         beats((0.0, 1.5, 'They sit without speaking; the drum turns with red light on its glass.'), (1.5, 3.0, 'Nora\'s head tilts a few degrees toward Dev; Dev\'s shoulders drop.'), (3.0, 4.0, 'The camera holds. No one speaks.')),
         'Stillness.', ['the drum turning', 'the score swells then fades']),
]

# What every person on screen is busy with (never idle), and why anyone who enters or moves to a new place does so
ACTIVITY = {
    'c1-wide': {'Nora': 'folding towels from her grey basket onto the steel table'},
    'c2-look': {'Nora': 'folding a towel, then glancing at the door as the bell rings'},
    'c3-enter': {'Dev': 'shaking off the rain, then reading the numbers on the washing machines to find one that is free'},
    'c4-tokens-offer': {'Nora': 'folding a towel while watching him read the coin instructions'},
    'c5-thank': {'Dev': 'reading the coin-slot instructions on machine 7 and patting his pockets for change'},
    'c6-tokens': {'Nora': 'holding out three tokens from her pocket', 'Dev': 'taking the tokens'},
    'c7-scarf': {'Dev': 'unpacking the red scarf from the plastic bag into the drum'},
    'c8-just-one': {'Nora': 'folding the same towel while watching him'},
    'c9-smells': {'Dev': 'keeping his hand on the drum door and staring at the scarf'},
    'c10-understands': {'Nora': 'holding the half-folded towel, her work stopped'},
    'c11-cold-slow': {'Nora': 'putting the towel on the stack and squaring it'},
    'c12-always': {'Dev': 'wiping his eye as the cycle starts'},
    'c13-drum': {'Dev': 'off-screen at the machine, watching the drum fill'},
    'c14-wait': {'Nora': 'nodding at the orange chairs behind her, ready to sit'},
    'c15-wait-wide': {'Nora': 'sitting down beside him to watch the drum', 'Dev': 'sitting to watch the drum'},
}
ARRIVAL = {
    'c3-enter': {'Dev': {'from': 'the front door', 'to': 'the row of washing machines', 'why': 'he needs a machine to wash one thing', 'then': 'he reads the numbers on the machines and heads for machine 7'}},
    'c4-tokens-offer': {'Dev': {'from': 'the middle of the room', 'to': 'machine 7', 'why': 'it is the last free machine', 'then': 'he reads the coin-slot instructions'}},
    'c15-wait-wide': {'Nora': {'from': 'her spot at the table', 'to': 'the orange chairs by machine 7', 'why': 'the cycle takes thirty minutes and she has chosen to stay', 'then': 'she sits and watches the drum'},
                      'Dev': {'from': 'machine 7', 'to': 'the chair beside her', 'why': 'she pulled the chair out for him', 'then': 'he sits and watches the drum'}},
}
for sh_ in SH:
    sh_['activity'] = ACTIVITY[sh_['id']]
    if sh_['id'] in ARRIVAL:
        sh_['arrival'] = ARRIVAL[sh_['id']]

story = {
    'rules': {'chain': True, 'activity': True},
    'title': 'Cold Cycle', 'logline': 'At 2 a.m. in an empty laundromat a stranger washes one red scarf; the woman folding clothes understands it is all he has left of someone.',
    'aspect': '16:9', 'bible': bible, 'voices': {'Nora': NORA_V, 'Dev': DEV_V},
    'plate': {'id': 'laundromat-plate', 'file': 'laundromat-plate.png'}, 'portraits': {'Nora': 'nora-master.png', 'Dev': 'dev-master.png'},
    'shots': SH, 'hook_title': 'At 2 a.m., he washed one scarf...', 'end_card': "Some things aren't ready to be washed.",
}

# ---------------------------------------------------------------- floor plan (metres; x east, y north, z up; origin south-west corner)
FEAT = [('glass front door', [1.0, 0, 0, 2.0, 0.06, 2.1], '#7fb3c8'), ('shop window with rain and red neon', [3.0, 0, 0.9, 7.0, 0.06, 2.2], '#5f7fa8')]
for n, x0 in zip((3, 4, 5, 6, 7), (2.0, 2.8, 3.6, 4.4, 5.2)):
    FEAT.append((f'washing machine {n}', [x0, 4.3, 0, x0 + 0.7, 5.0, 1.0], '#e8e8e8'))
FEAT += [('notice board with a yellow LOST CAT flyer', [2.3, 4.94, 1.7, 3.5, 5.0, 2.2], '#d8c070'), ('blue-glowing vending machine', [6.4, 4.4, 0, 7.2, 5.0, 1.8], '#3a6fd0'),
         ('green wall clock', [6.7, 4.94, 2.1, 6.9, 5.0, 2.3], '#3fa05a'), ('stacked steel dryers', [7.3, 1.2, 0, 8.0, 4.2, 1.9], '#b8b8c0'),
         ('WASH & FOLD price sign', [0, 1.9, 1.6, 0.06, 2.9, 2.1], '#f0f0f0'), ('orange plastic chair (south)', [0.1, 1.85, 0, 0.6, 2.35, 0.9], '#e07a1f'),
         ('orange plastic chair (north)', [0.1, 2.55, 0, 0.6, 3.05, 0.9], '#e07a1f'), ('steel folding table', [3.6, 2.3, 0, 5.6, 3.1, 0.9], '#a0a0a8')]
NORA, DEV = (4.7, 3.55), (5.55, 3.8)
CAM = {
    'W': ([1.5, 0.35, 1.55], [5.0, 3.0, 1.1], 24, [1.55, 0.4, 1.55], [5.0, 3.0, 1.1]),
    'E': ([7.0, 1.2, 1.5], [1.5, 0.9, 1.3], 24, [6.9, 1.2, 1.5], [1.5, 0.9, 1.3]),
    'A': ([6.3, 3.4, 1.55], [4.7, 3.55, 1.5], 35, [6.25, 3.42, 1.55], [4.7, 3.55, 1.5]),
    'B': ([3.75, 3.3, 1.55], [5.55, 3.8, 1.5], 28, [3.8, 3.3, 1.55], [5.55, 3.8, 1.5]),
    'I1': ([5.0, 3.0, 1.15], [5.12, 3.65, 1.0], 50, [5.0, 3.05, 1.15], [5.12, 3.65, 1.0]),
    'I2': ([5.9, 3.4, 1.25], [5.55, 4.3, 0.95], 50, [5.88, 3.45, 1.25], [5.55, 4.3, 0.95]),
}


def fig(pos_s, f_s, pos_e=None, f_e=None):
    return {'start': {'pos': list(pos_s), 'facing': f_s}, 'end': {'pos': list(pos_e or pos_s), 'facing': f_e if f_e is not None else f_s}}


def entry(cam, figures, show=None, hide=None, reposition=False):
    c = CAM[cam]
    e = {'camera': {'lens': c[2], 'start': {'pos': c[0], 'target': c[1]}, 'end': {'pos': c[3], 'target': c[4]}}, 'figures': figures,
         'must_show': {'start': show or [], 'end': show or []}, 'must_not_show': {'start': hide or [], 'end': hide or []}}
    if reposition:e['reposition'] = True
    return e


A_SHOW = ['WASH & FOLD price sign', 'orange plastic chair (south)', 'orange plastic chair (north)', 'Nora']
A_HIDE = ['washing machine 7', 'blue-glowing vending machine', 'stacked steel dryers', 'green wall clock']
B_SHOW = ['washing machine 7', 'blue-glowing vending machine', 'green wall clock', 'Dev']
B_HIDE = ['WASH & FOLD price sign', 'orange plastic chair (south)', 'glass front door']
N_FACE, D_FACE = 14, 195
P = {}
P['c1-wide'] = entry('W', {'Nora': fig(NORA, 270)}, show=['Nora', 'steel folding table'])
P['c2-look'] = entry('A', {'Nora': fig(NORA, N_FACE)}, show=A_SHOW, hide=A_HIDE)
P['c3-enter'] = entry('E', {'Dev': fig((1.6, 0.7), 20, (4.0, 2.0), 20), 'Nora': fig(NORA, 270)}, show=['glass front door', 'Dev'], hide=['washing machine 7'])
P['c4-tokens-offer'] = entry('A', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)}, show=A_SHOW, hide=A_HIDE, reposition=True)
P['c5-thank'] = entry('B', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)}, show=B_SHOW, hide=B_HIDE)
P['c6-tokens'] = entry('I1', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)})
P['c7-scarf'] = entry('I2', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)}, show=['washing machine 7'])
P['c8-just-one'] = entry('A', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)}, show=A_SHOW, hide=A_HIDE)
P['c9-smells'] = entry('B', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)}, show=B_SHOW, hide=B_HIDE)
P['c10-understands'] = entry('A', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)}, show=A_SHOW, hide=A_HIDE)
P['c11-cold-slow'] = entry('A', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)}, show=A_SHOW, hide=A_HIDE)
P['c12-always'] = entry('B', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)}, show=B_SHOW, hide=B_HIDE)
P['c13-drum'] = entry('I2', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)}, show=['washing machine 7'])
P['c14-wait'] = entry('A', {'Nora': fig(NORA, N_FACE), 'Dev': fig(DEV, D_FACE)}, show=A_SHOW, hide=A_HIDE)
P['c15-wait-wide'] = entry('W', {'Nora': fig((5.0, 3.55), 90), 'Dev': fig((5.7, 3.55), 90)}, show=['Nora', 'Dev'], reposition=True)
story['plan'] = {
    'units': 'metres; x east, y north, z up; origin at the laundromat\'s south-west corner; facing in compass degrees (0 east, 90 north, 180 west, 270 south)',
    'room': {'x': [0.0, 8.0], 'y': [0.0, 5.0], 'z': 2.8},
    'features': [{'name': n, 'box': b, 'color': c} for n, b, c in FEAT],
    'figures': {'Nora': {'height': 1.65, 'pose': 'standing', 'color': '#d9382b'}, 'Dev': {'height': 1.8, 'pose': 'standing', 'color': '#2f5fd0'}},
    'shots': P,
}

if __name__ == '__main__':
    out = Path(__file__).with_name('directed-story.json')
    out.write_text(json.dumps(story, indent=1, ensure_ascii=False), encoding='utf-8')
    from magicdrama.audiofirst.blocking import check_blocking
    from magicdrama.audiofirst.directed import directed_prompt, validate_directed
    probs = check_blocking(story)
    print('blocking problems:', len(probs))
    for p in probs:print(' -', p)
    try:
        print('validate:', validate_directed(story))
        print('prompt chars:', [len(directed_prompt(story, i)) for i in range(len(SH))])
    except ValueError as e:
        print(e)
