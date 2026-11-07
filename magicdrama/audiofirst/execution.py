"""Explicit run approvals and durable no-repeat ledger. Not an identity/auth service."""
import datetime as dt
import hashlib
import json
import sqlite3
from decimal import Decimal, InvalidOperation
from .core import identifier


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def money(value):
    if isinstance(value, bool): raise ValueError('Boolean cost not allowed')
    try: x=Decimal(str(value))
    except InvalidOperation as e: raise ValueError('Invalid cost') from e
    if not x.is_finite() or x < 0: raise ValueError('Finite nonnegative cost required')
    return x


def verify_approval(manifest, token, enabled=False, now=None):
    if enabled is not True: raise RuntimeError('Live execution refused by default')
    now=now or dt.datetime.now(dt.timezone.utc)
    expires=dt.datetime.fromisoformat(token.get('expires_at','').replace('Z','+00:00'))
    if expires.tzinfo is None or now>=expires: raise ValueError('Approval expired or missing timezone')
    if expires-now > dt.timedelta(days=1): raise ValueError('Approval must expire within 24 hours')
    for field in ('run_id','batch_id'):
        identifier(manifest[field],field)
        if token.get(field)!=manifest[field]: raise ValueError('Approval identity mismatch')
    if not token.get('approval_reference') or token.get('manifest_sha256')!=signature(manifest):
        raise ValueError('Exact approved manifest hash and source evidence required')
    jobs=manifest['jobs']; ids=[j['id'] for j in jobs]
    if len(set(ids))!=len(ids): raise ValueError('Duplicate job ID')
    unresolved={j['id']:set(j.get('depends_on',[])) for j in jobs}
    resolved=set()
    while unresolved:
        ready={key for key,deps in unresolved.items() if deps<=resolved}
        if not ready:raise ValueError('Cyclic or missing job dependency')
        resolved.update(ready)
        unresolved={key:deps for key,deps in unresolved.items() if key not in ready}
    totals={};counts={};episodes={};image_counts={}
    for j in jobs:
        identifier(j['id'],'job id');identifier(j['episode_id'],'episode id')
        provider=j['provider'];amount=money(j['quote']['amount']);unit=j['quote']['unit']
        if provider not in ('magichour','elevenlabs'): raise ValueError('Unknown provider')
        if j['quote'].get('verified_on') != now.astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30))).date().isoformat():
            raise ValueError('Quote must be reverified on current India date')
        if not j['quote'].get('source_url','').startswith('https://'): raise ValueError('Quote provenance missing')
        if amount<=0: raise ValueError('Positive verified quote required, no free assumption')
        if provider=='magichour':
            if unit!='credits' or amount!=amount.to_integral_value(): raise ValueError('Magic Hour integer credits required')
            if j['kind']=='voice':
                if token.get('magichour_voice_approved') is not True:
                    raise ValueError('Magic Hour voice requires separate explicit approval')
                req=j['request'];style=req['body'].get('style',{})
                prompt=style.get('prompt','')
                if req['endpoint']=='/v1/ai-voice-cloner':
                    # a cloned voice may only come from audio this project generated (never a real person's recording) and is priced per exact character
                    sample=req['body'].get('assets',{}).get('audio_file_path','')
                    if j.get('voice_source')!='project_generated_audio':raise ValueError('Voice cloning only from project-generated audio')
                    if not isinstance(sample,str) or not sample.startswith('api-assets/') or style.get('voice_name') or not isinstance(prompt,str) or not 1<=len(prompt)<=1000:
                        raise ValueError('Invalid Magic Hour voice clone request')
                elif req['endpoint']!='/v1/ai-voice-generator' or not isinstance(prompt,str) or not 1<=len(prompt)<=1000 or not style.get('voice_name'):
                    raise ValueError('Invalid Magic Hour voice request')
                expected=(Decimal(len(prompt))/10).to_integral_value(rounding='ROUND_CEILING')
                if amount!=expected:raise ValueError('Magic Hour voice quote must match exact submitted characters')
            elif j['kind']=='music':
                if token.get('magichour_music_approved') is not True:
                    raise ValueError('Magic Hour music requires separate explicit approval')
                req=j['request'];body=req['body'];duration=body.get('duration');style=body.get('style',{})
                if req['endpoint']!='/v1/ai-music-generator' or type(duration) is not int or not 15<=duration<=300 or style.get('instrumental') is not True or not isinstance(style.get('prompt'),str) or not style['prompt'].strip():
                    raise ValueError('Only explicit instrumental Magic Hour music supported')
                if amount!=duration:raise ValueError('Magic Hour music quote must match requested seconds')
            elif j['kind'] not in ('image','video'): raise ValueError('restricted image/video key image/video only')
            episodes[j['episode_id']]=episodes.get(j['episode_id'],Decimal(0))+amount
            if j['kind']=='image':image_counts[j['episode_id']]=image_counts.get(j['episode_id'],0)+1
        else:
            if j['kind']!='voice' or unit!='characters': raise ValueError('ElevenLabs exact submitted-character quote required')
            count=sum(len(i['text']) for i in j['request']['body']['inputs'])
            if amount!=count: raise ValueError('Tagged dialogue count differs from approval quote')
        if provider=='elevenlabs':
            billing=j['quote'].get('billing',{})
            if billing.get('unit') not in ('credits','INR','USD') or money(billing.get('max_amount',0))<=0 or not billing.get('rate_verified'):
                raise ValueError('Voice requires verified maximum billing cost as well as character count')
        key=provider+':'+unit;totals[key]=totals.get(key,Decimal(0))+amount
        counts[provider+':'+j['kind']]=counts.get(provider+':'+j['kind'],0)+1
    image_cap=manifest.get('image_cap_per_episode',12)
    if type(image_cap) is not int or not 1<=image_cap<=60 or any(n>image_cap for n in image_counts.values()):raise ValueError('Per-episode image cap exceeded')
    billing={j['id']:j['quote']['billing'] for j in jobs if j['provider']=='elevenlabs'}
    if token.get('billing_limits',{})!=billing:raise ValueError('Voice billing limits not explicitly approved')
    if token.get('job_counts')!=counts or token.get('totals')!={k:str(v) for k,v in totals.items()}:
        raise ValueError('Exact job counts and costs not approved')
    mh_identity='image-video-voice-key:approved' if token.get('magichour_voice_approved') is True else 'image-video-key:restricted'
    if token.get('magichour_music_approved') is True:
        mh_identity='image-video-voice-music-key:approved' if token.get('magichour_voice_approved') is True else 'image-video-music-key:approved'
    if token.get('key_identities')!={'magichour':mh_identity,'elevenlabs':'voice-key:approved'}:
        raise ValueError('Wrong key identities')
    credit_cap=token.get('magichour_credit_cap',30000)
    if type(credit_cap) is not int or not 1<=credit_cap<=30000:raise ValueError('Invalid Magic Hour credit cap')
    episode_cap=token.get('magichour_episode_credit_cap',3000)
    if type(episode_cap) is not int or not 1<=episode_cap<=30000:raise ValueError('Invalid Magic Hour episode credit cap')
    if any(x>episode_cap for x in episodes.values()) or totals.get('magichour:credits',0)>credit_cap:
        raise ValueError('Manifest exceeds hard episode/batch cap')
    return {'totals':totals,'counts':counts}


