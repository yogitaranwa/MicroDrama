"""Production from an approved studio script: assets -> (first frame -> review -> video -> speech gate -> last frame) per shot -> score -> assembly.

Resumable and honest by construction:
* nothing starts without `approval.json` whose hash matches `story.json`; the approved cap is the ledger's hard cap;
* every start frame needs a review record made by a named reviewer (`accept_frame`); the pipeline never claims it looked at pixels itself;
* every video is transcribed straight away: a dialogue shot must say its line; a silent shot that gets invented speech is flagged and muted in assembly;
* the first dialogue shot that fails stops the run (a re-render costs credits, so it is the user's decision, with `--allow-rerender SHOT`);
* a failed or pending provider job is never resubmitted automatically.
The provider is behind a small `Runner` interface so the whole state machine is tested without spending anything.
"""
import collections
import datetime as dt
import json
import sqlite3
import time
from pathlib import Path

from .core import digest
from .directed import directed_prompt, first_frame_plan, keyframe_request
from .execution import RunLedger, signature
from . import native_mix as nm
from .studio import assets_to_make, check_approval

REVIEW_CHECKS = ('identity', 'wardrobe', 'action', 'expression', 'prop_orientation', 'layout')
IMAGE_COST = 50
SPEECH_FAIL_WER = 0.35


class Blocked(Exception):
    """The run cannot continue without a human: the message says exactly what is needed."""


# ---------------------------------------------------------------- the provider
class MagicHourRunner:
    """The guarded Magic Hour adapter: immutable manifest + approval token + SQLite ledger, per-job, hard cap, no auto-retry."""
    def __init__(self, out, key, cap, approval_text, batch_id):
        self.out, self.key, self.cap, self.approval_text, self.batch_id = Path(out), key, int(cap), approval_text, batch_id
        self.jobs_dir = self.out / 'jobs'
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = self.jobs_dir / 'spend.sqlite'

    def _adapter(self, jobs, ident, uploads=None):
        from .live import LiveAdapters
        mf, tf = self.jobs_dir / f'manifest-{ident}.json', self.jobs_dir / f'approval-{ident}.json'
        manifest = {'run_id': 'st-' + ident, 'batch_id': self.batch_id, 'jobs': jobs, 'uploads': uploads or []}
        if mf.exists():
            if signature(json.loads(mf.read_text())) != signature(manifest):raise Blocked('The job manifest for ' + ident + ' changed after it was written; refusing')
        else:
            mf.write_text(json.dumps(manifest, indent=2))
        if tf.exists():
            token = json.loads(tf.read_text())
        else:
            counts = {}
            for j in jobs:counts['magichour:' + j['kind']] = counts.get('magichour:' + j['kind'], 0) + 1
            token = {'run_id': manifest['run_id'], 'batch_id': self.batch_id, 'manifest_sha256': signature(manifest),
                     'expires_at': (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=12)).isoformat(), 'approval_reference': self.approval_text, 'job_counts': counts,
                     'totals': {'magichour:credits': str(sum(j['quote']['amount'] for j in jobs))} if jobs else {},
                     'magichour_credit_cap': self.cap, 'magichour_episode_credit_cap': self.cap,
                     'key_identities': {'magichour': 'image-video-key:restricted', 'elevenlabs': 'voice-key:approved'}}
            if any(j['kind'] == 'music' for j in jobs):
                token['magichour_music_approved'] = True
                token['key_identities']['magichour'] = 'image-video-music-key:approved'
            tf.write_text(json.dumps(token, indent=2))
        return LiveAdapters(manifest, token, RunLedger(self.ledger), {'magichour': self.key}, True, sleep=time.sleep)

    def upload(self, path):
        path = Path(path)
        h = digest(path)
        cache = self.jobs_dir / f'upload-{h}.json'
        if cache.exists():return json.loads(cache.read_text())['file_path']
        for attempt in range(4):  # uploads are free and idempotent; generation jobs are never retried
            try:
                fp = self._adapter([], 'upload-' + h[:20], [{'sha256': h, 'kind': 'image'}]).upload(path, 'image')
                break
            except Exception as e:
                if attempt == 3 or ('SSL' not in type(e).__name__ + str(e)[:200] and 'Connection' not in type(e).__name__):raise
                time.sleep(5 * (attempt + 1))
        cache.write_text(json.dumps({'file_path': fp, 'sha256': h, 'kind': 'image'}))
        return fp

    def _job(self, ident, kind, amount, endpoint, body, **extra):
        today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date().isoformat()
        return {'id': ident, 'episode_id': 'ep1', 'provider': 'magichour', 'kind': kind,
                'quote': {'amount': amount, 'unit': 'credits', 'verified_on': today, 'source_url': 'https://docs.magichour.ai/api-reference/models'},
                'request': {'endpoint': endpoint, 'body': body}, **extra}

    def state(self, ident):
        if not self.ledger.exists():return None
        try:
            row = sqlite3.connect(self.ledger).execute('SELECT state FROM execution WHERE run=? AND job=?', ('st-' + ident, ident)).fetchone()
        except sqlite3.OperationalError:
            return None
        return row[0] if row else None

    def _run(self, j, output, polls=180):
        st = self.state(j['id'])
        if st in ('error', 'submitted'):
            raise Blocked(f"{j['id']} is '{st}' in the ledger: it may have been charged. Reconcile it (read the provider project, download if complete) before anything is resubmitted")
        try:
            self._adapter([j], j['id']).execute(j['id'], output, polls=polls)
        except TimeoutError:
            raise Blocked(j['id'] + ' is still pending at the provider; the same project is retained, do not resubmit')
        except Exception as e:
            raise Blocked(f"{j['id']} stopped: {type(e).__name__} {str(e)[:300]}")

    def image(self, ident, prompt, refs, output):
        body = {'name': 'Studio ' + ident, 'model': 'nano-banana-2.1', 'image_count': 1, 'resolution': '1k', 'aspect_ratio': '16:9', 'style': {'prompt': prompt}}
        if refs:
            body['assets'] = {'image_file_paths': [self.upload(r) for r in refs]}
        self._run(self._job(ident, 'image', IMAGE_COST, '/v1/ai-image-editor' if refs else '/v1/ai-image-generator', body), output)

    def video(self, ident, prompt, frame, seconds, model, output, evidence):
        body = {'name': 'Studio ' + ident, 'model': model, 'resolution': '720p', 'end_seconds': seconds, 'audio': True, 'assets': {'image_file_path': self.upload(frame)}, 'style': {'prompt': prompt}}
        self._run(self._job(ident, 'video', nm.quote_native_video(model, '720p', seconds)['amount'], '/v1/image-to-video', body, image_evidence=evidence), output)

    def music(self, ident, seconds, prompt, output):
        m = nm.plan_music(seconds, prompt)
        self._run(self._job(ident, 'music', m['quote']['amount'], m['endpoint'], m['body']), output)

    def balance(self):
        import requests
        return requests.get('https://api.magichour.ai/v1/account', headers={'Authorization': 'Bearer ' + self.key}, timeout=30).json()['credits']


