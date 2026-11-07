"""Native-audio episode assembly: keep each clip's own dialogue/effects/ambience and join with real transitions.

The older dubbed route discarded every clip's sound (-an), laid one pre-made voice file over silent video and
hard-concatenated the shots, so crashes had no sound, seams had no room tone and speech was never tied to the
mouth that spoke it. This module keeps the generated audio, overlaps shots (video dissolve plus audio crossfade),
layers optional ambience/effects/ducked music and measures dead air, silent seams and level. Measurements are
signal facts only; listening to the real playback is still required.
"""
import math
import re
import shutil
import subprocess
from pathlib import Path

from .core import digest, finite, integer, write_json

FPS = 24
MAX_WORDS_PER_SECOND = 3.2
AUDIO_SEAM_FRAMES = 6  # edge fades; only planned overlaps crossfade, and level continuity still needs review
IMPACT = re.compile(r'\b(crash\w*|collaps\w*|burst\w*|explo\w*|slam\w*|smash\w*|shatter\w*|thud\w*|impact\w*|breach\w*|'
                    r'topple\w*|roar\w*|stomp\w*|bang\w*|thunder\w*|kick\w*|flip\w*|gunshot\w*)\b', re.I)
# Credits per output second from https://docs.magichour.ai/api-reference/models (read 2026-10-29): (base, audio extra, published)
NATIVE_RATES = {
    ('veo3.1-lite', '720p'): (48, 24, True), ('veo3.1-lite', '1080p'): (72, 24, True),
    ('veo3.1', '720p'): (96, 24, True), ('veo3.1', '1080p'): (120, 24, True),
    ('kling-3.0', '720p'): (48, 24, True), ('kling-3.0', '1080p'): (72, 24, True),  # +24 audio listed on the rate table, re-read 2026-11-01
    ('seedance-2.0-mini', '480p'): (48, 0, True), ('seedance-2.0-mini', '720p'): (120, 0, True),
    ('seedance-2.0', '720p'): (216, 0, True), ('minimax-h3', '720p'): (48, 0, True), ('ltx-2.5', '720p'): (48, 0, True),
    ('wan-3.0', '720p'): (96, 0, True), ('wan-3.0', '480p'): (48, 0, True),
}


def ffmpeg_exe():
    found = shutil.which('ffmpeg')
    if found:return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:raise RuntimeError('ffmpeg is required: install it or `pip install imageio-ffmpeg`')


def _run(args):
    r = subprocess.run([ffmpeg_exe(), '-v', 'error', '-nostdin', '-y', *map(str, args)], capture_output=True, text=True)
    if r.returncode:raise RuntimeError('ffmpeg failed: ' + r.stderr[:1200])


def _stderr(args):
    return subprocess.run([ffmpeg_exe(), '-hide_banner', '-nostdin', *map(str, args)], capture_output=True, text=True).stderr


def probe(path):
    err = _stderr(['-i', path])
    d = re.search(r'Duration:\s*(\d+):(\d+):([\d.]+)', err)
    if not d:raise ValueError('Unreadable media: ' + str(path))
    size = re.search(r'Video:.*?,\s*(\d{2,5})x(\d{2,5})', err)
    return {'duration': int(d[1]) * 3600 + int(d[2]) * 60 + float(d[3]), 'has_audio': 'Audio:' in err,
            'has_video': 'Video:' in err, 'size': (int(size[1]), int(size[2])) if size else None}


def checked(asset):
    p = Path(asset['path'])
    if not p.is_file() or digest(p) != asset['sha256']:raise ValueError('Absent or changed media asset')
    return p.resolve()


