"""Director-style shot planning: a visual bible, a floor plan, motivated light, timed action beats, a camera move and restrained acting for
every shot, plus continuity from the previous shot (its last frame as the next first frame, and a written "previous shot ended with" line).

Why: independent still-to-video shots with thin prompts gave a light that "just turns on", cuts that looked like two different films, no
camera movement and exaggerated acting. A real script says who does what and why, where the camera is and how it moves, what lights the
room and how each shot begins and ends. The same JSON feeds the prompts and a readable director's script.
"""
import math
import re

from .core import finite
from .native_mix import native_prompt, quote_native_video, FPS
from .native_plan import SET_LOCK, speech_seconds
from .blocking import camera_setup, check_blocking, framing_text

STATIC = re.compile(r'^\s*(static|locked|locked[- ]off|none|still|fixed)\b', re.I)
UNMOTIVATED = re.compile(r'\b(suddenly|automatically|by itself|on its own|magically|mysteriously)\b[^.]{0,50}\b(turns? on|comes? on|lights? up|switch(es)? on|opens?|closes?)\b', re.I)
LIGHT_CHANGE = re.compile(r'\b(light|lamp)\b[^.]{0,40}\b(comes?|turns?|switch(es)?|goes?|flicks?) on\b', re.I)
CAUSE = re.compile(r'\b(press(es|ed)?|flick(s|ed)?|switch plate|switch|toggle[sd]?)\b', re.I)
IDLE = re.compile(r'^\s*(stands?|standing|waits?|waiting|nothing|idle|just (stands?|standing|waits?)|looks? around|is present|there)\b', re.I)
PROMPT_SOFT_LIMIT = 2500  # kling-3.0 and veo3.1 accept 2500 characters of prompt text


def validate_directed(story):
    """Raises ValueError listing every problem a script supervisor would catch before a credit is spent."""
    problems = []
    bible = story.get('bible', {})
    for key in ('format', 'set', 'geography', 'lighting', 'performance', 'wardrobe_props'):
        if not str(bible.get(key, '')).strip():problems.append(f'bible.{key} is missing')
    shots = story.get('shots', [])
    if not shots:problems.append('no shots')
    portraits = story.get('portraits', {})
    for i, s in enumerate(shots):
        sid = s.get('id', f'#{i}')
        for key in ('title', 'intent', 'start_state', 'end_state', 'lighting', 'performance'):
            if not str(s.get(key, '')).strip():problems.append(f'{sid}: {key} is missing')
        cam = s.get('camera', {})
        for key in ('size', 'angle', 'movement', 'lens'):
            if not str(cam.get(key, '')).strip():problems.append(f'{sid}: camera.{key} is missing')
        if STATIC.search(str(cam.get('movement', ''))):problems.append(f'{sid}: the camera must move (a push, a pan, a tilt, a follow); a static frame is what made the first films look dead')
        if i == 0 and not s.get('keyframe'):problems.append(f'{sid}: the first shot needs a keyframe description')
        if i > 0 and not s.get('continues_previous') and not s.get('keyframe'):problems.append(f'{sid}: a shot that does not continue the previous frame needs a keyframe description')
        if i == 0 and s.get('continues_previous'):problems.append(f'{sid}: the first shot cannot continue a previous shot')
        for name in s.get('cast', []):
            if name not in portraits:problems.append(f'{sid}: cast member {name} has no portrait')
        seconds = float(s.get('seconds', 0))
        beats = s.get('beats', [])
        if not beats:problems.append(f'{sid}: no timed action beats')
        cursor = 0.0
        for b in beats:
            if abs(float(b['t0']) - cursor) > 0.25:problems.append(f"{sid}: beats leave a gap or overlap at {cursor:.1f}-{b['t0']} s")
            if float(b['t1']) <= float(b['t0']) or float(b['t1']) > seconds + 0.05:problems.append(f"{sid}: beat {b['t0']}-{b['t1']} s does not fit in {seconds} s")
            cursor = float(b['t1'])
        if beats and abs(cursor - seconds) > 0.6:problems.append(f'{sid}: beats end at {cursor:.1f} s but the shot is {seconds} s')
        action = ' '.join(b['text'] for b in beats)  # the cause must be in what the camera sees, not only in the lighting note
        if UNMOTIVATED.search(' '.join([str(s.get('intent', '')), str(s.get('lighting', '')), action])):problems.append(f'{sid}: something changes "suddenly/automatically": say who or what causes it')
        if LIGHT_CHANGE.search(action) and not CAUSE.search(action):problems.append(f'{sid}: the light changes but nothing in the action switches it; show the hand on the switch')
        for d in (s.get('sound') or {}).get('dialogue', []) or []:
            if speech_seconds(d['line']) > seconds:problems.append(f"{sid}: the line {d['line']!r} cannot be spoken in {seconds} s")
    if story.get('rules', {}).get('activity') and not problems:problems += check_activity(story)
    if 'plan' in story and not problems:problems += check_blocking(story)  # people cannot teleport, the camera must see what the shot needs and not what is behind it
    if problems:raise ValueError('Director script problems:\n- ' + '\n- '.join(problems))
    return True


