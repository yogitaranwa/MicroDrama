"""Compile story shots into native-audio render jobs. No network, no spend.

One prompt per shot carries picture and sound (voice, effects, ambience). A shot marked `continues_previous` starts
from the last frame of the previous render (same framing only; a new angle needs its own reference frame); a scene change dissolves. Every price is
quoted before anything is submitted and a credit cap is enforced on the whole plan.
"""
import math
import re

from .core import finite, integer, identifier
from .execution import signature
from .native_mix import NATIVE_DURATIONS, native_prompt, quote_native_video, FPS

SPEECH_WORDS_PER_SECOND = 2.4
SPEECH_PADDING_SECONDS = 1.2
SCENE_DISSOLVE_FRAMES = 8


def speech_seconds(text):
    return len(str(text).split()) / SPEECH_WORDS_PER_SECOND


def snap_duration(model, seconds):
    allowed = NATIVE_DURATIONS.get(model)
    if not allowed:raise ValueError('No recorded durations for ' + model)
    fits = [d for d in allowed if d >= seconds - 1e-9]
    if not fits:raise ValueError(f'{seconds:.1f}s exceeds {model} maximum of {allowed[-1]}s; split at a motivated cut')
    return fits[0]


SET_LOCK = ('SET LOCK: every frame of this scene is the same place, copied from the first reference image. Keep every landmark, wall colour, '
            'window, furniture position and light direction identical; only the camera angle and the characters change. The place: ')
MAX_FRAME_REFS = 4


def build_frame_requests(story):
    """Ordered image requests for a story: one environment plate per scene first, then every frame built from the scene's plate,
    its characters' portraits and the previous frame of the same scene (the reference-selection idea used by multi-shot
    video agents). A plate costs one image; it is what keeps the background constant between shots."""
    refs = story['references'];scenes = story.get('scenes', {});out = []
    for scene_id, sc in scenes.items():
        out.append({'id': sc['plate'], 'scene': scene_id, 'edit': False, 'refs': [], 'prompt': sc['plate_prompt']})
    masters = set(refs.get('masters', {}))
    known = masters | {sc['plate'] for sc in scenes.values()};last = {}
    for name, spec in refs['frames'].items():
        scene_id = spec.get('scene')
        chosen = list(spec['refs'])
        if scene_id is not None:
            if scene_id not in scenes:raise ValueError(f'Frame {name} names unknown scene {scene_id}')
            plate = scenes[scene_id]['plate']
            chosen = [plate] + [r for r in chosen if r != plate]
            # carry the previous frame of this scene only when a character continues into this one; otherwise it would leak
            # the wrong person into the new frame
            if scene_id in last and masters.intersection(chosen) & last[scene_id][1]:chosen.append(last[scene_id][0])
        if not chosen:raise ValueError(f'Frame {name} has no reference images')
        missing = [r for r in chosen if r not in known]
        if missing:raise ValueError(f'Frame {name} references unknown images: {missing}')
        if len(chosen) > MAX_FRAME_REFS:chosen = chosen[:MAX_FRAME_REFS - 1] + [chosen[-1]]
        prompt = (SET_LOCK + scenes[scene_id]['set'] + '. ' if scene_id is not None else '') + spec['prompt']
        out.append({'id': name, 'scene': scene_id, 'edit': True, 'refs': chosen, 'prompt': prompt})
        known.add(name)
        if scene_id is not None:last[scene_id] = (name, masters.intersection(spec['refs']))
    return out


def tighten_seconds(shots, minimum=3):
    """Give every dialogue shot just the time its lines need (speech plus the usual padding, whole seconds, never below `minimum`).
    Only useful on models that accept any whole second; Veo's fixed 4/6/8 would round it back up. Silent shots keep their length."""
    out = []
    for shot in shots:
        dialogue = (shot.get('sound') or {}).get('dialogue') or []
        if isinstance(dialogue, dict):dialogue = [dialogue]
        need = sum(speech_seconds(d['line']) for d in dialogue) + (SPEECH_PADDING_SECONDS if dialogue else 0)
        out.append({**shot, 'seconds': max(minimum, math.ceil(need)) if dialogue else shot.get('seconds', minimum)})
    return out