NATIVE_DURATIONS = {  # whole seconds a model accepts for image-to-video (Magic Hour OpenAPI, read 2026-10-29)
    'veo3.1-lite': [4, 6, 8, 16, 24, 32, 40, 48, 56], 'veo3.1': [4, 6, 8, 16, 24, 32, 40, 48, 56],
    'kling-3.0': list(range(3, 16)), 'seedance-2.0-mini': list(range(4, 16)), 'seedance-2.0': list(range(4, 16)),
    'minimax-h3': list(range(1, 31)), 'ltx-2.5': list(range(1, 61)),
    'wan-3.0': [2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30],
}


AUDIO_TO_VIDEO_RATES = {'480p': 24, '720p': 48, '1080p': 72}  # credits per output second, docs.magichour.ai models page, read 2026-11-01


def quote_audio_to_video(seconds, resolution='720p'):
    """Video driven by a separate audio file (a fixed voice): the voice comes first, the mouth follows it."""
    if resolution not in AUDIO_TO_VIDEO_RATES:raise ValueError('No recorded audio-to-video rate for ' + resolution)
    # billed per whole frame at 24 fps (2.3 s = 56 frames = 112 credits at 720p, not 111): round frames up first
    frames = math.ceil(finite(seconds, 'seconds', .5) * 24 - 1e-9)
    return {'amount': math.ceil(frames * AUDIO_TO_VIDEO_RATES[resolution] / 24), 'unit': 'credits', 'frames': frames}


def quote_voice(text):
    """Voice cloner / voice generator: 0.1 credit per character, rounded up, 1000 characters per request."""
    n = len(str(text))
    if not 1 <= n <= 1000:raise ValueError('Voice text must be 1-1000 characters')
    return {'amount': math.ceil(n / 10), 'unit': 'credits', 'characters': n}


def plan_music(seconds, prompt):
    """An instrumental score under the whole film: 1 credit per requested second, 15-300 s. One continuous bed is what makes cuts feel joined."""
    seconds = integer(max(15, math.ceil(finite(seconds, 'seconds', 1))), 'seconds', 15, 300)  # the service sells 15 s at the least
    if not str(prompt).strip():raise ValueError('Describe the music')
    return {'endpoint': '/v1/ai-music-generator', 'body': {'name': 'Score', 'duration': seconds, 'style': {'prompt': str(prompt).strip(), 'instrumental': True}},
            'quote': {'amount': seconds, 'unit': 'credits'}}


def quote_native_video(model, resolution, seconds, audio=True):
    """Planning quote in credits. `derived` means the audio surcharge is arithmetic, not a published rate."""
    if (model, resolution) not in NATIVE_RATES:raise ValueError('No recorded rate for ' + model + ' ' + resolution)
    base, extra, published = NATIVE_RATES[(model, resolution)]
    seconds = finite(seconds, 'seconds', .5)
    return {'amount': math.ceil(seconds * (base + (extra if audio else 0))), 'unit': 'credits', 'derived': bool(audio and extra and not published)}


def _dialogue(sound):
    d = sound.get('dialogue')
    return [] if not d else list(d) if isinstance(d, list) else [d]


def require_sound_design(shot):
    """An impact/action shot must say what it sounds like. Silent crashes were the worst audible defect."""
    sound = shot.get('sound') or {}
    action = ' '.join(str(shot.get(k, '')) for k in ('visual', 'action'))
    if IMPACT.search(action) and not [e for e in sound.get('effects', []) if str(e).strip()]:
        raise ValueError('Shot ' + str(shot.get('id')) + ' has an impact/action but no sound effect written for it')
    lines = _dialogue(sound)
    for d in lines:
        if not str(d.get('voice', '')).strip():raise ValueError('Dialogue needs a written voice description, not a preset name')
    if lines and sum(len(str(d['line']).split()) for d in lines) / finite(shot['seconds'], 'seconds', 1) > MAX_WORDS_PER_SECOND:
        raise ValueError('Line too long for shot length')
    return True


