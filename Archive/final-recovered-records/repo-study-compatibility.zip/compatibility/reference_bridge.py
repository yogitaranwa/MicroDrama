"""Reversible no-network camera/reference bridge. Original local implementation.
ViMax-inspired dependency provenance, without its default renderer or agent shell.
No source images are fabricated and missing views are never relabeled.
"""
import hashlib, json
from pathlib import Path

def signature(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def compile_camera_plan(shots, cameras, bank, files, approved_audio):
    refs={r['id']:r for r in bank['references']}
    if len(refs)!=len(bank['references']): raise ValueError('Duplicate reference id')
    by_shot={s['id']:s for s in shots}
    if len(by_shot)!=len(shots): raise ValueError('Duplicate shot id')
    by_camera={c['id']:c for c in cameras}
    if len(by_camera)!=len(cameras): raise ValueError('Duplicate camera id')
    membership={}
    for camera in cameras:
        for sid in camera['shots']:
            if sid not in by_shot or sid in membership: raise ValueError('Missing or duplicate camera shot')
            membership[sid]=camera['id']
        parent=camera.get('parent_camera')
        anchor=camera.get('parent_shot')
        if parent is not None:
            if parent not in by_camera or anchor not in by_camera[parent]['shots']: raise ValueError('Parent shot must belong to parent camera')
            if by_shot[anchor]['location']!=by_shot[camera['shots'][0]]['location']: raise ValueError('Cannot chain reference across locations')
        elif anchor is not None: raise ValueError('Root camera cannot have parent shot')
        visited=set(); current=camera['id']
        while current is not None:
            if current in visited: raise ValueError('Camera cycle')
            visited.add(current); current=by_camera[current].get('parent_camera')
    if set(membership)!=set(by_shot): raise ValueError('Every shot needs one explicit camera')
    def bind(ref):
        path=Path(files[ref['id']])
        got=hashlib.sha256(path.read_bytes()).hexdigest()
        if got!=ref['sha256']: raise ValueError('Reference hash mismatch: '+ref['id'])
        return {'id':ref['id'],'path':str(path),'sha256':got,'views':ref['views']}
    rows=[]
    for s in shots:
        chosen=[]
        for char in s['visible_characters']:
            candidates=[r for r in refs.values() if r['kind']=='character' and r.get('characters')==[char] and s['framing'] in r['views'] and r.get('primary')]
            if len(candidates)!=1: raise ValueError('Explicit primary view missing or ambiguous: '+s['id']+'/'+char)
            chosen.append(bind(candidates[0]))
        locations=[r for r in refs.values() if r['kind']=='location' and r.get('location')==s['location'] and r.get('primary')]
        if len(locations)!=1: raise ValueError('Explicit primary location missing or ambiguous')
        chosen.append(bind(locations[0]))
        audio=[]
        for line in s.get('line_ids',[]):
            rec=approved_audio.get(line)
            if not rec: raise ValueError('Approved audio missing for '+line)
            actual=hashlib.sha256(Path(rec['path']).read_bytes()).hexdigest()
            if actual!=rec['sha256']: raise ValueError('Audio hash mismatch')
            audio.append({'line_id':line,**rec})
        row={'shot_id':s['id'],'camera_id':membership[s['id']],'location':s['location'],'seconds':s['seconds'],
             'aspect_ratio':'9:16','reference_bindings':chosen,'locked_audio':audio,
             'visible_speech':bool(set(s.get('speakers',[])) & set(s['visible_characters'])),
             'camera_anchor':by_camera[membership[s['id']]].get('parent_shot'),
             'status':'prepared_not_rendered_not_quality_accepted'}
        row['content_id']=signature(row);rows.append(row)
    return {'shots':rows,'plan_sha256':signature(rows),'live_enabled':False,'note':'Camera parents are supplied, not inferred. Reference coverage does not prove visual consistency.'}