def check_activity(story):
    """A film person is never idle and never just appears: everyone on screen has something they are doing (a task, not "stands" or "waits"),
    and a person who comes in or moves to a new place has a stated reason, a route and the first thing they do on arrival."""
    problems, plan, shots = [], story.get('plan'), story['shots']
    for i, s in enumerate(shots):
        sid, act = s['id'], s.get('activity', {})
        for name in s.get('cast', []):
            doing = str(act.get(name, '')).strip()
            if not doing:problems.append(f'{sid}: {name} is on screen with nothing to do; say what they are busy with (activity.{name})')
            elif IDLE.search(doing):problems.append(f'{sid}: {name} is "{doing}"; give them a task that explains why they are there, not standing or waiting')
        if not plan or i == 0:continue
        cur, prev = plan['shots'][sid], plan['shots'][shots[i - 1]['id']]
        for name, st in cur['figures'].items():
            was = prev['figures'].get(name)
            moved = was is None or math.dist(was['end']['pos'], st['start']['pos']) > 0.4
            if not moved:continue
            arr = s.get('arrival', {}).get(name)
            need = ('from', 'to', 'why', 'then')
            if not arr or any(not str(arr.get(k, '')).strip() for k in need):
                problems.append(f'{sid}: {name} appears in a new place; give arrival.{name} with from, to, why and then (the first thing they do there)')
            elif IDLE.search(str(arr['then'])):problems.append(f'{sid}: arrival.{name}.then must be a task, not standing or waiting')
    return problems


def first_frame_plan(story):
    """Where each shot's first frame comes from, so people carry over from the shot before instead of being re-invented:
    continue   same camera as the previous shot, the same people where they were: use that shot's real last frame directly (no image job);
    resume     an earlier shot used this same camera angle: its real last frame is the state of this angle when the story left it;
    build      a new angle: build the frame from the previous shot's real last frame, the room plate, the portraits and the layout guide."""
    shots, plan, out = story['shots'], story.get('plan'), []
    seen = {}
    for i, s in enumerate(shots):
        key = camera_setup(plan, s['id']) if plan else None
        prev = shots[i - 1] if i else None
        if i == 0:
            mode, src = 'build', None
        elif s.get('continues_previous'):
            mode, src = 'continue', prev['id']
        elif key is not None and prev and camera_setup(plan, prev['id']) == key and all(
                f in plan['shots'][prev['id']]['figures'] and math.dist(plan['shots'][prev['id']]['figures'][f]['end']['pos'], st['start']['pos']) <= 0.4
                for f, st in plan['shots'][s['id']]['figures'].items()):
            mode, src = 'continue', prev['id']
        elif key is not None and key in seen:
            mode, src = 'resume', seen[key]
        else:
            mode, src = 'build', prev['id'] if prev else None
        out.append({'id': s['id'], 'mode': mode, 'from_shot': src, 'previous': prev['id'] if prev else None})
        if key is not None:seen[key] = s['id']
    return out


# What the video prompt can lose first when it must fit the service's 2500 characters: the start image already carries the look,
# the wardrobe and the set, so those reminders go before anything about motion, camera, action, sound or continuity.
DROP_ORDER = ('wardrobe', 'format', 'set', 'geography', 'bible_performance', 'intent')