def native_prompt(shot):
    """Render a shot into one prompt that asks the video model for picture and sound together."""
    require_sound_design(shot)
    sound = shot.get('sound') or {}
    parts = [shot['visual'].strip()]
    if shot.get('camera'):parts.append('Camera: ' + shot['camera'].strip())
    audio = []
    if sound.get('ambience'):audio.append('continuous room tone and ambience: ' + sound['ambience'].strip())
    effects = [str(e).strip() for e in sound.get('effects', []) if str(e).strip()]
    if effects:audio.append('clearly audible sound effects at film-level loudness, synchronized to the picture: ' + '; '.join(effects))
    for d in _dialogue(sound):
        who = f"an off-screen voice of {d['speaker']}" if d.get('offscreen') else d['speaker']
        audio.append(f"{who} ({d['voice'].strip()}) says exactly once: \"{d['line'].strip()}\"" + (f" - delivery: {d['delivery'].strip()}" if d.get('delivery') else ''))
    parts.append('SOUND (must be audible): ' + '; '.join(audio) + '.' if audio else 'SOUND: natural room tone only.')
    if _dialogue(sound):
        # seen with kling-3.0: it prepends "Ugh" / "A- A-" before a line, and turns the speaker's back to the camera mid-line
        parts.append('SPEECH RULES: speak only the quoted words, once, in order, nothing before or after: no interjections, fillers, stutters or sighs. '
                     'The speaker\'s face stays toward the camera, mouth visible, while speaking.')
    parts.append('No music, no subtitles, no on-screen text, no watermarks.')
    return ' '.join(parts)


def plan_timeline(shots):
    """Frame-exact placement. `overlap_frames` dissolves a shot into the previous one; it is removed from the total."""
    if not shots:raise ValueError('No shots')
    cursor, rows = 0, []
    for i, s in enumerate(shots):
        frames = integer(s['frames'], 'frames', 2, 4320)
        overlap = integer(s.get('overlap_frames', 0), 'overlap_frames', 0, 48)
        if i == 0 and overlap:raise ValueError('First shot cannot overlap a previous shot')
        nxt = integer(shots[i + 1].get('overlap_frames', 0), 'overlap_frames', 0, 48) if i + 1 < len(shots) else 0
        if overlap + nxt > frames:raise ValueError('Shot ' + str(i) + ' is shorter than its two overlaps')
        start = cursor - overlap
        rows.append({'index': i, 'start_frame': start, 'frames': frames, 'overlap_frames': overlap})
        cursor = start + frames
    return {'shots': rows, 'total_frames': cursor, 'duration': cursor / FPS}


def _levels(path, start, seconds):
    err = _stderr(['-ss', f'{start:.3f}', '-t', f'{seconds:.3f}', '-i', path, '-af', 'volumedetect', '-vn', '-f', 'null', '-'])
    mean, peak = re.search(r'mean_volume:\s*([-\d.]+)', err), re.search(r'max_volume:\s*([-\d.]+)', err)
    return (float(mean[1]) if mean else None), (float(peak[1]) if peak else None)


def shot_gain_db(path, start, seconds, target_mean_db=-22.0, limit_db=12.0, peak_ceiling_db=-1.5):
    """Bring each clip's own audio to a common level; never push the peak over the ceiling."""
    mean, peak = _levels(path, start, seconds)
    if mean is None:return 0.0
    gain = max(-limit_db, min(limit_db, target_mean_db - mean))
    return round(min(gain, peak_ceiling_db - peak) if peak is not None else gain, 2)


