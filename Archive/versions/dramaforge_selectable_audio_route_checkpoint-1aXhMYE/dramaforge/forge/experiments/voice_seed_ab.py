"""Matched ElevenLabs seed experiment, held until generation is permitted.
A pair can show seed sensitivity for one voice/text, not prove a universal cause.
"""
import hashlib
import json
from pathlib import Path
from forge.integrations.registry import IntegrationError


def prepare_voice_seed_ab(*, text, voice_id, voice_settings, output_dir,
                          seeds=(42,43), model='eleven_multilingual_v2'):
    if not isinstance(text,str) or not text.strip(): raise IntegrationError('text required')
    if not isinstance(voice_id,str) or not voice_id.strip(): raise IntegrationError('voice ID required')
    if not isinstance(voice_settings,dict):raise IntegrationError('voice settings mapping required')
    if not 2 <= len(seeds) <= 4 or len(set(seeds))!=len(seeds) or any(type(s) is not int or not 0<=s<2**32 for s in seeds):
        raise IntegrationError('need2-4 distinct unsigned32bit seeds')
    # Reuse actual client validation WITHOUT sending or reserving anything.
    from forge.audio.tts import ElevenLabsFinal
    class ValidateOnlyLedger:
        def reserve(self,*args):raise _Validated()
    for seed in seeds:
        try:ElevenLabsFinal('',voice_id,char_ledger=ValidateOnlyLedger(),model=model).say(
            text,'unused',voice_settings=voice_settings,seed=seed)
        except _Validated:pass
    out=Path(output_dir).resolve()
    runs=[dict(seed=s,output=str(out/('seed_%d_raw.mp3'%s))) for s in seeds]
    if any(Path(r['output']).exists() for r in runs):raise IntegrationError('existing experiment output, do not regenerate')
    params=dict(text=text,voice_id=voice_id,voice_settings=dict(voice_settings),model=model,runs=runs)
    fingerprint=hashlib.sha256(json.dumps(params,sort_keys=True).encode()).hexdigest()
    return dict(parameters=params,fingerprint=fingerprint,status='prepared_not_executed',
                characters_required=len(text)*len(seeds),quality_status='unreviewed',
                verdict_scope='seed sensitivity on this voice/text/model only; best-effort determinism')


class _Validated(Exception):pass


def execute_voice_seed_ab(experiment, *, project_dir, api_key, ledger):
    from forge.guard.generation_hold import require_generation_open
    from forge.audio.tts import ElevenLabsFinal
    require_generation_open(project_dir=project_dir,ledger_path=ledger.path)
    p=experiment['parameters'];runs=p['runs']
    fresh=prepare_voice_seed_ab(text=p['text'],voice_id=p['voice_id'],voice_settings=p['voice_settings'],
        output_dir=Path(runs[0]['output']).parent,seeds=tuple(r['seed'] for r in runs),model=p['model'])
    if fresh!=experiment:raise IntegrationError('experiment parameters changed after preparation')
    if ledger.remaining()<experiment['characters_required']:raise IntegrationError('pair exceeds remaining approved character budget')
    out=Path(runs[0]['output']).parent;out.mkdir(parents=True,exist_ok=True)
    receipts=out/'experiment_receipts.json'
    if receipts.exists():raise IntegrationError('existing/partial experiment: reconcile instead of rerunning')
    state={'fingerprint':experiment['fingerprint'],'runs':[],'status':'started_not_reviewed'}
    client=ElevenLabsFinal(api_key,p['voice_id'],char_ledger=ledger,model=p['model'])
    for run in runs:
        require_generation_open(project_dir=project_dir,ledger_path=ledger.path)
        row=dict(run,status='request_pending');state['runs'].append(row);receipts.write_text(json.dumps(state,indent=2))
        client.say(p['text'],run['output'],voice_settings=p['voice_settings'],seed=run['seed'])
        row.update(status='generated_unreviewed',sha256=hashlib.sha256(Path(run['output']).read_bytes()).hexdigest())
        receipts.write_text(json.dumps(state,indent=2))
    state['status']='generated_unreviewed';receipts.write_text(json.dumps(state,indent=2))
    return state