class RunLedger:
    def __init__(self,path):
        self.db=sqlite3.connect(path,timeout=10,isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS execution (batch TEXT,run TEXT,job TEXT,episode TEXT,provider TEXT,hash TEXT,quote TEXT,actual TEXT,state TEXT,result TEXT,PRIMARY KEY(run,job))')
        self.db.execute('CREATE TABLE IF NOT EXISTS voice_reservations (batch TEXT,run TEXT,job TEXT,unit TEXT,amount TEXT,PRIMARY KEY(run,job))')
    def close(self):self.db.close()
    def reserve(self,manifest,token,enabled=False):
        verify_approval(manifest,token,enabled)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            existing=self.db.execute('SELECT job,hash,batch FROM execution WHERE run=?',(manifest['run_id'],)).fetchall()
            if existing:
                missing_voice = self.db.execute('SELECT count(*) FROM execution e WHERE e.run=? AND e.provider=? AND NOT EXISTS (SELECT 1 FROM voice_reservations v WHERE v.run=e.run AND v.job=e.job)', (manifest['run_id'],'elevenlabs')).fetchone()[0]
                if missing_voice:raise ValueError('Legacy voice reservations lack billing ceilings; reconcile ledger before resume')
                if any(row[2] != manifest['batch_id'] for row in existing) or {row[0]:row[1] for row in existing}!={j['id']:signature(j) for j in manifest['jobs']}:raise ValueError('Run manifest changed; never overwrite reservations')
                self.db.execute('COMMIT');return
            rows=self.db.execute('SELECT episode,quote,actual FROM execution WHERE batch=? AND provider=?',(manifest['batch_id'],'magichour')).fetchall()
            by={};total=Decimal(0)
            for ep,q,a in rows:
                cost=max(money(q),money(a));by[ep]=by.get(ep,Decimal(0))+cost;total+=cost
            for j in manifest['jobs']:
                if j['provider']=='magichour':
                    c=money(j['quote']['amount']);ep=j['episode_id'];by[ep]=by.get(ep,Decimal(0))+c;total+=c
            if total>token.get('magichour_credit_cap',30000) or any(c>token.get('magichour_episode_credit_cap',3000) for c in by.values()):raise ValueError('Existing reservations/actuals exceed combined episode/batch cap')
            voice_jobs = [j for j in manifest['jobs'] if j['provider']=='elevenlabs']
            if voice_jobs:
                limits = token.get('batch_billing_limits', {})
                amounts = {}
                for unit, amount in self.db.execute('SELECT unit,amount FROM voice_reservations WHERE batch=?', (manifest['batch_id'],)).fetchall():
                    amounts[unit] = amounts.get(unit, Decimal(0)) + money(amount)
                for j in voice_jobs:
                    billing = j['quote']['billing']; unit = billing['unit']
                    amounts[unit] = amounts.get(unit, Decimal(0)) + money(billing['max_amount'])
                if set(limits) != set(amounts) or any(money(limits[unit]) < amount for unit,amount in amounts.items()):
                    raise ValueError('Explicit cumulative batch voice billing ceiling required; existing uncertain jobs stay reserved')
                for j in voice_jobs:
                    b = j['quote']['billing']
                    self.db.execute('INSERT INTO voice_reservations VALUES (?,?,?,?,?)', (manifest['batch_id'],manifest['run_id'],j['id'],b['unit'],str(money(b['max_amount']))))
            for j in manifest['jobs']:
                self.db.execute('INSERT INTO execution VALUES (?,?,?,?,?,?,?,?,?,?)',(manifest['batch_id'],manifest['run_id'],j['id'],j['episode_id'],j['provider'],signature(j),str(j['quote']['amount']),'0','reserved',None))
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK');raise
    def get(self,run,job):
        row=self.db.execute('SELECT state,result,quote,actual FROM execution WHERE run=? AND job=?',(run,job)).fetchone()
        return dict(zip(('state','result','quote','actual'),row)) if row else None
    def transition(self,run,job,old,new,result=None,actual=None):
        allowed = {'reserved': {'submitting'}, 'submitting': {'unknown', 'submitted'}, 'submitted': {'complete', 'error', 'overcharge'}}
        if new not in allowed.get(old, set()):raise ValueError('Illegal execution state transition')
        if actual is not None:money(actual)
        row=self.get(run,job)
        if not row or row['state']!=old:raise ValueError('Unexpected job state')
        changed=self.db.execute('UPDATE execution SET state=?,result=?,actual=? WHERE run=? AND job=? AND state=?',
                        (new,json.dumps(result) if result is not None else row['result'],str(actual) if actual is not None else row['actual'],run,job,old)).rowcount
        if changed!=1:raise RuntimeError('Concurrent state change; stop instead of duplicate execution')
    def halt_overcharge(self,batch):
        return self.db.execute("SELECT count(*) FROM execution WHERE batch=? AND state='overcharge'",(batch,)).fetchone()[0]>0
