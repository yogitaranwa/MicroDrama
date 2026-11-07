"""Local end-to-end dry run for the reference-to-video route. No network, keys or spend.

Reads the real hash-bound Harry+Draconia reference bank and the E01 shot list,
classifies every shot (R2V-eligible vs exact-audio-required), builds a validated
manifest for the eligible shots against placeholder upload paths, and prints
exact per-model comparison quotes.

    python examples/r2v/dry_run.py

Placeholder uploads are marked NOT_UPLOADED: a real run replaces them with
api-assets paths from the live upload phase after manifest approval.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from magicdrama.audiofirst import r2v

ROOT = Path(__file__).resolve().parent


def main():
    bank = json.loads((ROOT / 'harry-draconia-reference-bank.json').read_text())
    episode = json.loads((ROOT / 'e01-shots.json').read_text())
    uploads = {r['id']: {'file_path': 'api-assets/NOT_UPLOADED/' + r['id'] + '.png',
                         'sha256': r['sha256']}
               for r in bank['references']}

    eligible, spoken = [], []
    for shot in episode['shots']:
        speakers = set(shot.get('speakers', [])) & set(shot.get('visible_characters', []))
        (spoken if shot.get('line_ids') and speakers else eligible).append(shot)

    print('Episode %s: %d shots, %d R2V-eligible (no visible speech), %d need exact-audio routes'
          % (episode['id'], len(episode['shots']), len(eligible), len(spoken)))
    print('Spoken shots (exact-audio route owns these, NOT this manifest):',
          ', '.join(s['id'] for s in spoken) or 'none')
    print()

    planned = {'id': episode['id'], 'shots': eligible}
    for shot in eligible:
        refs = r2v.select_shot_references(shot, bank, uploads)
        print('%s (%ss, %s): references -> %s'
              % (shot['id'], shot['seconds'], shot['framing'],
                 ', '.join('@' + r['name'] for r in refs)))

    manifest = r2v.reference_video_manifest(planned, bank, uploads, 'dry-run', 'dry-batch',
                                            'minimax-h3', '720p')
    print()
    print('Manifest: %d job(s), status %s' % (len(manifest['jobs']), manifest['status']))
    for job in manifest['jobs']:
        print(' ', job['id'], job['request']['endpoint'], job['request']['body']['model'],
              job['quote']['amount'], job['quote']['unit'])

    print()
    report = r2v.compare_route_quotes(planned, bank,
                                      models=('minimax-h3', 'seedance-2.0-mini', 'seedance-2.0', 'seedance-2.5'))
    print('Route quote comparison @720p (%s, comparison only, not an order):' % report['verified_on'])
    for model, row in report['models'].items():
        if row['status'] == 'quoted':
            print('  %-18s %6d credits' % (model, row['credits']))
        else:
            print('  %-18s %s: %s' % (model, row['status'], row.get('reason', '')))


if __name__ == '__main__':
    main()
