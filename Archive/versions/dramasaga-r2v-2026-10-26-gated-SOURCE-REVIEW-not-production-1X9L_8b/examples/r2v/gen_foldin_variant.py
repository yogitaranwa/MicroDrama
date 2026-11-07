"""Build the FOLD-IN staging variant (proposal only - NOT the canonical manifest).

Head plan: wordless head beat + dialogue beat (per-beat billing, 2s unit minimum).
Fold-in:   one dialogue unit per shot; the canon lead-in action rides inside the
           unit as an explicit "0-<off>s lead-in:" and the approved take starts at
           audio_offset_s = the shot's real frame-grid slack. Bills shot_s exactly.
e01 s16 keeps its real 2.0s crash insert (a genuine separate visual, not a lead-in).
Reads shot-manifest-wan30.json (head plan), writes shot-manifest-wan30.foldin.json.
"""
import json, math, sys
sys.path.insert(0, '.')
import stages as ST, production_runner as pr

m = json.load(open('shot-manifest-wan30.json'))
W = json.load(open('/tmp/take_windows.json')) if False else None  # takes already audited; slack comes from the head beats
converted = 0
for s in m['shots']:
    if not s.get('beats') or not s.get('audio'):
        continue
    if s['episode'] == 'e01' and s['shot'] == 16:
        continue  # real crash insert stays a beat
    bs = s['beats']
    dia = [b for b in bs if b['carries_line']]
    if len(dia) != 1:
        continue
    d = dia[0]
    head = [b for b in bs if b['id'] < d['id'] and not b['carries_line']]
    if not head:
        continue
    h = head[0]
    off = s.get('audio_offset_s') or 0.0
    assert abs(h['dur_s'] - off) < 1e-9, (s['episode'], s['shot'])
    tail = [b for b in bs if b['id'] > d['id']]
    lead = h['action'].rstrip('.')
    d['lead_in_s'] = off
    d['action'] = "0-%ss lead-in: %s. Then the line: %s" % ("%g" % off, lead, d['action'])
    d['frame'] = h['frame']  # the unit starts on the lead-in visual, not the speaking close-up
    d['dur_s'] = s['shot_s'] - sum(b['dur_s'] for b in tail)
    s['beats'] = [d] + tail
    for i, b in enumerate(s['beats']):
        b['id'] = i + 1
    converted += 1
m['total_cr_staged'] = sum(sum(ST.next_gen_s(b['dur_s']) for b in s['beats']) if s.get('beats') else s['billing_s'] for s in m['shots']) * 96
m['variant'] = "fold-in lead-in proposal (not canonical; heads plan remains shot-manifest-wan30.json)"
json.dump(m, open('shot-manifest-wan30.foldin.json', 'w'), indent=1)
errs = [(s['episode'], s['shot'], ST.validate_beats(s, known_refs=pr.REF_FILES)) for s in m['shots']]
errs = [e for e in errs if e[2]]
print("converted:", converted, "| staged:", m['total_cr_staged'], "| validate:", errs or "CLEAN")
