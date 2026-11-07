#!/usr/bin/env python3
"""Rebuild E01 v4.3 final candidate v3 local zero-credit corrections.

Inputs are the already-approved generated/local clips in the workspace paths used
by the 2026-10-25 E01 rebuild. This script performs no paid API work.
"""
from pathlib import Path
import json
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path('/tmp/e01-v43-assembly')
PRO = Path('/tmp/e01-v43-lipsync-pro')
PROD = Path('/tmp/e01-v43-remaining-production-720p')
CONFORMED = ROOT / 'conformed'


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    raise RuntimeError("Historical custom assembler retired: it encoded unrelated globs after checking assets.json. Use run_pipeline.py assemble.")
    # Delivery gate (2026-10-25 FAILURE.TXT revision, project-documented):
    # 1. Every beat needs an approving, hash-current named-human review
    #    receipt; missing or stale receipts pause the build, a reviewer-marked
    #    absent scripted action rejects the beat. No receipts -> no assembly.
    # 2. The assembled file must pass mechanical checks (freeze, silence,
    #    levels); a defective assembly is removed, not shipped.
    # 3. Without an episode receipt (full playback + emotional listen) the
    #    output is a review candidate, never a finished episode.
    from microdrama.reviewgate import gate_check, load_receipts, evaluate_episode

    requirements = json.loads((Path(__file__).resolve().parent
                               / 'config' / 'E01_v43_gate_requirements.json').read_text())
    assets_path = ROOT / 'assets.json'
    receipts = load_receipts(ROOT / 'receipts')
    if not assets_path.is_file():
        raise SystemExit(
            'Delivery gate: assets.json (beat id -> shot video path) required at '
            f'{assets_path}; assembling from unreviewed globs is no longer allowed.')
    assets = json.loads(assets_path.read_text())
    gate = gate_check(requirements, assets, receipts)
    if not gate['all_approved']:
        print(json.dumps({'assembled': False, 'counts': gate['counts'],
                          'beats': [{'beat': b['beat'], 'status': b['status'],
                                     'reasons': b['reasons']} for b in gate['beats']]},
                         indent=2))
        raise SystemExit('Delivery gate: assembly paused or rejected; see per-beat status.')

    CONFORMED.mkdir(parents=True, exist_ok=True)

    # Shot10: remove the source-generated dark horizontal upper-background band
    # while preserving the dancers and floor-grid action.
    run([
        'ffmpeg', '-y', '-v', 'error', '-i', str(PRO / 'shot10-lines11-12-pro-01.mp4'),
        '-vf', 'crop=450:800:60:180,scale=720:1280,fps=24,setsar=1',
        '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
        str(CONFORMED / '10-shot10-pro.mp4'),
    ])

    # Shot11b: line 13 keeps the full marks view. Line 14 is intentionally
    # offscreen dialogue over a hands/marks-only insert, avoiding visible
    # closed-mouth speech on Harry.
    run([
        'ffmpeg', '-y', '-v', 'error', '-i', str(PROD / 'shot11b-marks-01.mp4'),
        '-t', '2.0', '-vf', 'scale=720:1280,fps=24,setsar=1',
        '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
        str(ROOT / 'shot11b-part1.mp4'),
    ])
    run([
        'ffmpeg', '-y', '-v', 'error', '-i', str(PROD / 'shot11b-marks-01.mp4'),
        '-ss', '2.0', '-vf', 'crop=450:800:120:450,scale=720:1280,fps=24,setsar=1',
        '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
        str(ROOT / 'shot11b-part2.mp4'),
    ])
    concat = ROOT / 'shot11b-concat.txt'
    concat.write_text(
        f"file '{ROOT / 'shot11b-part1.mp4'}'\n"
        f"file '{ROOT / 'shot11b-part2.mp4'}'\n"
    )
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat), '-c', 'copy', str(CONFORMED / '12-shot11b.mp4')])

    files = sorted(CONFORMED.glob('*.mp4'))
    final_concat = ROOT / 'concat-v3.txt'
    final_concat.write_text(''.join(f"file '{p}'\n" for p in files))
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(final_concat), '-c', 'copy', str(ROOT / 'base-video-v3.mp4')])
    final = Path('/tmp/Harry-Draconia-YuleBall-E01-v43-final-candidate-v3.mp4')
    run([
        'ffmpeg', '-y', '-v', 'error', '-i', str(ROOT / 'base-video-v3.mp4'),
        '-i', str(ROOT / 'final-audio-v2.m4a'), '-map', '0:v', '-map', '1:a',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
        str(final),
    ])

    # Post-assembly episode gate: measured defects remove the output.
    from microdrama.detectors import mechanical_report
    windows = [w for b in requirements['beats'] for w in b['lines']]
    mechanical = mechanical_report(final, dialogue_windows=windows)
    if mechanical['defects']:
        (ROOT / 'episode-mechanical-report.json').write_text(json.dumps(mechanical, indent=2))
        final.unlink()
        raise SystemExit('Delivery gate: assembled file has measured mechanical '
                         'defects; output removed, report at episode-mechanical-report.json')
    episode_receipt_path = ROOT / 'receipts' / 'episode.receipt.json'
    episode_receipt = json.loads(episode_receipt_path.read_text()) if episode_receipt_path.is_file() else None
    episode = evaluate_episode(final, episode_receipt, dialogue_windows=windows,
                               mechanical=mechanical)
    print(json.dumps({'assembled': True, 'episode_status': episode['status'],
                      'reasons': episode['reasons']}, indent=2))
    if episode['status'] != 'APPROVED':
        raise SystemExit(2)  # review candidate only, not a finished episode


if __name__ == '__main__':
    main()