# ---------------------------------------------------------------- checks that run on real media (injectable for tests)
def speech_gate(video, lines):
    """What the clip says against what it should say. Dialogue: WER and extra words. Silent: at most one stray word."""
    from .intelligibility import check_script, transcribe
    if lines:
        g = check_script(video, lines)
        extra = len(g['heard'].split()) - len(g['expected'].split())
        return {'kind': 'dialogue', 'wer': g['wer'], 'extra_words': extra, 'heard': g['heard'], 'expected': g['expected'], 'pass': g['wer'] <= SPEECH_FAIL_WER and extra <= 1}
    heard = ' '.join(w['text'] for w in transcribe(video))
    return {'kind': 'silent', 'heard': heard, 'pass': len(heard.split()) <= 1}


def last_frame(video, output):
    return nm.extract_frame(video, output)


# ---------------------------------------------------------------- the state machine
class Producer:
    def __init__(self, out, runner, model='kling-3.0', gate=speech_gate, extract=last_frame, assemble=None, allow_rerender=()):
        self.out, self.runner, self.model, self.gate, self.extract = Path(out), runner, model, gate, extract
        self.assemble_fn, self.allow = assemble, collections.Counter(allow_rerender)  # each occurrence authorises one paid re-render of that shot
        self.approval = check_approval(self.out)
        self.story = json.loads((self.out / 'story.json').read_text(encoding='utf-8'))
        self.pack = json.loads((self.out / 'pack.json').read_text(encoding='utf-8'))
        self.plan = {p['id']: p for p in first_frame_plan(self.story)}
        for d in ('assets', 'frames', 'reviews', 'clips', 'gates', 'layouts'):(self.out / d).mkdir(exist_ok=True)

    # -- paths
    def asset(self, key):return self.out / 'assets' / (key + '.png')
    def frame(self, sid):return self.out / 'frames' / (sid + '.png')
    def review(self, sid):return self.out / 'reviews' / (sid + '.json')
    def clip(self, sid):return self.out / 'clips' / (sid + '.mp4')
    def gate_file(self, sid):return self.out / 'gates' / (sid + '.json')
    def last(self, sid):return self.out / 'clips' / (sid + '-last.png')
    def score(self):return self.out / 'assets' / 'score.mp3'
    def film(self):return self.out / 'film' / 'film.mp4'

    def shots(self):return self.story['shots']
    def takes(self, sid):return len(list((self.out / 'clips').glob(sid + '-take*.mp4')))

    # -- what is needed next
    def next_action(self):
        for key in assets_to_make(self.pack, None):
            if not self.asset(key).exists():return {'action': 'asset', 'key': key}
        for i, s in enumerate(self.shots()):
            sid = s['id']
            if self.clip(sid).exists():
                g = json.loads(self.gate_file(sid).read_text()) if self.gate_file(sid).exists() else None
                if g is None:return {'action': 'gate', 'shot': sid}
                if not g['pass'] and g['kind'] == 'dialogue':
                    if self.takes(sid) < self.allow[sid]:return {'action': 'rerender', 'shot': sid}
                    return {'action': 'blocked', 'shot': sid, 'why': f"dialogue shot {sid} failed its speech check (heard: {g['heard']!r}, expected: {g['expected']!r}). Re-rendering costs credits: review, then rerun with --allow-rerender {sid}"}
                continue
            ff = self.plan[sid]
            if not self.frame(sid).exists():
                if ff['mode'] == 'continue' and ff['from_shot'] and not self.last(ff['from_shot']).exists():return {'action': 'blocked', 'shot': sid, 'why': 'previous last frame missing'}
                return {'action': 'frame', 'shot': sid, 'mode': ff['mode']}
            if not self.review(sid).exists():return {'action': 'review', 'shot': sid, 'frame': str(self.frame(sid))}
            return {'action': 'video', 'shot': sid}
        if not self.score().exists():return {'action': 'music'}
        if not self.film().exists():return {'action': 'assemble'}
        return {'action': 'done', 'film': str(self.film())}

    # -- doing it
    def step(self):
        a = self.next_action()
        kind = a['action']
        if kind == 'asset':self.make_asset(a['key'])
        elif kind == 'frame':self.make_frame(a['shot'])
        elif kind == 'video':self.make_video(a['shot'])
        elif kind == 'rerender':self.rerender(a['shot'])
        elif kind == 'gate':self.run_gate(a['shot'])
        elif kind == 'music':self.make_music()
        elif kind == 'assemble':self.make_film()
        return a

    def run(self, max_steps=200):
        """Run until a human is needed, something failed, or the film is done. Returns the last action."""
        for _ in range(max_steps):
            a = self.next_action()
            if a['action'] in ('review', 'blocked', 'done'):return a
            try:
                self.step()
            except Blocked as e:
                return {'action': 'blocked', 'why': str(e), 'at': a}
        return {'action': 'blocked', 'why': 'step limit reached'}

    def make_asset(self, key):
        self.runner.image('asset-' + key, assets_to_make(self.pack, None)[key], [], self.asset(key))

    def ref_path(self, ref, sid):
        i = [s['id'] for s in self.shots()].index(sid)
        if ref == 'room-plate' or ref == self.story['plate']['id']:return self.asset('room-plate')
        if ref in self.story['portraits']:return self.asset(self.story['portraits'][ref].replace('.png', ''))
        if ref == 'previous_last_frame':return self.last(self.shots()[i - 1]['id'])
        if ref.startswith('last:'):return self.last(ref[5:])
        if ref.startswith('layout:'):
            from .blocking import render_layout
            path = self.out / 'layouts' / (ref[7:] + '.png')
            if not path.exists():render_layout(self.story['plan'], ref[7:], 'start', size=(1280, 720)).save(path)
            return path
        raise Blocked('Unknown reference ' + ref)

    def make_frame(self, sid):
        i = [s['id'] for s in self.shots()].index(sid)
        req = keyframe_request(self.story, i)
        if req is None:  # same angle and people: the previous real last frame is this shot's first frame
            import shutil
            shutil.copyfile(self.last(self.plan[sid]['from_shot']), self.frame(sid))
            return
        n = len(list(self.frame(sid).parent.glob(sid + '.rejected*')))  # a regenerated frame is a new paid job with a new id (the old job's manifest is immutable)
        self.runner.image('frame-' + sid + (f'-v{n + 1}' if n else ''), req['prompt'], [self.ref_path(r, sid) for r in req['refs']], self.frame(sid))

    def evidence(self, sid):
        rec = json.loads(self.review(sid).read_text())
        frame = self.frame(sid)
        if rec['sha256'] != digest(frame):raise Blocked(f'The start frame of {sid} changed after it was reviewed; review it again')
        p_ = {'tasks': [{'id': 'frame-' + sid}], 'uploaded_local_references': {}}
        p_['plan_sha256'] = signature(p_)
        item = {'path': str(frame.resolve()), 'sha256': rec['sha256'], 'plan_sha256': p_['plan_sha256'], 'reviewer': rec['reviewer'], 'reviewed_at': rec['reviewed_at'],
                'checks': rec['checks'], 'note': rec.get('note', '')}
        return {'plan': p_, 'accepted': {'frame-' + sid: item}}

    def make_video(self, sid, take=None):
        i = [x['id'] for x in self.shots()].index(sid)
        out = self.clip(sid)
        self.runner.video(sid if take is None else f'{sid}-t{take}', directed_prompt(self.story, i), self.frame(sid), self.shots()[i]['seconds'], self.model, out, self.evidence(sid))
        self.extract(out, self.last(sid))

    def rerender(self, sid):
        """One authorised paid re-render: the failed take is kept as clips/<shot>-takeN.mp4 with its gate result, then a new job (new id) is made."""
        n = self.takes(sid) + 1
        self.clip(sid).rename(self.out / 'clips' / f'{sid}-take{n}.mp4')
        self.gate_file(sid).rename(self.out / 'gates' / f'{sid}.take{n}.json')
        if self.last(sid).exists():self.last(sid).unlink()
        self.make_video(sid, take=n + 1)

    def run_gate(self, sid):
        s = self.shots()[[x['id'] for x in self.shots()].index(sid)]
        lines = [d['line'] for d in s['sound'].get('dialogue', []) or []]
        self.gate_file(sid).write_text(json.dumps(self.gate(self.clip(sid), lines), indent=1))

    def make_music(self):
        total = len(self.shots()) * self.shots()[0]['seconds']
        self.runner.music('score', total, 'Sparse, tense, quiet instrumental score for a small intimate drama in one room: low sustained strings and a slow soft piano pulse, slowly building, then a hush. No drums, no vocals, no melody that steals attention.', self.score())

    def make_film(self):
        if self.assemble_fn is None:raise Blocked('No assembler configured')
        muted = [s['id'] for s in self.shots() if not s['sound'].get('dialogue') and self.gate_file(s['id']).exists() and not json.loads(self.gate_file(s['id']).read_text())['pass']]
        self.film().parent.mkdir(exist_ok=True)
        self.assemble_fn(self, muted)