def extract_room_tone(videos, output, seconds=0.6):
    """Cut the quietest stretch (the ambience between lines) out of a scene's own clips, so a bed that matches the room can be
    looped under the scene. Refuses a window that is digital silence: that would be a bed of nothing."""
    import numpy as np
    best = None
    for v in videos:
        raw = subprocess.run([ffmpeg_exe(), '-v', 'error', '-nostdin', '-i', str(v), '-vn', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True).stdout
        x = np.frombuffer(raw, np.int16).astype(float) / 32768;w = int(16000 * seconds)
        for i in range(0, max(len(x) - w, 0), 1600):
            level = float(np.sqrt(np.mean(x[i:i + w] ** 2)))
            if best is None or level < best[0]:best = (level, str(v), i / 16000)
    if best is None or best[0] < 10 ** (-70 / 20):raise ValueError('No usable room tone: the quietest stretch is digital silence')
    output = Path(output)
    if output.exists():raise ValueError('Fresh output path required')
    _run(['-ss', f'{best[2]:.3f}', '-t', f'{seconds:.3f}', '-i', best[1], '-vn', '-ar', 48000, '-ac', 2, output])
    return {'path': str(output.resolve()), 'sha256': digest(output), 'source': best[1], 'start': round(best[2], 2), 'level_dbfs': round(20 * math.log10(best[0]), 1)}


def ensure_mp3(path):
    """Return a path whose bytes really are MP3. The voice cloner returns WAV data even when the file is saved as .mp3, and
    audio-to-video then refuses it ("couldn't read your audio file"). Real MP3s come back unchanged."""
    path = Path(path)
    head = path.read_bytes()[:3]
    if head == b'ID3' or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):return path
    out = path.with_name(path.stem + '-real.mp3')
    if not out.exists():_run(['-i', path, '-vn', '-ar', 44100, '-ac', 1, '-c:a', 'libmp3lame', '-b:a', '128k', out])
    return out


def extract_frame(video, output, last=True):
    """Pull the final (or first) frame of a clip so the next shot can start from where this one ended."""
    output = Path(output)
    if output.exists():raise ValueError('Fresh frame output path required')
    _run((['-sseof', '-0.15'] if last else []) + ['-i', video, '-frames:v', 1, '-update', 1, output])
    if not output.is_file():raise RuntimeError('Frame extraction produced nothing')
    return {'path': str(output.resolve()), 'sha256': digest(output)}


def frame_count(path):
    err = _stderr(['-i', path, '-map', '0:v:0', '-f', 'null', '-'])
    found = re.findall(r'frame=\s*(\d+)', err)
    if not found:raise ValueError('Cannot count frames: ' + str(path))
    return int(found[-1])


def _exact(path, expected, what):
    got = frame_count(path)
    if got != expected:raise RuntimeError(f'{what} has {got} frames, planned {expected}; refusing to ship a short film')
    return path


def _effects(shot, frames, w, h):
    """Editor tricks that add life to a static shot at no credit cost: `zoom` [start, end] scale (1.0-1.5, e.g. [1.0, 1.12] push-in or
    [1.12, 1.0] pull-out) and `flash_frames` (a white flash that fades into the picture, for impacts and shocks)."""
    out = ''
    zoom = shot.get('zoom')
    if zoom:
        z0, z1 = (finite(z, 'zoom', 1.0) for z in zoom)
        if not (1.0 <= z0 <= 1.5 and 1.0 <= z1 <= 1.5):raise ValueError('zoom must stay between 1.0 and 1.5')
        dur = frames / FPS
        out += f",scale=w='ceil({w}*({z0}+({z1}-{z0})*t/{dur:.4f})/2)*2':h=-2:eval=frame,crop={w}:{h}"
    grade = shot.get('grade')
    if grade:
        # per-channel gains (and optional gamma) to match one shot's look to its neighbour's: a freshly generated first frame can be much warmer
        # and brighter than the frame chained from the previous shot, and the cut then looks like two different films
        r, g, b = (finite(grade.get(k, 1.0), 'grade ' + k, 0.3) for k in ('r', 'g', 'b'))
        gamma = finite(grade.get('gamma', 1.0), 'grade gamma', 0.3)
        if max(r, g, b) > 2.0 or gamma > 2.5:raise ValueError('grade gains must stay within 0.3-2.0')
        out += f',colorchannelmixer=rr={r}:gg={g}:bb={b}' + (f',eq=gamma={gamma}' if abs(gamma - 1.0) > 1e-6 else '')
    flash = integer(shot.get('flash_frames', 0), 'flash_frames', 0, 24)
    if flash:out += f',fade=t=in:s=0:n={flash}:color=white'
    return out


