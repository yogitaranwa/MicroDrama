#!/usr/bin/env python3
"""Rebuild E01 v4.3 final candidate v3 local zero-credit corrections.

Inputs are the already-approved generated/local clips in the workspace paths used
by the 2026-10-25 E01 rebuild. This script performs no paid API work.
"""
from pathlib import Path
import subprocess

ROOT = Path('/tmp/e01-v43-assembly')
PRO = Path('/tmp/e01-v43-lipsync-pro')
PROD = Path('/tmp/e01-v43-remaining-production-720p')
CONFORMED = ROOT / 'conformed'


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
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
    run([
        'ffmpeg', '-y', '-v', 'error', '-i', str(ROOT / 'base-video-v3.mp4'),
        '-i', str(ROOT / 'final-audio-v2.m4a'), '-map', '0:v', '-map', '1:a',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
        '/tmp/Harry-Draconia-YuleBall-E01-v43-final-candidate-v3.mp4',
    ])


if __name__ == '__main__':
    main()