def accept_frame(out, shot_id, reviewer, checks=None, note=''):
    """A named person (or Claude, having looked at the actual pixels) records that this start frame was reviewed. Without it no video is paid for."""
    out = Path(out)
    frame = out / 'frames' / (shot_id + '.png')
    if not frame.exists():raise ValueError('No start frame for ' + shot_id)
    if not str(reviewer).strip():raise ValueError('A reviewer name is required')
    checks = {k: bool((checks or {}).get(k, True)) for k in REVIEW_CHECKS}
    if not all(checks.values()):raise ValueError('A frame with a failed check cannot be accepted: ' + ', '.join(k for k, v in checks.items() if not v))
    rec = {'shot': shot_id, 'sha256': digest(frame), 'reviewer': reviewer, 'reviewed_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'checks': checks, 'note': note}
    (out / 'reviews' / (shot_id + '.json')).write_text(json.dumps(rec, indent=1))
    return rec


def reject_frame(out, shot_id):
    """Deletes a start frame so it will be generated again (this costs an image credit; the old file is kept as .rejected)."""
    out = Path(out)
    frame = out / 'frames' / (shot_id + '.png')
    if frame.exists():frame.rename(frame.with_suffix(f'.rejected{len(list(frame.parent.glob(shot_id + ".rejected*"))) + 1}.png'))
    r = out / 'reviews' / (shot_id + '.json')
    if r.exists():r.unlink()


def status(out):
    out = Path(out)
    story = json.loads((out / 'story.json').read_text(encoding='utf-8'))
    rows = []
    for s in story['shots']:
        sid = s['id']
        g = json.loads((out / 'gates' / (sid + '.json')).read_text()) if (out / 'gates' / (sid + '.json')).exists() else None
        rows.append({'shot': sid, 'frame': (out / 'frames' / (sid + '.png')).exists(), 'reviewed': (out / 'reviews' / (sid + '.json')).exists(),
                     'clip': (out / 'clips' / (sid + '.mp4')).exists(), 'gate': None if g is None else ('pass' if g['pass'] else 'FAIL')})
    return rows


# ---------------------------------------------------------------- assembly (needs ffmpeg; exercised by real films, see tests for the synthetic check)
def assemble_film(prod, muted):
    """Join the clips: invented speech in silent shots replaced by the room's own ambience, gentle measured colour match, ducked score, ASR-timed captions, hook and end card."""
    import shutil
    import subprocess
    import av
    import numpy as np
    from .intelligibility import transcribe
    story, out = prod.story, prod.out
    ids = [s['id'] for s in story['shots']]
    files = {i: prod.clip(i) for i in ids}
    work = out / 'film'
    work.mkdir(exist_ok=True)
    if muted:
        tone = work / 'tone.wav'
        if tone.exists():tone.unlink()
        nm.extract_room_tone([files[s['id']] for s in story['shots'] if s['sound'].get('dialogue')] or list(files.values()), tone, seconds=0.8)
        for i in muted:
            clean = work / (i + '-clean.mp4')
            if clean.exists():clean.unlink()
            subprocess.run([nm.ffmpeg_exe(), '-v', 'error', '-y', '-i', str(files[i]), '-stream_loop', '-1', '-i', str(tone), '-map', '0:v', '-map', '1:a', '-t', str(story['shots'][ids.index(i)]['seconds']),
                            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', str(clean)], check=True)
            files[i] = clean

    def mean_rgb(path):
        c = av.open(str(path))
        fr = [f.to_ndarray(format='rgb24')[::6, ::6] for k, f in enumerate(c.decode(video=0)) if k % 12 == 0]
        c.close()
        return np.mean([f.reshape(-1, 3).mean(0) for f in fr], axis=0) / 255
    means = {i: mean_rgb(files[i]) for i in ids}
    target = np.mean(list(means.values()), axis=0)
    grade = {i: dict(zip('rgb', (round(float(v), 2) for v in np.clip(1 + 0.5 * (target / m - 1), 0.8, 1.25)))) for i, m in means.items()}
    shots = [{'path': str(files[i]), 'sha256': digest(files[i]), 'frames': round(s['seconds'] * 24), 'source_start_frame': 0, 'overlap_frames': 0, 'pixel_checked': True, 'grade': grade[i]} for i, s in zip(ids, story['shots'])]
    build = work / 'build'
    shutil.rmtree(build, ignore_errors=True)
    size = (1280, 720)
    result = nm.assemble_native_episode({'shots': shots, 'music': [{'path': str(prod.score()), 'sha256': digest(prod.score()), 'gain': 0.55, 'start_seconds': 0, 'steady': True}]}, build, size=size)
    cues = []
    for row, s in zip(result['timeline']['shots'], story['shots']):
        lines = [d['line'] for d in s['sound'].get('dialogue', []) or []]
        if not lines:continue
        words = [{'start': float(x['start']), 'end': float(x['end'])} for x in transcribe(files[s['id']])]
        span = nm.speech_span(files[s['id']], 0.0, row['frames'] / 24)
        t0 = row['start_frame'] / 24
        start = span[0] if span else (words[0]['start'] if words else 0.5)
        end = max(words[-1]['end'] if words else 0.0, span[1] if span else 0.0)
        cues.append({'start': round(t0 + start, 2), 'end': round(t0 + min(end + 0.25, row['frames'] / 24), 2), 'text': ' '.join(lines)})
    cues.append({'start': 0.0, 'end': 3.0, 'text': story['hook_title'], 'top': True})
    cues.append({'start': result['duration'] - 2.6, 'end': result['duration'], 'text': story['end_card'], 'top': True})
    final = nm.burn_captions(result['path'], cues, build / 'captioned.mp4', size)
    shutil.copyfile(final['path'], prod.film())
    (work / 'report.json').write_text(json.dumps({'duration': result['duration'], 'frames': result['frames'], 'lufs': result['mechanical']['integrated_lufs'], 'defects': result['mechanical']['defects'],
                                                  'muted_silent_shots': muted, 'grade': grade, 'cues': cues}, indent=1))
    return {'film': str(prod.film()), 'duration': result['duration'], 'defects': result['mechanical']['defects']}
