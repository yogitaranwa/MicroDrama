"""Studio: from a short brief to a reviewed, validated, priced director's script. No credits are spent here.

    brief (idea, environment or none, number of characters, length)
      -> LLM drafts a small *story pack* (characters, room features, shots with lines, what everyone is doing)
      -> checked and repaired in a loop (the LLM is shown exactly what is wrong)
      -> code, not the LLM, does the geometry: floor plan in metres, camera set-ups, marks, framing, chained first frames
      -> the same validators the pipeline uses (blocking, activity, speech length, prompt budget) must pass
      -> review pack for the user: script, floor plan, what each camera sees, price quote, approval hash.

The LLM never writes coordinates or prompts: weak or local models are good at story and bad at geometry, so the split is deliberate.
The LLM is a small interface (`chat(system, user) -> str`), so a local model today and an API model later are one-line swaps.
First build limits: exactly two on-screen characters; one closed room; 4-second shots; production (rendering) is a later stage.
"""
import hashlib
import json
import math
import re
from pathlib import Path

from .blocking import check_blocking, render_floor_plan, render_layout
from .directed import (PROMPT_SOFT_LIMIT, IDLE, directed_prompt, first_frame_plan, plan_directed, render_script_markdown, validate_directed)
from .native_plan import speech_seconds

SHOT_SECONDS = 4
MAX_WORDS = 9
ROOM = {'x': [0.0, 8.0], 'y': [0.0, 5.0], 'z': 2.8}
KINDS = {  # kind -> (width along the wall, depth into the room, z0, z1, default colour)
    'machine': (0.8, 0.7, 0.0, 1.0, '#e8e8e8'), 'furniture': (1.2, 0.6, 0.0, 0.85, '#9a7b55'), 'window': (1.8, 0.06, 0.9, 2.2, '#5f7fa8'),
    'door': (1.0, 0.06, 0.0, 2.1, '#7a5a3a'), 'sign': (0.9, 0.06, 1.6, 2.1, '#f0f0f0'), 'screen': (0.9, 0.06, 1.0, 1.6, '#3a6fd0'),
    'shelf': (1.2, 0.35, 0.0, 1.9, '#8a7a60'), 'appliance': (0.9, 0.7, 0.0, 1.8, '#b8b8c0'), 'plant': (0.5, 0.5, 0.0, 1.2, '#4a8a4a')}
WALLS = ('north', 'south', 'east', 'west')
POSITIONS = {'left': 0.2, 'centre': 0.5, 'right': 0.8}
BEAT_TYPES = ('wide', 'entrance', 'dialogue', 'insert')
P1_MARK, P2_MARK = (3.4, 3.3), (4.6, 3.3)
CENTRE = [3.2, 1.7, 0.0, 4.8, 2.5, 0.85]  # the piece of furniture between and in front of the two people
DOOR_MARK = (1.8, 1.3)


