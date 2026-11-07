"""Lossless adapter for the existing v9 project script schema.

Does not rewrite dialogue, add story beats, or select a new script. Converts
`loc/speaker/text` to the existing shot planner's `location/lines` shape.
"""
from copy import deepcopy
from .registry import IntegrationError


def normalize_v9(script):
    if not isinstance(script, dict) or not script.get('shots'):
        raise IntegrationError('script must contain shots')
    locations = script.get('locations', {})
    normalized = []
    seen = set()
    for src in script['shots']:
        n = src['n']
        if n in seen:
            raise IntegrationError(f'duplicate shot number: {n}')
        seen.add(n)
        loc = locations.get(src.get('loc'))
        if not loc or not loc.get('name'):
            raise IntegrationError(f'shot {n}: unknown location')
        text, speaker = src.get('text'), src.get('speaker')
        if bool(text) != bool(speaker):
            raise IntegrationError(f'shot {n}: speaker and text must be paired')
        lines = []
        if text:
            lines.append({'speaker': speaker, 'text': text,
                          'emotion': src.get('emotion'),
                          'source_seconds': src.get('seconds')})
        normalized.append({'n': n, 'location': loc['name'],
            'camera': src.get('camera', ''), 'action': src.get('action', ''),
            'seconds': src['seconds'], 'lines': lines,
            'source_kind': src.get('kind'), 'source': deepcopy(src)})
    return normalized