def directed_prompt(story, index, limit=PROMPT_SOFT_LIMIT):
    """One shot's full direction as a single prompt that fits `limit` characters, with the previous shot's ending stated."""
    bible, shots = story['bible'], story['shots']
    s, prev = shots[index], (shots[index - 1] if index else None)
    cam = s['camera']
    beats = ' '.join(f"{b['t0']:.1f}-{b['t1']:.1f} s: {b['text']}" for b in s['beats'])
    if s.get('continues_previous') and prev:
        continuity = f"This shot continues directly from the previous shot's last frame, which shows: {prev['end_state']}"
    else:
        continuity = (f"The previous shot ended with: {prev['end_state']} " if prev else '') + f"This shot begins with: {s['start_state']}"
    sections = {
        'intent': f"SHOT {index + 1} of {len(shots)}: {s['title']}. {s['intent']}",
        'set': f"SET: {bible.get('set_short', bible['set'])}.",
        'geography': f"GEOGRAPHY: {bible.get('geography_short', bible['geography'])}",
        'framing': (f"FRAMING (exact, from the floor plan): {framing_text(story['plan'], s['id'])}" if 'plan' in story else ''),
        'lighting': f"LIGHTING: {bible.get('lighting_rule', bible['lighting'])} This shot: {s['lighting']}",
        'wardrobe': f"WARDROBE AND PROPS: {bible.get('wardrobe_short', bible['wardrobe_props'])}",
        'activity': ('WHAT EACH PERSON IS DOING (never idle): ' + ' '.join(f'{n}: {a}.' for n, a in s.get('activity', {}).items())) if s.get('activity') else '',
        'arrival': ('ARRIVAL: ' + ' '.join(f"{n} comes from {a['from']} to {a['to']} because {a['why']}; on arrival {a['then']}." for n, a in s.get('arrival', {}).items())) if s.get('arrival') else '',
        'continuity': f'CONTINUITY: {continuity}',
        'action': f'ACTION, TIMED: {beats}',
        'performance': f"PERFORMANCE: {s['performance']}",
        'bible_performance': f"STYLE OF ACTING: {bible.get('performance_short', bible['performance'])}",
        'format': f"FORMAT: {bible['format']}."}
    order = ['intent', 'set', 'geography', 'framing', 'lighting', 'wardrobe', 'continuity', 'arrival', 'activity', 'action', 'performance', 'bible_performance', 'format']
    shot = {'id': s['id'], 'seconds': s['seconds'], 'camera': f"{cam['size']}, {cam['angle']}; {cam['movement']}; {cam['lens']} lens.", 'sound': s['sound']}
    dropped = []
    while True:
        shot['visual'] = ' '.join(sections[k] for k in order if k not in dropped and sections[k])
        prompt = native_prompt(shot)
        if len(prompt) <= limit or len(dropped) == len(DROP_ORDER):break
        dropped.append(DROP_ORDER[len(dropped)])
    directed_prompt.last_dropped = dropped
    return prompt


def keyframe_request(story, index):
    """The image-editor request that builds a cut's first frame from the room plate, the people and the previous shot's real last frame.
    None when the shot simply continues the previous frame."""
    s, bible = story['shots'][index], story['bible']
    if s.get('continues_previous'):return None
    chain = story.get('rules', {}).get('chain')
    ff = first_frame_plan(story)[index] if chain else None
    if ff and ff['mode'] == 'continue':return None  # same angle, same people: the previous shot's real last frame is this shot's first frame
    # identity follows what the viewer has already seen: a shot can name earlier real frames (`last:<shot id>`) instead of the original portrait
    refs = list(s.get('keyframe_refs') or ([story['plate']['id']] + [name for name in s.get('cast', [])] + (['previous_last_frame'] if index else [])))
    chain_text = ''
    if ff and ff['mode'] == 'resume':
        ids = [x['id'] for x in story['shots']]
        between = [x['end_state'] for x in story['shots'][ids.index(ff['from_shot']) + 1:index]]
        refs = ['last:' + ff['from_shot'], story['plate']['id']] + list(s.get('cast', []))
        chain_text = ("The FIRST reference image is the real last frame of this same camera angle from earlier in the film. Resume exactly from it: the same people in the same places "
                      "and the same size in frame, the same clothes, hair, props and every object on the walls and floor. Only what has happened since may differ"
                      + (' (' + ' '.join(between)[:400] + ')' if between else '') + '. ')
    elif ff and index:
        refs = ['previous_last_frame', story['plate']['id']] + list(s.get('cast', []))
        chain_text = ("The FIRST reference image is the real last frame of the previous shot. This is the same moment seen from a new camera angle: keep the same people in the same places, "
                      "clothes, props, light and room, and show only what the new camera would see. ")
    prompt = (f"{bible['format']}. {SET_LOCK}{bible['set']}. THE STARTING FRAME OF THE SHOT: {s['keyframe']} Lighting: {bible['lighting']} {s['lighting']} "
              f"Wardrobe and props: {bible['wardrobe_props']} "
              + (chain_text or ('Keep the room, the light, the wardrobe and every position exactly as in the previous shot\'s last frame (the final reference image); only the camera angle changes. ' if index else ''))
              + 'No text, no watermark.')
    if 'plan' in story:
        refs.append('layout:' + s['id'])
        people_key = '; '.join(f'the {c} block is {n}' for c, n in zip(('red', 'blue', 'green'), story['plan']['figures']))
        prompt = (prompt.replace('No text, no watermark.', '') + f"The LAST reference image is a LAYOUT GUIDE, not a style reference: flat coloured blocks show the exact camera position and where the walls, doorway, "
                  f"furniture and the people stand ({people_key}). Reproduce that layout exactly, photorealistically, in the look of the other references; "
                  f"do not copy the guide's flat colours or outlines. {framing_text(story['plan'], s['id'])} No text, no watermark.")
    return {'id': 'key-' + s['id'], 'refs': refs, 'prompt': prompt, 'cost': 50}