# ---------------------------------------------------------------- the LLM interface
class OllamaLLM:
    """A local model through Ollama's chat API (JSON mode). `http` is injectable for tests."""
    def __init__(self, model, host='http://127.0.0.1:11434', http=None, temperature=0.7):
        self.model, self.host, self.temperature = model, host.rstrip('/'), temperature
        if http is None:
            import requests
            http = requests.Session()
        self.http = http

    def installed(self):
        r = self.http.get(self.host + '/api/tags', timeout=10);r.raise_for_status()
        return [m['name'] for m in r.json().get('models', [])]

    def chat(self, system, user):
        r = self.http.post(self.host + '/api/chat', json={'model': self.model, 'format': 'json', 'stream': False, 'options': {'temperature': self.temperature},
                                                           'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}, timeout=900)
        r.raise_for_status()
        return r.json()['message']['content']


class ScriptedLLM:
    """Returns prepared replies in order (tests, and replaying a saved draft). Records what it was asked."""
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def chat(self, system, user):
        self.calls.append((system, user))
        if not self.replies:raise RuntimeError('ScriptedLLM has no more replies')
        r = self.replies.pop(0)
        return r if isinstance(r, str) else json.dumps(r)


def parse_json(text):
    """The first JSON object in a model reply, tolerating code fences and chatter around it."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
    try:
        return json.loads(text)
    except ValueError:
        a, b = text.find('{'), text.rfind('}')
        if a < 0 or b <= a:raise ValueError('The model did not return a JSON object')
        return json.loads(text[a:b + 1])


# ---------------------------------------------------------------- brief
def check_brief(brief):
    problems = []
    if not str(brief.get('idea', '')).strip():problems.append('brief.idea is missing: say what the story is about')
    n = brief.get('characters', 2)
    if n != 2:problems.append(f'brief.characters is {n}: this first build supports exactly 2 on-screen characters')
    if not 20 <= int(brief.get('seconds', 60)) <= 120:problems.append('brief.seconds must be between 20 and 120')
    if problems:raise ValueError('Brief problems:\n- ' + '\n- '.join(problems))
    return {'idea': brief['idea'].strip(), 'environment': str(brief.get('environment', '')).strip(), 'characters': 2, 'seconds': int(brief.get('seconds', 60)),
            'tone': str(brief.get('tone', 'quiet, naturalistic drama')).strip(), 'names': list(brief.get('names', [])), 'title': brief.get('title', '')}


def shots_wanted(brief):
    return max(5, round(brief['seconds'] / SHOT_SECONDS))


# ---------------------------------------------------------------- prompts
SYSTEM = """You are a screenwriter and film director writing a short micro-drama that will be shot as a series of {sec}-second video clips in ONE closed room with exactly TWO people.
Answer with ONE JSON object only. Rules you must follow:
- Two characters. Give each a name, a one-sentence look (age, hair, build), a wardrobe (clothes that never change), and a voice (age, tone, pace).
- The room is a single closed room 8 m wide (west to east) and 5 m deep (south to north). The two people stand in the middle talking, one near the west side, one near the east side. Behind the first person is the WEST wall, behind the second is the EAST wall, so put the most recognisable features on the west and east walls. List 4 to 8 features: name, wall (north|south|east|west), position (left|centre|right), kind (machine|furniture|window|door|sign|screen|shelf|appliance|plant), colour as #rrggbb. Also give center_piece: the piece of furniture between the two people (a table, counter or desk).
- "beats" are the shots in order, exactly {shots} of them. Types: "wide" (whole room, no speech; use it first and last), "entrance" (the second character comes in: who, from, why, then), "dialogue" (speaker, line, doing, emotion), "insert" (a silent close-up of an object or hands: subject must be one feature name or "center_piece", text).
- A dialogue line is at most {words} words, spoken by one person, with no pauses inside it. Do not use ellipses.
- Nobody is ever idle. Every dialogue beat has "doing": an object mapping the speaker's name to what they are busy with while they talk (a task: folding, stirring, typing, cleaning, reading; never "standing" or "waiting"). An entrance gives a reason for coming in and the first thing they do on arrival.
- Show, don't tell: actions the camera can see. The ending leaves a question the viewer wants answered.
Schema: {{"title": str, "logline": str, "hook_title": str, "end_card": str, "characters": [{{"name","look","wardrobe","voice"}}, {{...}}],
 "environment": {{"name": str, "description": str, "lighting": str, "features": [{{"name","wall","position","kind","colour"}}], "center_piece": {{"name","kind","colour"}}}},
 "beats": [{{"type":"wide","text":str,"doing":{{name:task}}}}, {{"type":"entrance","who":name,"from":str,"why":str,"then":str}}, {{"type":"dialogue","speaker":name,"line":str,"doing":{{name:task}},"emotion":str}}, {{"type":"insert","subject":str,"text":str}}]}}"""


def draft_request(brief):
    system = SYSTEM.format(sec=SHOT_SECONDS, shots=shots_wanted(brief), words=MAX_WORDS)
    env = (f"Environment given by the user (use it): {brief['environment']}" if brief['environment'] else
           'No environment was given: invent one small closed room that suits the story and make it specific and recognisable.')
    names = f"Character names to use: {', '.join(brief['names'])}." if brief['names'] else 'Choose short original character names.'
    user = f"Story idea: {brief['idea']}\n{env}\nTone: {brief['tone']}.\nCharacters: 2. {names}\nTarget length: {brief['seconds']} seconds ({shots_wanted(brief)} shots)."
    return system, user


KIND_WORDS = {'furniture': ('desk', 'table', 'counter', 'chair', 'bed', 'sofa', 'couch', 'bench', 'cabinet', 'stool', 'workbench', 'bookcase'),
              'appliance': ('stove', 'oven', 'fridge', 'heater', 'radio', 'clock', 'lamp', 'kettle', 'fireplace', 'machine'), 'window': ('window', 'porthole', 'skylight'),
              'door': ('door', 'doorway', 'gate', 'hatch'), 'sign': ('sign', 'poster', 'map', 'picture', 'painting', 'chart', 'notice', 'calendar'), 'shelf': ('shelf', 'rack', 'shelves'),
              'screen': ('screen', 'monitor', 'television', 'tv'), 'plant': ('plant', 'tree', 'flowers')}


def normalise_pack(pack):
    """Safe, mechanical clean-ups of what small models get wrong, so the repair budget is spent on real story problems:
    an unknown feature kind is mapped from its name (a "Desk" is furniture), ellipses inside lines become full stops, odd wall/position casing is lowered."""
    if not isinstance(pack, dict):return pack
    for f in (pack.get('environment') or {}).get('features') or []:
        if not isinstance(f, dict):continue
        for k in ('wall', 'position', 'kind'):
            if isinstance(f.get(k), str):f[k] = f[k].strip().lower()
        if f.get('kind') not in KINDS:
            name = str(f.get('name', '')).lower()
            f['kind'] = next((k for k, ws in KIND_WORDS.items() if any(w in name for w in ws)), 'furniture')
    cp = (pack.get('environment') or {}).get('center_piece')
    if isinstance(cp, dict) and cp.get('kind') not in KINDS:cp['kind'] = 'furniture'
    for b in pack.get('beats') or []:
        if isinstance(b, dict) and isinstance(b.get('line'), str):b['line'] = re.sub(r'\s*(\.{2,}|…)\s*', '. ', b['line']).strip()
    return pack


def snap_insert_subjects(pack):
    """An insert must be on a real feature. A subject the model made up snaps to the feature sharing a word with it, else the centre piece."""
    names = [str(f.get('name', '')) for f in (pack.get('environment') or {}).get('features') or [] if isinstance(f, dict)]
    for b in pack.get('beats') or []:
        if isinstance(b, dict) and b.get('type') == 'insert':
            sub = str(b.get('subject', '')).strip()
            if sub == 'center_piece' or sub.lower() in [n.lower() for n in names]:continue
            words = {w for w in re.findall(r'[a-z]+', sub.lower()) if len(w) > 2}
            hit = next((n for n in names if words & set(re.findall(r'[a-z]+', n.lower()))), None)
            b['subject'] = hit or 'center_piece'
    return pack


def shorten_long_lines(pack, llm, tries=2):
    """A small focused request per over-long line (small models cannot count words inside a big script, but can rewrite one sentence)."""
    for b in pack.get('beats') or []:
        if not (isinstance(b, dict) and b.get('type') == 'dialogue' and isinstance(b.get('line'), str)):continue
        for _ in range(tries):
            if len(b['line'].split()) <= MAX_WORDS:break
            try:
                reply = parse_json(llm.chat('You rewrite one line of film dialogue. Answer with one JSON object: {"line": "..."}.',
                                            f'Rewrite this line in {MAX_WORDS - 1} words or fewer, same meaning, same voice, no ellipses: "{b["line"]}"'))
                new = str(reply.get('line', '')).strip()
            except (ValueError, AttributeError):
                continue
            if new:b['line'] = re.sub(r'\s*(\.{2,}|…)\s*', '. ', new).strip()
    return pack


# ---------------------------------------------------------------- checking the pack (the LLM's part)
def check_pack(pack, brief):
    p = []
    if not isinstance(pack, dict):return ['the reply is not a JSON object']
    for k in ('title', 'logline', 'hook_title', 'end_card'):
        if not str(pack.get(k, '')).strip():p.append(f'{k} is missing')
    chars = pack.get('characters') or []
    names = [c.get('name', '') for c in chars if isinstance(c, dict)]
    if len(chars) != 2 or len(set(names)) != 2 or not all(names):p.append('exactly two characters with different names are required')
    for c in chars:
        for k in ('look', 'wardrobe', 'voice'):
            if not str(c.get(k, '')).strip():p.append(f"character {c.get('name', '?')}: {k} is missing")
    env = pack.get('environment') or {}
    for k in ('name', 'description', 'lighting'):
        if not str(env.get(k, '')).strip():p.append(f'environment.{k} is missing')
    feats = env.get('features') or []
    if not 3 <= len(feats) <= 10:p.append('environment.features needs 3 to 10 features')
    seen = set()
    for f in feats:
        nm = str(f.get('name', '')).strip()
        if not nm or nm.lower() in seen:p.append(f'feature name "{nm}" is empty or repeated')
        seen.add(nm.lower())
        if f.get('wall') not in WALLS:p.append(f'feature "{nm}": wall must be one of {WALLS}')
        if f.get('position') not in POSITIONS:p.append(f'feature "{nm}": position must be left, centre or right')
        if f.get('kind') not in KINDS:p.append(f'feature "{nm}": kind must be one of {sorted(KINDS)}')
    if not str((env.get('center_piece') or {}).get('name', '')).strip():p.append('environment.center_piece.name is missing')
    if not any(f.get('wall') in ('west', 'east') for f in feats):p.append('put at least one feature on the west or east wall: those are the backdrops behind the two people')
    beats, want = pack.get('beats') or [], shots_wanted(brief)
    if abs(len(beats) - want) > 1:p.append(f'beats has {len(beats)} shots; {want} were asked for')
    if beats and beats[0].get('type') != 'wide':p.append('the first beat must be type "wide"')
    if beats and beats[-1].get('type') not in ('wide', 'dialogue'):p.append('the last beat must be "wide" or "dialogue"')
    spoken, entrances = 0, 0
    for i, b in enumerate(beats, 1):
        t, tag = b.get('type'), f'beat {i}'
        if t not in BEAT_TYPES:p.append(f'{tag}: type must be one of {BEAT_TYPES}');continue
        if t == 'dialogue':
            spoken += 1
            line = str(b.get('line', '')).strip()
            if b.get('speaker') not in names:p.append(f'{tag}: speaker must be one of {names}')
            if not line:p.append(f'{tag}: line is empty')
            elif len(line.split()) > MAX_WORDS:p.append(f'{tag}: the line "{line}" is {len(line.split())} words; at most {MAX_WORDS}')
            elif '...' in line or '…' in line:p.append(f'{tag}: no ellipses or pauses inside a line')
            doing = (b.get('doing') or {}).get(b.get('speaker'), '')
            if not str(doing).strip():p.append(f'{tag}: doing.{b.get("speaker")} is missing; say what the speaker is busy with')
            elif IDLE.search(str(doing)):p.append(f'{tag}: "{doing}" is not a task; the speaker must be doing something')
        elif t == 'entrance':
            entrances += 1
            for k in ('who', 'from', 'why', 'then'):
                if not str(b.get(k, '')).strip():p.append(f'{tag}: entrance needs {k}')
            if b.get('who') not in names:p.append(f'{tag}: who must be one of {names}')
            elif IDLE.search(str(b.get('then', ''))):p.append(f'{tag}: entrance.then must be a task')
        elif t == 'insert':
            sub = str(b.get('subject', '')).strip()
            if sub != 'center_piece' and sub.lower() not in seen:p.append(f'{tag}: insert subject must be "center_piece" or the name of a feature ({sorted(seen)})')
        elif t == 'wide' and not str(b.get('text', '')).strip():p.append(f'{tag}: wide needs text')
    if spoken < 4:p.append('at least 4 dialogue beats are needed')
    if entrances > 1:p.append('at most one entrance')
    return p


def draft_pack(brief, llm, max_repairs=5):
    """Ask the LLM for a pack, show it every problem found, repeat. Returns (pack, history)."""
    brief = check_brief(brief)
    system, user = draft_request(brief)
    history, reply = [], llm.chat(system, user)
    for attempt in range(max_repairs + 1):
        try:
            pack = snap_insert_subjects(normalise_pack(parse_json(reply)))
            shorten_long_lines(pack, llm)
            problems = check_pack(pack, brief)
        except ValueError as e:
            pack, problems = None, [str(e)]
        history.append({'attempt': attempt, 'problems': problems})
        if not problems:return pack, history
        if attempt == max_repairs:break
        reply = llm.chat(system, user + '\n\nYour previous answer had these problems. Return the corrected JSON object only:\n- ' + '\n- '.join(problems)
                         + ('\n\nPrevious answer:\n' + json.dumps(pack) if pack else ''))
    raise ValueError(f'The LLM could not produce a valid story pack after {max_repairs} repairs. Last problems:\n- ' + '\n- '.join(history[-1]['problems']))


# ---------------------------------------------------------------- code does the geometry
def _unit(a, b):
    d = (b[0] - a[0], b[1] - a[1]);n = math.hypot(*d) or 1
    return (d[0] / n, d[1] / n)


def _facing(frm, to):
    return round(math.degrees(math.atan2(to[1] - frm[1], to[0] - frm[0])) % 360)


def feature_box(feat, index_on_wall):
    w, depth, z0, z1, _ = KINDS[feat['kind']]
    frac = POSITIONS[feat['position']] + 0.13 * (index_on_wall % 3 - (1 if index_on_wall else 0)) * (1 if index_on_wall else 0)
    rx, ry = ROOM['x'][1], ROOM['y'][1]
    wall = feat['wall']
    if wall in ('north', 'south'):
        c = min(max(frac * rx, w / 2 + 0.1), rx - w / 2 - 0.1)
        y0, y1 = (ry - depth, ry) if wall == 'north' else (0.0, depth)
        return [round(c - w / 2, 2), y0, z0, round(c + w / 2, 2), y1, z1]
    c = min(max(frac * ry, w / 2 + 0.1), ry - w / 2 - 0.1)
    x0, x1 = (0.0, depth) if wall == 'west' else (rx - depth, rx)
    return [x0, round(c - w / 2, 2), z0, x1, round(c + w / 2, 2), z1]


def build_plan(pack):
    names = [c['name'] for c in pack['characters']]
    p1, p2 = names
    env = pack['environment']
    feats, per_wall = [], {}
    for f in env['features']:
        k = (f['wall'], f['position'])
        feats.append({'name': f['name'], 'box': feature_box(f, per_wall.get(k, 0)), 'color': f.get('colour') or KINDS[f['kind']][4]})
        per_wall[k] = per_wall.get(k, 0) + 1
    cp = env['center_piece']
    feats.append({'name': cp['name'], 'box': CENTRE, 'color': cp.get('colour') or '#a0a0a8'})
    cam_a = [round(P2_MARK[0] + 1.1, 2), 2.8, 1.55]   # behind person 2, looking at person 1 (west wall behind them)
    cam_b = [round(P1_MARK[0] - 1.1, 2), 2.8, 1.55]   # behind person 1, looking at person 2 (east wall behind them)
    tgt_a, tgt_b = [P1_MARK[0], P1_MARK[1], 1.5], [P2_MARK[0], P2_MARK[1], 1.5]
    face1, face2 = _facing(P1_MARK, cam_a), _facing(P2_MARK, cam_b)
    cams = {'A': (cam_a, tgt_a, 35), 'B': (cam_b, tgt_b, 35), 'W': ([0.4, 0.3, 1.55], [4.2, 3.0, 1.1], 24)}

    def fig(pos, f, pos_e=None, f_e=None):
        return {'start': {'pos': list(pos), 'facing': f}, 'end': {'pos': list(pos_e or pos), 'facing': f if f_e is None else f_e}}

    def entry(cam, figures, show=None, reposition=False, drift=0.05):
        pos, tgt, lens = cam
        end_pos = [round(pos[0] + drift * (tgt[0] - pos[0]), 2), round(pos[1] + drift * (tgt[1] - pos[1]), 2), pos[2]]
        e = {'camera': {'lens': lens, 'start': {'pos': pos, 'target': tgt}, 'end': {'pos': end_pos, 'target': tgt}}, 'figures': figures,
             'must_show': {'start': show or [], 'end': show or []}, 'must_not_show': {'start': [], 'end': []}}
        if reposition:e['reposition'] = True
        return e

    plan = {'units': "metres; x east, y north, z up; origin at the room's south-west corner; facing in compass degrees (0 east, 90 north, 180 west, 270 south)",
            'room': ROOM, 'features': feats,
            'figures': {p1: {'height': 1.65, 'pose': 'standing', 'color': '#d9382b'}, p2: {'height': 1.8, 'pose': 'standing', 'color': '#2f5fd0'}}, 'shots': {}}
    return plan, {'names': names, 'cams': cams, 'faces': (face1, face2), 'fig': fig, 'entry': entry}


def insert_camera(plan, subject, cp_name):
    target = next(f for f in plan['features'] if f['name'].lower() == (cp_name if subject == 'center_piece' else subject).lower())
    b = target['box']
    c = [(b[0] + b[3]) / 2, (b[1] + b[4]) / 2, min(max((b[2] + b[5]) / 2, 0.9), 1.3)]
    d = _unit(c, (4.0, 2.5))
    pos = [round(c[0] + d[0] * 0.9, 2), round(c[1] + d[1] * 0.9, 2), min(c[2] + 0.25, 1.5)]
    return (pos, [round(v, 2) for v in c], 50)


def compile_story(pack, brief):
    """The directed-story JSON the rest of the pipeline already consumes, built from the LLM's pack plus computed geometry."""
    brief = check_brief(brief)
    plan, g = build_plan(pack)
    p1, p2 = g['names']
    cams, (face1, face2), fig, entry = g['cams'], g['faces'], g['fig'], g['entry']
    chars = {c['name']: c for c in pack['characters']}
    env = pack['environment']
    cp = env['center_piece']['name']
    west = [f['name'] for f in env['features'] if f['wall'] == 'west']
    east = [f['name'] for f in env['features'] if f['wall'] == 'east']
    look = env['lighting'].rstrip('.') + '; the same in every shot'
    wardrobe = ' '.join(f"{n}: {chars[n]['wardrobe']}." for n in g['names'])
    bible = {
        'format': '16:9, 24 fps, 35 mm lens equivalent, shallow depth of field, soft natural film grain, restrained naturalistic colour, no stylised grading, handheld-steady realism',
        'set': f"{env['description'].rstrip('.')}; features: " + '; '.join(f"{f['name']} on the {f['wall']} wall" for f in env['features']) + f"; {cp} in the middle",
        'geography': (f"{p1} stands on the west side of {cp}, {p2} on the east side, about a metre apart, and both stay on those spots. Shots from {p2}'s side look west at {p1}: "
                      f"behind {p1} is the west wall" + (' with ' + ', '.join(west) if west else '') + f". Shots from {p1}'s side look east at {p2}: behind {p2} is the east wall"
                      + (' with ' + ', '.join(east) if east else '') + '. Never swap the two backgrounds. Keep every object where it is.'),
        'lighting': f'The light never changes: {look}. Nobody touches a light switch.',
        'performance': f"Naturalistic and restrained, like a film: micro-expressions, small hand movements, no grins, no wide-eyed shock, no big gestures. {brief['tone']}.",
        'wardrobe_props': wardrobe,
        'set_short': f"{env['name']}: " + ', '.join(f"{f['name']} ({f['wall']})" for f in env['features']) + f", {cp} in the middle",
        'geography_short': f"{p1} stands west of {cp}, {p2} east of it, a metre apart. {p2}'s side looks west (west wall behind {p1}); {p1}'s side looks east (east wall behind {p2}). Never swap backgrounds.",
        'lighting_rule': f'Unchanging light: {look}. No switch is touched.',
        'wardrobe_short': wardrobe,
        'performance_short': 'Naturalistic and restrained: micro-expressions only, no grins, no shock, no big gestures.'}
    voices = {n: chars[n]['voice'] for n in g['names']}
    shots, plan_shots = [], plan['shots']
    entrance = next((b for b in pack['beats'] if b['type'] == 'entrance'), None)
    present = {p1: True, p2: not entrance}
    for i, b in enumerate(pack['beats'], 1):
        sid = f"s{i:02d}-{b['type']}"
        base = {'id': sid, 'seconds': SHOT_SECONDS, 'lighting': 'Unchanging, as in every shot.', 'activity': {}, 'sound': {'ambience': voices and env['name'] + ' ambience: a quiet room tone', 'effects': [], 'dialogue': []}}
        t = b['type']
        if t == 'wide':
            figs = {p1: fig(P1_MARK, face1)}
            if present[p2]:figs[p2] = fig(P2_MARK, face2)
            plan_shots[sid] = entry(cams['W'], figs, show=[p1], drift=0.05)
            doing = b.get('doing') or {}
            base.update(title=f'Wide {i}', cast=[n for n in g['names'] if n in figs], intent=b['text'], size='wide', angle='eye level', move='slow push in about 5%', lens='24 mm',
                        start=f"From a corner of the room looking across it: {b['text']}", end='The room as before, the people where they were.',
                        bts=[(0.0, 1.5, b['text']), (1.5, 3.0, 'The people go on with what they are doing; the camera pushes in slowly.'), (3.0, 4.0, 'Nobody speaks.')], perf='Quiet and unhurried.',
                        activity={n: doing.get(n) or 'busy with a small task in the room' for n in figs}, effects=[])
        elif t == 'entrance':
            who = b['who']
            other = p1 if who == p2 else p2
            path_end = P2_MARK if who == p2 else P1_MARK
            figs = {who: fig(DOOR_MARK, _facing(DOOR_MARK, path_end), path_end, _facing(DOOR_MARK, path_end)), other: fig(P1_MARK if other == p1 else P2_MARK, face1 if other == p1 else face2)}
            plan_shots[sid] = entry((cams['W'][0], cams['W'][1], 24), figs, show=[who], drift=0.03)
            present[who] = True
            base.update(title=f'{who} comes in', cast=[who], intent=f"{who} comes in from {b['from']} because {b['why']}.", size='wide', angle='eye level', move='slow drift about 3%', lens='24 mm',
                        start=f"From the far corner: {who} just inside {b['from']}, {other} busy in the middle of the room.", end=f"{who} has crossed the room and stands beside {cp}.",
                        bts=[(0.0, 1.0, f"{who} arrives at {b['from']}."), (1.0, 3.0, f"{who} crosses the room toward the middle: {b['then']}."), (3.0, 4.0, f"{who} reaches their place beside {cp}. Nobody speaks.")],
                        perf='Natural and purposeful.', activity={who: b['then']}, effects=['footsteps'],
                        arrival={who: {'from': b['from'], 'to': 'the middle of the room', 'why': b['why'], 'then': b['then']}})
        elif t == 'dialogue':
            sp = b['speaker']
            cam, face = (cams['A'], face1) if sp == p1 else (cams['B'], face2)
            other = p2 if sp == p1 else p1
            figs = {n: fig(P1_MARK if n == p1 else P2_MARK, face1 if n == p1 else face2) for n in g['names'] if present[n]}
            plan_shots[sid] = entry(cam, figs, show=[sp], drift=0.04)
            doing = (b.get('doing') or {}).get(sp, 'working with their hands')
            base.update(title=f"{sp}: \"{b['line']}\"", cast=[sp], intent=f"{sp} speaks; {b.get('emotion', 'quietly')}.", size='medium close-up', angle='eye level', move='slow push in about 4%', lens='35 mm',
                        start=f"{sp} in the middle of the frame, close, {doing}; {other}'s shoulder soft in the foreground.", end=f'{sp} has said the line and holds the look.',
                        bts=[(0.0, 1.0, f"{sp} is {doing} and turns toward {other}."), (1.0, 3.0, f"{sp} says the line, {b.get('emotion', 'quietly')}."), (3.0, 4.0, f'{sp} holds the look and waits.')],
                        perf=b.get('emotion', 'quiet and restrained'), activity={sp: doing}, effects=['a faint breath'])
            base['sound']['dialogue'] = [{'speaker': sp, 'voice': voices[sp], 'line': b['line'].strip(), 'delivery': b.get('emotion', 'quiet')}]
        else:  # insert
            pos, tgt, lens = insert_camera(plan, b['subject'], cp)
            figs = {n: fig(P1_MARK if n == p1 else P2_MARK, face1 if n == p1 else face2) for n in g['names'] if present[n]}
            plan_shots[sid] = entry((pos, tgt, lens), figs, drift=0.01)
            base.update(title=f"Close on {b['subject']}", cast=[], intent=b['text'], size='close-up insert', angle='eye level', move='tiny drift in about 1%', lens='50 mm',
                        start=f"EXTREME CLOSE-UP filling the whole frame, only {b['subject'] if b['subject'] != 'center_piece' else cp} (no person, no face and no hands anywhere in the frame): {b['text']}", end='The detail as before, still with no person in frame.',
                        bts=[(0.0, 1.5, b['text']), (1.5, 3.0, 'The detail changes slightly as the scene moves on.'), (3.0, 4.0, 'Nobody speaks and nobody walks into frame.')], perf='No people in the shot, only the object.', activity={}, effects=['a small sound from the object'])
        shots.append({'id': sid, 'title': base['title'], 'seconds': SHOT_SECONDS, 'cast': base['cast'], 'intent': base['intent'], 'start_state': base['start'], 'end_state': base['end'],
                      'camera': {'size': base['size'], 'angle': base['angle'], 'movement': base['move'], 'lens': base['lens']}, 'lighting': base['lighting'],
                      'beats': [{'t0': a, 't1': c, 'text': tx} for a, c, tx in base['bts']], 'performance': base['perf'],
                      'sound': {'ambience': base['sound']['ambience'], 'effects': base['effects'], 'dialogue': base['sound']['dialogue']},
                      'keyframe': base['start'], 'activity': base['activity'], **({'arrival': base['arrival']} if 'arrival' in base else {})})
    story = {'title': pack['title'], 'logline': pack['logline'], 'aspect': '16:9', 'rules': {'chain': True, 'activity': True}, 'bible': bible, 'voices': voices,
             'plate': {'id': 'room-plate', 'file': 'room-plate.png'}, 'portraits': {n: n.lower().replace(' ', '-') + '-master.png' for n in g['names']}, 'shots': shots,
             'hook_title': pack['hook_title'], 'end_card': pack['end_card'], 'plan': plan}
    return story


def assets_to_make(pack, brief):
    """The reference images production will generate first (the room plate, a portrait each), as prompts the user can read now."""
    env, style = pack['environment'], '16:9 photoreal cinematic still, 35 mm lens, shallow depth of field, soft film grain, restrained colour, no text, no watermark. '
    out = {'room-plate': style + f"An EMPTY room, no people. {env['description']} Features: " + '; '.join(f"{f['name']} on the {f['wall']} wall" for f in env['features']) + f". {env['lighting']}"}
    for c in pack['characters']:
        out[c['name'].lower().replace(' ', '-') + '-master'] = style + f"Full-body portrait of {c['name']}, {c['look']}. Wearing {c['wardrobe']}. Calm neutral expression, mouth closed, neutral grey studio background, even soft light."
    return out


def validate_compiled(story):
    """Everything the pipeline checks before spending: raises ValueError listing every problem."""
    validate_directed(story)
    over = [(s['id'], len(directed_prompt(story, i))) for i, s in enumerate(story['shots']) if len(directed_prompt(story, i)) > PROMPT_SOFT_LIMIT]
    if over:raise ValueError('Prompts over the 2500-character limit: ' + ', '.join(f'{a} ({b})' for a, b in over))
    return True


# ---------------------------------------------------------------- the review pack
def pack_hash(story):
    return hashlib.sha256(json.dumps(story, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def write_review(out, story, pack, brief, model='kling-3.0'):
    """Writes everything the user needs to decide: the script, floor plan, what the two cameras see, assets, the price and the approval hash."""
    out = Path(out)
    (out / 'views').mkdir(parents=True, exist_ok=True)
    priced = plan_directed(story, model, '720p')
    ff = first_frame_plan(story)
    n_images = sum(1 for p in ff if p['mode'] != 'continue') + 1 + len(story['portraits'])
    images = 50 * n_images
    music = max(15, len(story['shots']) * SHOT_SECONDS)
    quote = {'video_credits': priced['video_credits'], 'image_credits_estimate': images, 'music_credits': music, 'model': model,
             'total_credits': priced['video_credits'] + images + music, 'note': 'Quoted before approval; production re-verifies quotes and enforces a hard cap. Re-render reserve is not included.'}
    sample = {}
    for i, s in enumerate(story['shots']):
        if s['cast'] and s['sound']['dialogue'] and len(sample) < 2 and s['cast'][0] not in sample:
            sample[s['cast'][0]] = s['id']
    for who, sid in sample.items():
        render_layout(story['plan'], sid, 'start', size=(960, 540)).save(out / 'views' / f'camera-{who}.png')
    first = story['shots'][0]['id']
    render_floor_plan(story['plan'], first).save(out / 'views' / 'floor-plan.png')
    md = [render_script_markdown(story), '', '## First-frame chain', '']
    md += [f"- {p['id']}: {p['mode']}" + (f" (from {p['from_shot']})" if p['from_shot'] else '') for p in ff]
    md += ['', '## Reference images production will make first', ''] + [f'- **{k}**: {v}' for k, v in assets_to_make(pack, brief).items()]
    md += ['', '## Price', '', json.dumps(quote, indent=2), '', '## Approve', '',
           f"Read the script above, then run `python audiofirst.py studio approve --out {out} --max-credits <your cap>`. Approval is bound to this exact script (sha256 {pack_hash(story)[:16]}…).", '']
    (out / 'REVIEW.md').write_text('\n'.join(md), encoding='utf-8')
    (out / 'story.json').write_text(json.dumps(story, indent=1, ensure_ascii=False), encoding='utf-8')
    (out / 'pack.json').write_text(json.dumps(pack, indent=1, ensure_ascii=False), encoding='utf-8')
    (out / 'quote.json').write_text(json.dumps(quote, indent=1), encoding='utf-8')
    return {'review': str(out / 'REVIEW.md'), 'story': str(out / 'story.json'), 'quote': quote, 'story_sha256': pack_hash(story)}


def approve(out, max_credits, who='user'):
    """Records that the user accepted this exact script and spending cap. Production refuses a story whose hash differs."""
    out = Path(out)
    story = json.loads((out / 'story.json').read_text(encoding='utf-8'))
    quote = json.loads((out / 'quote.json').read_text(encoding='utf-8'))
    if max_credits < quote['total_credits']:raise ValueError(f"The cap {max_credits} is below the quote {quote['total_credits']}: raise the cap or shorten the film")
    rec = {'approved_by': who, 'story_sha256': pack_hash(story), 'max_credits': int(max_credits), 'quote': quote['total_credits']}
    (out / 'approval.json').write_text(json.dumps(rec, indent=1), encoding='utf-8')
    return rec


def check_approval(out):
    out = Path(out)
    if not (out / 'approval.json').exists():raise ValueError('This script is not approved yet: read REVIEW.md, then run `studio approve --out ... --max-credits N`')
    rec = json.loads((out / 'approval.json').read_text(encoding='utf-8'))
    story = json.loads((out / 'story.json').read_text(encoding='utf-8'))
    if rec['story_sha256'] != pack_hash(story):raise ValueError('The script changed after it was approved: review and approve it again')
    return rec


def draft(brief, llm, out, max_repairs=5, model='kling-3.0'):
    """The whole draft stage: brief -> pack -> story -> validation -> review pack on disk."""
    brief = check_brief(brief)
    pack, history = draft_pack(brief, llm, max_repairs)
    story = compile_story(pack, brief)
    validate_compiled(story)
    result = write_review(out, story, pack, brief, model)
    Path(out, 'draft-history.json').write_text(json.dumps(history, indent=1), encoding='utf-8')
    return {**result, 'repairs': len(history) - 1}