def lint_story(shots):
    """Warnings about how a story will FEEL before any credit is spent. These are craft rules drawn from the measured gap to a
    reference the user wanted to match (more movement, not wall-to-wall dialogue, reaction beats, shots that differ from their neighbours)."""
    warnings = []
    total = sum(max(float(s.get('seconds', 0)), 0) for s in shots) or 1.0
    locked = [s for s in shots if re.search(r'\b(locked|static|steady)\b', str(s.get('camera', '')), re.I)]
    if len(locked) / len(shots) > 0.5:
        warnings.append(f'{len(locked)} of {len(shots)} shots ask for a locked/static camera: the film will look stiff. Give most shots a push-in, pull-out, pan or handheld sway, or set `zoom`.')
    talking = sum(float(s.get('seconds', 0)) for s in shots if (s.get('sound') or {}).get('dialogue'))
    if talking / total > 0.7:
        warnings.append(f'{round(100 * talking / total)}% of the runtime is someone talking: add silent reaction beats, inserts and sound-only moments between lines.')
    silent = [s for s in shots if not (s.get('sound') or {}).get('dialogue')]
    if len(silent) < max(2, len(shots) // 6):
        warnings.append(f'only {len(silent)} shot(s) without dialogue: add reaction or insert shots so the story can breathe.')
    run = 1
    for a, b in zip(shots, shots[1:]):
        run = run + 1 if (a.get('camera') or '').strip().lower() == (b.get('camera') or '').strip().lower() and a.get('camera') else 1
        if run >= 3:
            warnings.append(f"shots up to {b['id']} repeat the same camera setup three times in a row: change the angle or size.")
            break
    moving = [s for s in shots if s.get('zoom') or s.get('flash_frames')]
    if not moving:
        warnings.append('no shot uses `zoom` or `flash_frames`: add a push-in on reactions and a flash on shocks (free editor tricks).')
    return warnings


def compile_native_shots(shots, model='veo3.1-lite', resolution='720p', credit_cap=None, scene_dissolve_frames=SCENE_DISSOLVE_FRAMES, scenes=None):
    """shots: [{id, scene_id, location, visual, camera?, seconds?, action?, sound:{ambience, effects[], dialogue[]}}]
    scenes: optional {scene_id: {set, plate}}; when given, every shot of a scene carries the identical `set` line in its prompt."""
    if not shots:raise ValueError('No shots')
    if scenes is not None:
        unknown = sorted({s['scene_id'] for s in shots} - set(scenes))
        if unknown:raise ValueError('Shots name scenes with no locked set: ' + ', '.join(unknown))
        shots = [{**s, 'visual': 'Set: ' + scenes[s['scene_id']]['set'].rstrip('. ') + '. ' + s['visual']} for s in shots]
    scene_dissolve_frames = integer(scene_dissolve_frames, 'scene dissolve', 0, 24)
    jobs, previous, seen = [], None, set()
    for shot in shots:
        sid = identifier(shot['id'], 'shot id')
        if sid in seen:raise ValueError('Duplicate shot id ' + sid)
        seen.add(sid)
        sound = shot.get('sound') or {}
        dialogue = sound.get('dialogue') or []
        if isinstance(dialogue, dict):dialogue = [dialogue]
        if len({d['speaker'] for d in dialogue}) > 2:raise ValueError('More than two speakers in one shot: ' + sid)
        # the mouth that moves must be the voice you hear: a second on-screen speaker lets the model cut mid-line and put one
        # character's voice on another's face (seen in the 16s take, 2026-10-31). Cut between speakers; off-screen lines are fine.
        if len({d['speaker'] for d in dialogue if not d.get('offscreen')}) > 1 and not shot.get('allow_multi_speaker'):
            raise ValueError('Two on-screen speakers in one shot: ' + sid + '. Split into one shot per speaker, or mark the second offscreen.')
        spoken = sum(speech_seconds(d['line']) for d in dialogue) + (SPEECH_PADDING_SECONDS if dialogue else 0)
        seconds = snap_duration(model, max(finite(shot.get('seconds', 0), 'seconds', 0), spoken, 1))
        prompt = native_prompt({**shot, 'seconds': seconds, 'sound': {**sound, 'dialogue': dialogue}})
        chained = shot.get('continues_previous') is True
        if chained and (previous is None or (previous['scene_id'], previous['location']) != (shot['scene_id'], shot['location'])):
            raise ValueError('continues_previous needs a previous shot in the same scene and location: ' + sid)
        quote = quote_native_video(model, resolution, seconds, True)
        frames = round(seconds * FPS)
        jobs.append({'id': 'native-' + sid, 'shot_id': sid, 'scene_id': shot['scene_id'], 'location': shot['location'],
                     'model': model, 'resolution': resolution, 'audio': True, 'seconds': seconds, 'frames': frames,
                     'prompt': prompt, 'quote': quote,
                     'first_frame': {'source': 'previous_last_frame', 'shot_id': previous['id']} if chained
                     else {'source': 'reference', 'image_id': 'frame-' + sid},
                     'depends_on': ['native-' + previous['id']] if chained else [],
                     'overlap_frames': scene_dissolve_frames if previous is not None and (previous['scene_id'], previous['location']) != (shot['scene_id'], shot['location']) else 0,
                     'speakers': sorted({d['speaker'] for d in dialogue})})
        previous = shot
    total = sum(j['quote']['amount'] for j in jobs)
    if credit_cap is not None and total > credit_cap:
        raise ValueError(f'Plan costs {total} credits, over the {credit_cap} cap; shorten shots, cut shots or pick a cheaper model')
    by_speaker = {}
    for j in jobs:
        for s in j['speakers']:by_speaker.setdefault(s, []).append(j['shot_id'])
    plan = {'model': model, 'resolution': resolution, 'jobs': jobs, 'total_seconds': sum(j['seconds'] for j in jobs),
            'total_credits': total, 'derived_quote': any(j['quote']['derived'] for j in jobs),
            'assembly_shots': [{'shot_id': j['shot_id'], 'frames': j['frames'], 'overlap_frames': j['overlap_frames']} for j in jobs],
            'voice_consistency_checks': {s: ids for s, ids in by_speaker.items() if len(ids) > 1},
            'warnings': ['Each shot generates its own voice from the written description: listen to every speaker across shots before accepting.',
                         'Render chained shots in order; extract the previous clip\'s last frame (native_mix.extract_frame) as the next first frame.'],
            'lint': lint_story(shots), 'status': 'compiled_not_rendered', 'paid_requests': 0}
    plan['plan_sha256'] = signature(plan)
    return plan


def compile_native_plan(brief, episode, model='veo3.1-lite', resolution='720p', voices=None, sound=None, credit_cap=None):
    """Adapter for the story/brief schema. Voices come from `voices` or a character's optional `voice` field."""
    chars = {c['id']: c for c in brief['characters']}
    voices = {**{cid: c['voice'] for cid, c in chars.items() if c.get('voice')}, **(voices or {})}
    lines = {l['id']: l for l in episode['lines']}
    shots = []
    for s in episode['shots']:
        design = {**(s.get('sound') or {}), **((sound or {}).get(s['id'], {}))}
        dialogue = []
        for lid in s['line_ids']:
            l = lines[lid]
            if l['speaker'] not in voices:raise ValueError('No written voice description for ' + l['speaker'])
            dialogue.append({'speaker': chars[l['speaker']]['name'], 'voice': voices[l['speaker']], 'line': l['text'],
                             'delivery': l.get('performance', ''), 'offscreen': l['speaker'] not in s['visible_characters']})
        cast = '; '.join(f"{chars[c]['name']}: {chars[c]['description']}" for c in s['visible_characters'])
        visual = ' '.join(x for x in (
            'Preserve the exact starting frame, faces, wardrobe and room.', s.get('location_description', ''), cast + '.' if cast else '',
            ('Wardrobe: ' + s['wardrobe']) if s.get('wardrobe') else '', ('Props: ' + ', '.join(s['props']) + '.') if s.get('props') else '',
            s['action']) if x)
        shots.append({'id': s['id'], 'scene_id': s['scene_id'], 'location': s['location'], 'visual': visual, 'camera': s.get('camera', ''),
                      'seconds': s.get('seconds', 0), 'continues_previous': s.get('continues_previous', False), 'sound': {**design, 'dialogue': dialogue}})
    return compile_native_shots(shots, model, resolution, credit_cap)


def compile_scene_take(shots, voices, scene, model='veo3.1-lite', resolution='720p', credit_cap=None):
    """Merge consecutive shots of ONE scene into a single generation of time-coded beats. Same price per second as separate
    shots, but one generation means one room and (the hypothesis under test) one voice per character for the whole take.
    shots: each with `seconds` (the beat length), visual, camera?, sound{ambience, effects[], dialogue[]}.
    voices: {speaker: written voice description}. scene: {set}."""
    if not shots:raise ValueError('No shots')
    beats, cursor, speakers = [], 0.0, []
    for shot in shots:
        sound = shot.get('sound') or {}
        dialogue = sound.get('dialogue') or []
        need = sum(speech_seconds(d['line']) for d in dialogue) + (0.6 if dialogue else 0)
        length = finite(shot['seconds'], 'seconds', 1)
        if need > length + 1e-9:raise ValueError(f"Beat {shot['id']} needs {need:.1f}s for its lines but has {length:.1f}s")
        native_prompt({**shot, 'seconds': length, 'sound': {**sound, 'dialogue': dialogue}})  # impact and voice-description gates
        parts = [shot['visual'].strip()]
        if shot.get('camera'):parts.append('Camera: ' + shot['camera'].strip())
        audio = [str(e).strip() for e in sound.get('effects', [])]
        if sound.get('ambience'):audio.append('ambience: ' + sound['ambience'].strip())
        for d in dialogue:
            if d['speaker'] not in voices:raise ValueError('No written voice for ' + d['speaker'])
            if d['speaker'] not in speakers:speakers.append(d['speaker'])
            who = 'off-screen ' + d['speaker'] if d.get('offscreen') else d['speaker']
            audio.append(f"{who} says exactly once: \"{d['line'].strip()}\"" + (f" ({d['delivery'].strip()})" if d.get('delivery') else ''))
        beats.append(f"{cursor:.0f}-{cursor + length:.0f}s: " + ' '.join(parts) + (' Sound: ' + '; '.join(audio) + '.' if audio else ''))
        cursor += length
    seconds = snap_duration(model, cursor)
    if seconds - cursor > 1e-9:raise ValueError(f'Beats total {cursor:.0f}s but {model} accepts {seconds}s next; add or trim a beat so no time is wasted')
    bible = ' '.join(f'{s}: {voices[s]}.' for s in speakers)
    prompt = (f"One continuous {seconds}-second scene filmed as a single take sequence in one place: {scene['set'].rstrip('. ')}. "
              'The same characters, the same room and the same voices for the whole clip; nothing resets between beats. '
              f'VOICES (identical every time the character speaks): {bible} '
              'BEATS: ' + ' '.join(beats) + ' No music, no subtitles, no on-screen text, no watermarks.')
    quote = quote_native_video(model, resolution, seconds, True)
    if credit_cap is not None and quote['amount'] > credit_cap:raise ValueError(f"Take costs {quote['amount']} credits, over the {credit_cap} cap")
    return {'id': 'take-' + shots[0]['id'], 'shot_ids': [s['id'] for s in shots], 'model': model, 'resolution': resolution, 'audio': True,
            'seconds': seconds, 'frames': round(seconds * FPS), 'prompt': prompt, 'quote': quote, 'beats': beats,
            'first_frame': {'source': 'reference', 'image_id': 'frame-' + shots[0]['id']}, 'paid_requests': 0,
            'warnings': ['Multi-speaker takes let the model choose its own cuts: it can cut away mid-line and leave one character\'s voice '
                         'on another character\'s moving mouth (seen 2026-10-31). Prefer one speaker per shot for dialogue.']}
