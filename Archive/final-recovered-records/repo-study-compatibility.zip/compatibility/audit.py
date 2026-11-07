"""Offline AST audit of a ViMax snapshot versus a supplied shot manifest.
Does not import or execute third-party code, call APIs, or claim media quality.
"""
import argparse, ast, hashlib, json
from pathlib import Path

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit(repo, manifest):
    source = repo / 'pipelines/script2video_pipeline.py'
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Script2VideoPipeline')
    method = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'generate_video_for_single_shot')
    call = next(n for n in ast.walk(method) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'generate_single_video')
    passed = sorted(k.arg for k in call.keywords if k.arg)
    keyword_expansion = any(k.arg is None for k in call.keywords)
    shots = json.loads(manifest.read_text())['shots']
    backend_path = repo / 'tools/video_generator_veo_google_api.py'
    backend_tree = ast.parse(backend_path.read_text())
    backend_method = next(n for n in ast.walk(backend_tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'generate_single_video')
    defaults = dict(zip([n.arg for n in backend_method.args.args][-len(backend_method.args.defaults):],
                        [ast.literal_eval(n) for n in backend_method.args.defaults]))
    controls = {
        'locked_audio_file': {'passed': any(k in passed for k in ('audio', 'audio_path', 'audio_file', 'audio_url')), 'required_on_visible_speech': True},
        'per_shot_seconds': {'passed': any(k in passed for k in ('duration', 'duration_seconds', 'seconds'))},
        'aspect_ratio': {'passed': 'aspect_ratio' in passed, 'required': '9:16'},
        'resolution': {'passed': 'resolution' in passed},
    }
    rows=[]
    for shot in shots:
        visible_speakers=sorted(set(shot.get('speakers',[])) & set(shot.get('visible_characters',[])))
        failures=[]
        if not controls['per_shot_seconds']['passed'] and shot.get('seconds') != defaults.get('duration'): failures.append('planned_duration_not_forwarded')
        if not controls['aspect_ratio']['passed'] and defaults.get('aspect_ratio') != '9:16': failures.append('vertical_aspect_not_forwarded')
        if visible_speakers and shot.get('line_ids') and not controls['locked_audio_file']['passed']: failures.append('locked_voice_waveform_not_forwarded')
        rows.append({'shot_id':shot['id'], 'planned_seconds':shot.get('seconds'), 'visible_speakers':visible_speakers,'blocking_mismatches':failures})
    return {'status':'incompatible_without_adapter' if any(r['blocking_mismatches'] for r in rows) else 'no_static_mismatch_found_not_runtime_verified',
            'analysis_kind':'source_AST_and_real_input_schema_not_generation',
            'source_manifest':str(manifest), 'manifest_sha256':sha(manifest), 'pipeline_sha256':sha(source),
            'call_keywords':passed,'keyword_expansion':keyword_expansion, 'backend_defaults':defaults,
            'required_controls':controls,'shots':rows,
            'summary':{'shots':len(rows),'planned_seconds':sum(s['seconds'] for s in shots),
                       'default_backend_seconds_without_adapter':len(rows)*defaults['duration'],
                       'visible_speech_shots':sum(bool(r['visible_speakers']) for r in rows),
                       'blocked_shots':sum(bool(r['blocking_mismatches']) for r in rows)},
            'caveat':'No repository code imported, no generation, no output-quality or current-production verdict. Manifest version must be checked separately.'}

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();result=audit(a.repo,a.manifest);a.out.write_text(json.dumps(result,indent=2));print(json.dumps(result['summary'],indent=2));print(result['status'])