def plan_directed(story, model='kling-3.0', resolution='720p', credit_cap=None):
    validate_directed(story)
    jobs, images, warnings = [], 0, []
    for i, s in enumerate(story['shots']):
        prompt = directed_prompt(story, i)
        if len(prompt) > PROMPT_SOFT_LIMIT:warnings.append(f"{s['id']}: prompt is {len(prompt)} characters; trim it if the service truncates")
        key = keyframe_request(story, i)
        images += 1 if key else 0
        quote = quote_native_video(model, resolution, s['seconds'], True)
        jobs.append({'id': 'dir-' + s['id'], 'shot_id': s['id'], 'seconds': s['seconds'], 'frames': round(s['seconds'] * FPS), 'model': model, 'resolution': resolution,
                     'prompt': prompt, 'prompt_chars': len(prompt), 'quote': quote, 'continues_previous': bool(s.get('continues_previous')), 'keyframe': key,
                     'depends_on': ['dir-' + story['shots'][i - 1]['id']] if i else []})
    video = sum(j['quote']['amount'] for j in jobs)
    total = video + images * 50
    if credit_cap is not None and total > credit_cap:raise ValueError(f'Directed plan costs {total} credits (video {video} + {images} keyframes), over the {credit_cap} cap')
    return {'model': model, 'resolution': resolution, 'jobs': jobs, 'video_credits': video, 'keyframes': images, 'keyframe_credits': images * 50, 'total_credits': total,
            'total_seconds': sum(s['seconds'] for s in story['shots']), 'warnings': warnings, 'paid_requests': 0}


def render_script_markdown(story):
    """The readable director's script generated from the same data the prompts use."""
    b = story['bible']
    out = [f"# {story['title']}", '', f"*{story['logline']}*", '', '## Visual bible', '',
           f"- **Format:** {b['format']}", f"- **Set:** {b['set']}", f"- **Geography:** {b['geography']}", f"- **Lighting:** {b['lighting']}",
           f"- **Performance:** {b['performance']}", f"- **Wardrobe and props:** {b['wardrobe_props']}", '', '## Shots']
    for i, s in enumerate(story['shots'], 1):
        c = s['camera']
        out += ['', f"### {i}. {s['title']} ({s['seconds']} s)", '', f"**Intent:** {s['intent']}", '',
                f"**Camera:** {c['size']}, {c['angle']}; {c['movement']}; {c['lens']} lens.", f"**Light:** {s['lighting']}",
                f"**Begins with:** {s['start_state']}" + (" *(continues straight from the previous shot's last frame)*" if s.get('continues_previous') else ''), '', '| Time | Action |', '| --- | --- |']
        out += [f"| {x['t0']:.1f}-{x['t1']:.1f} s | {x['text']} |" for x in s['beats']]
        out += ['', f"**Performance:** {s['performance']}", f"**Sound:** {s['sound'].get('ambience', '')}; " + '; '.join(s['sound'].get('effects', []))]
        for d in s['sound'].get('dialogue', []) or []:
            out.append(f"**{d['speaker']}** ({d['delivery']}): \"{d['line']}\"")
        out.append(f"**Ends with:** {s['end_state']}")
    out += ['', f"**Hook title:** {story['hook_title']}  |  **End card:** {story['end_card']}"]
    return '\n'.join(out)