def assemble_native_episode(spec, output, size=(540, 960)):
    """spec: shots[{path,sha256,frames,source_start_frame,overlap_frames,pixel_checked,gain_db?}],
    beds[{path,sha256,gain,start_seconds}], effects[{path,sha256,at_seconds,gain}], music[{path,sha256,gain,start_seconds}].
    Video is built from verified exact-frame pieces (shot files -> hard-cut runs -> dissolves between runs); the
    fps filter is never used to join because it drops frames at segment ends and shifts every later dissolve."""
    output = Path(output)
    if output.exists():raise ValueError('Fresh episode output directory required')
    w, h = size
    if w / h not in (9 / 16, 16 / 9) or any(type(x) is not int or x < 100 or x % 2 for x in size):raise ValueError('Even 9:16 or 16:9 output dimensions required')
    timeline = plan_timeline(spec['shots'])
    total, duration = timeline['total_frames'], timeline['duration']
    if duration > 180:raise ValueError('Episode exceeds 180 seconds')
    paths, gains = [], []
    for row, s in zip(timeline['shots'], spec['shots']):
        path = checked(s)
        if s.get('pixel_checked') is not True:raise ValueError('Shot pixels not checked')
        info = probe(path);offset = integer(s.get('source_start_frame', 0), 'source_start_frame', 0, 24 * 180)
        if not info['has_video']:raise ValueError('Shot has no video')
        if not info['has_audio']:raise ValueError('Native-audio shot has no audio stream; regenerate with audio on, do not dub silently')
        if info['duration'] + 1 / FPS < (offset + row['frames']) / FPS:raise ValueError('Video is shorter than planned; do not freeze silently')
        paths.append(path)
        gains.append(s['gain_db'] if 'gain_db' in s else shot_gain_db(path, offset / FPS, row['frames'] / FPS))
    output.mkdir(parents=True)
    work = output / 'work';work.mkdir()
    pieces = []
    for row, s, path in zip(timeline['shots'], spec['shots'], paths):
        off = s.get('source_start_frame', 0);piece = work / f'shot-{row["index"]:03}.mp4'
        _run(['-i', path, '-vf', f'fps={FPS},trim=start_frame={off}:end_frame={off + row["frames"]},setpts=PTS-STARTPTS,'
              f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p' + _effects(s, row['frames'], w, h),
              '-frames:v', row['frames'], '-an', '-c:v', 'libx264', '-crf', '10', '-preset', 'veryfast', '-r', FPS, piece])
        pieces.append(_exact(piece, row['frames'], 'Shot ' + str(row['index'])))
    runs, current = [], [0]  # a dissolve starts a new run; hard cuts stay inside one run
    for row in timeline['shots'][1:]:
        if row['overlap_frames']:runs.append(current);current = [row['index']]
        else:current.append(row['index'])
    runs.append(current)
    run_files = []
    for k, members in enumerate(runs):
        frames = sum(timeline['shots'][i]['frames'] for i in members)
        if len(members) == 1:run_files.append(pieces[members[0]]);continue
        listing = work / f'run-{k}.txt'
        listing.write_text(''.join(f"file '{pieces[i].name}'\n" for i in members))
        out = work / f'run-{k}.mp4'
        _run(['-f', 'concat', '-safe', 1, '-i', listing, '-c:v', 'libx264', '-crf', '10', '-preset', 'veryfast', '-r', FPS, out])
        run_files.append(_exact(out, frames, 'Run ' + str(k)))
    video = output / 'video.mp4'
    if len(run_files) == 1:
        shutil.copyfile(run_files[0], video)
    else:
        fc, cv = [], '0:v'
        for k in range(1, len(run_files)):
            first = timeline['shots'][runs[k][0]]
            fc.append(f'[{cv}][{k}:v]xfade=transition=fade:duration={first["overlap_frames"] / FPS:.4f}:offset={first["start_frame"] / FPS:.4f}[x{k}]')
            cv = f'x{k}'
        args = [a for f in run_files for a in ('-i', f)]
        _run(args + ['-filter_complex', ';'.join(fc), '-map', f'[{cv}]', '-c:v', 'libx264', '-crf', '14', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-r', FPS, video])
    _exact(video, total, 'Assembled video')
    inputs, af, i0 = [], [], len(paths)
    seam = integer(spec.get('seam_frames', AUDIO_SEAM_FRAMES), 'seam_frames', 2, 24)
    for row, g, path in zip(timeline['shots'], gains, paths):
        i, s = row['index'], spec['shots'][row['index']];off = s.get('source_start_frame', 0) / FPS;sec = row['frames'] / FPS
        inputs += ['-i', path]
        fin = max(row['overlap_frames'], seam) / FPS
        nxt = spec['shots'][i + 1].get('overlap_frames', 0) if i + 1 < len(paths) else 0
        fout = max(nxt, seam) / FPS;ms = round(row['start_frame'] / FPS * 1000)
        st = finite(s.get('pitch_semitones', 0), 'pitch_semitones', -6)
        if st > 6:raise ValueError('Pitch shift beyond 6 semitones sounds processed; regenerate the shot')
        pitch = f'rubberband=pitch={2 ** (st / 12):.5f}:formant=preserved,' if abs(st) > 0.05 else ''
        af.append(f'[{i}:a]atrim=start={off:.4f}:duration={sec:.4f},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,'
                  f'{pitch}volume={g}dB,afade=t=in:st=0:d={fin:.4f},afade=t=out:st={max(sec - fout, 0):.4f}:d={fout:.4f},adelay={ms}|{ms}[a{i}]')
    af.append(''.join(f'[a{i}]' for i in range(len(paths))) + f'amix=inputs={len(paths)}:normalize=0:dropout_transition=0,apad=whole_dur={duration:.4f}[dia]')
    layers, ducked = ['[dia]'], []
    for kind in ('beds', 'effects', 'music'):
        for a in spec.get(kind, []):
            layer = checked(a);gain = finite(a.get('gain', .2), 'gain', 0)
            if gain > 1:raise ValueError('Layer gain exceeds conservative maximum')
            start = finite(a.get('start_seconds', a.get('at_seconds', 0)), 'start', 0);ms = round(start * 1000)
            inputs += (['-stream_loop', '-1'] if kind != 'effects' else []) + ['-i', layer]
            lab = f'l{i0}'
            steady = ',acompressor=threshold=0.04:ratio=4:attack=40:release=300:makeup=4' if a.get('steady') else ''  # a generated score swells and dies; this keeps the bed level
            af.append(f'[{i0}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo{steady},atrim=duration={duration:.4f},volume={gain},'
                      f'afade=t=in:st=0:d=0.4,adelay={ms}|{ms},apad=whole_dur={duration:.4f},atrim=duration={duration:.4f}[{lab}]')
            (ducked if kind == 'music' else layers).append(f'[{lab}]');i0 += 1
    if ducked:
        af.append('[dia]asplit=2[dsc][dmx]')
        layers[0] = '[dmx]'
        for k, lab in enumerate(ducked):
            af.append(f'{lab}[dsc]sidechaincompress=threshold=0.04:ratio=8:attack=15:release=500[dk{k}]');layers.append(f'[dk{k}]')
    af.append(''.join(layers) + f'amix=inputs={len(layers)}:normalize=0:dropout_transition=0,alimiter=limit=0.95,loudnorm=I=-16:TP=-1.5:LRA=11,atrim=duration={duration:.4f}[out]')
    audio = output / 'audio.wav'
    _run(inputs + ['-filter_complex', ';'.join(af), '-map', '[out]', '-ar', 48000, '-c:a', 'pcm_s16le', audio])
    clean = output / 'clean.mp4'
    _run(['-i', video, '-i', audio, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-ar', '48000', '-b:a', '192k', '-t', f'{duration:.4f}', clean])
    shutil.rmtree(work, ignore_errors=True)
    report = native_report(clean, [r['start_frame'] / FPS for r in timeline['shots'][1:]], expected_frames=total)
    for cut, row in zip(report['cut_audio']['cuts'], timeline['shots'][1:]):
        cut.update(left_shot_index=row['index'] - 1, right_shot_index=row['index'], overlap_frames=row['overlap_frames'])
    result = {'path': str(clean.resolve()), 'sha256': digest(clean), 'duration': duration, 'frames': total, 'timeline': timeline, 'gains_db': gains,
              'mechanical': report, 'status': 'assembled_preview_requires_full_playback_and_listening', 'paid_requests': 0}
    write_json(output / 'assembly.json', result)
    if report['defects']:
        raise ValueError('Assembled episode has measured defects: ' + '; '.join(d['type'] + '@' + str(d.get('at', d.get('start'))) for d in report['defects']))
    return result


def native_report(video, cut_times=(), expected_frames=None, dead_air_db=-50.0, dead_air_seconds=1.0, seam_db=-55.0, lufs_range=(-23.0, -12.0)):
    """Dead air, silent seams at every cut, and integrated level. Not an audibility or quality verdict."""
    from .edit_profile import cut_audio_report
    video = Path(video);info = probe(video);defects = [];cut_times = list(cut_times)
    if expected_frames is not None:
        got = frame_count(video)
        if got < expected_frames - 1:defects.append({'type': 'video_frames_missing', 'expected': expected_frames, 'got': got})
    if not info['has_audio']:return {'defects': [{'type': 'missing_audio'}], 'mechanical_pass': False}
    err = _stderr(['-i', video, '-af', f'silencedetect=n={dead_air_db}dB:d={dead_air_seconds}', '-vn', '-f', 'null', '-'])
    starts = [float(x) for x in re.findall(r'silence_start:\s*([-\d.]+)', err)];ends = [float(x) for x in re.findall(r'silence_end:\s*([-\d.]+)', err)]
    for k, s in enumerate(starts):defects.append({'type': 'dead_air', 'start': max(s, 0), 'end': ends[k] if k < len(ends) else info['duration']})
    for t in cut_times:
        mean, _ = _levels(video, max(t - .15, 0), .3)
        if mean is not None and mean < seam_db:defects.append({'type': 'silent_seam', 'at': round(t, 3), 'mean_db': mean})
    loud = _stderr(['-i', video, '-af', 'ebur128=peak=true', '-vn', '-f', 'null', '-'])
    lufs = re.findall(r'I:\s*([-\d.]+)\s*LUFS', loud);lufs = float(lufs[-1]) if lufs else None
    if lufs is None or not lufs_range[0] <= lufs <= lufs_range[1]:defects.append({'type': 'loudness_out_of_range', 'lufs': lufs})
    return {'duration_seconds': info['duration'], 'integrated_lufs': lufs, 'defects': defects, 'mechanical_pass': not defects,
            'cut_audio': cut_audio_report(video, cut_times),
            'scope': 'Signal measurements only; does not establish voice quality, acting, sync or audibility in real playback.'}


def speech_span(path, start, seconds, rise_db=10.0, min_seconds=0.15):
    """(first, last) second of speech inside a clip window: where the level rises `rise_db` above that clip's own noise floor
    (10th percentile), for at least `min_seconds`. Adapts to wind and room tone that a fixed threshold mistakes for speech.
    A clip with no contrast (a steady sound) is returned whole; an inaudible one gives None."""
    import numpy as np
    raw = subprocess.run([ffmpeg_exe(), '-v', 'error', '-nostdin', '-ss', f'{start:.3f}', '-t', f'{seconds:.3f}', '-i', str(path), '-vn', '-ac', '1', '-ar', '16000',
                          '-f', 's16le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float) / 32768
    hop = 320  # 20 ms
    n = len(x) // hop
    if n < 5:return None
    rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1))
    peak, floor = rms.max(), max(np.percentile(rms, 10), 1e-5)
    if peak < 10 ** (-50 / 20):return None
    thr = floor * 10 ** (rise_db / 20)
    if peak < thr:return (0.0, seconds)
    active = rms > thr;need = max(int(min_seconds / 0.02), 1)
    runs, i = [], 0
    while i < n:
        if active[i]:
            j = i
            while j < n and active[j]:j += 1
            if j - i >= need:runs.append((i, j))
            i = j
        else:i += 1
    if not runs:return None
    return (round(runs[0][0] * 0.02, 3), round(runs[-1][1] * 0.02, 3))


def caption_cues(timeline, spec_shots, lines):
    """lines: {shot_index: [{'text': ...}]}. Each shot's lines share that shot's measured speech span, split by word count."""
    cues = []
    for index, texts in lines.items():
        row, s = timeline['shots'][index], spec_shots[index]
        span = speech_span(checked(s), s.get('source_start_frame', 0) / FPS, row['frames'] / FPS)
        if span is None:continue
        total = sum(len(t['text'].split()) for t in texts) or 1;cursor = span[0]
        for t in texts:
            part = (span[1] - span[0]) * len(t['text'].split()) / total
            cues.append({'start': round(row['start_frame'] / FPS + cursor, 3), 'end': round(row['start_frame'] / FPS + cursor + part, 3), 'text': t['text']})
            cursor += part
    return cues


def _ass_time(t):
    return f'{int(t // 3600)}:{int(t % 3600 // 60):02}:{t % 60:05.2f}'


def burn_captions(video, cues, output, size):
    """Burn plain white captions with a dark outline at the bottom third. Same frames in, same frames out."""
    import textwrap
    w, h = size;output = Path(output)
    if output.exists():raise ValueError('Fresh output path required')
    font, margin = round(h * 0.045 if h > w else h * 0.06), round(h * 0.12 if h > w else h * 0.08)
    width = 22 if h > w else 46
    rows = ['[Script Info]', 'ScriptType: v4.00+', f'PlayResX: {w}', f'PlayResY: {h}', 'WrapStyle: 2', '', '[V4+ Styles]',
            'Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding',
            f'Style: Default,Arial,{font},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{max(font // 12, 2)},1,2,40,40,{margin},1',
            f'Style: Top,Arial,{round(font * 1.15)},&H0000F0FF,&H0000F0FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{max(font // 10, 3)},1,8,40,40,{round(h * 0.05)},1',
            '', '[Events]', 'Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text']
    for c in cues:
        text = (chr(92) + 'N').join(textwrap.wrap(c['text'], width)).replace('{', '(').replace('}', ')')
        rows.append(f'Dialogue: 0,{_ass_time(c["start"])},{_ass_time(c["end"])},{"Top" if c.get("top") else "Default"},,0,0,0,,{text}')
    work = output.parent;ass = work / (output.stem + '.ass');ass.write_text('\n'.join(rows) + '\n', encoding='utf-8')
    r = subprocess.run([ffmpeg_exe(), '-v', 'error', '-nostdin', '-y', '-i', str(Path(video).resolve()), '-vf', f'ass={ass.name}', '-c:v', 'libx264', '-crf', '17',
                        '-pix_fmt', 'yuv420p', '-c:a', 'copy', output.name], cwd=work, capture_output=True, text=True)
    if r.returncode:raise RuntimeError('caption burn failed: ' + r.stderr[:600])
    return {'path': str(output.resolve()), 'cues': len(cues), 'ass': str(ass.resolve())}
