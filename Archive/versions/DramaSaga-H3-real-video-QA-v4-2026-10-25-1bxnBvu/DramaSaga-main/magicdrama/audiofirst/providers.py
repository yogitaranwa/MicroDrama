from dataclasses import dataclass
from pathlib import Path
from .core import finite


@dataclass(frozen=True)
class Capabilities:
    fixed_audio: bool
    timed_pins: bool
    multiple_speakers_verified: bool
    live_tested: bool


CAPABILITIES = {
    'magichour_audio_to_video': Capabilities(True, False, False, False),
    'magichour_lip_sync': Capabilities(True, False, False, False),
    'magichour_image_to_video': Capabilities(False, False, False, False),
    # Live-verified 2026-10-25: Magic Hour text-to-video exposes MiniMax H3 with image/video/audio references.
    'magichour_h3_reference_to_video': Capabilities(True, False, False, True),
}


def video_request(route, shot, audio_asset, image_asset=None, video_asset=None, reference_assets=None, *, experimental=False):
    if route not in CAPABILITIES:
        raise ValueError('Unknown route')
    capabilities = CAPABILITIES[route]
    if shot.get('pins') and not capabilities.timed_pins:
        raise ValueError('Timed frame pins are not supported by this verified contract')
    if not capabilities.fixed_audio:
        raise ValueError('Native audio toggle is not a fixed-audio input')
    duration = finite(shot['seconds'], 'seconds', 0.01)
    if duration <= 0 or duration > 30:
        raise ValueError('Conservative test limit is 30 seconds; provider maximum is unverified')
    if not audio_asset:
        raise ValueError('Accepted audio asset required')
    if route == 'magichour_audio_to_video':
        return {'endpoint': '/v1/audio-to-video', 'body': {
            'assets': {'audio_file_path': audio_asset, **({'image_file_path': image_asset} if image_asset else {})},
            'start_seconds': 0, 'end_seconds': duration, 'resolution': '720p',
            'style': {'prompt': shot['prompt']}}, 'live_enabled': False,
            'unverified': ['model identity', 'multi-speaker sync', 'fixed waveform preservation']}
    if route == 'magichour_h3_reference_to_video':
        if not experimental:
            raise ValueError('Magic Hour H3 reference video failed measured speaker/lip-sync QA on 2026-10-25; experimental request construction requires experimental=True and remains disabled for production')
        references = list(reference_assets or [])
        if image_asset:
            references.insert(0, {'file_path': image_asset, 'name': 'scene'})
        references.append({'file_path': audio_asset, 'name': 'voice'})
        if not any(r.get('name') != 'voice' for r in references):
            raise ValueError('H3 reference video requires at least one visual reference')
        if len(references) > 10:
            raise ValueError('Magic Hour reference video accepts at most 10 references')
        names = [r.get('name') for r in references]
        if any(not n or not str(n).replace('-', '_').isalnum() for n in names) or len(names) != len(set(names)):
            raise ValueError('Reference names must be unique alphanumeric names')
        return {'endpoint': '/v1/text-to-video', 'body': {
            'model': 'minimax-h3', 'resolution': shot.get('resolution', '480p'), 'aspect_ratio': shot.get('aspect_ratio', '9:16'),
            'audio': True, 'end_seconds': duration, 'references': references,
            'style': {'prompt': shot['prompt']}}, 'live_enabled': False,
            'unverified': ['per-speaker lip sync', 'exact waveform preservation', 'long-scene identity drift'],
            'experimental_only': True, 'qa_status': 'failed_audiovisual_sync_2026-10-25'}
    if len(shot['visible_characters']) != 1 or len(set(shot['speakers'])) != 1 or shot['speakers'][0] != shot['visible_characters'][0]:
        raise ValueError('Lip-sync fallback requires exactly one visible, matching speaker')
    if not video_asset:
        raise ValueError('Lip-sync requires source video')
    return {'endpoint': '/v1/lip-sync', 'body': {
        'assets': {'audio_file_path': audio_asset, 'video_file_path': video_asset, 'video_source': 'file'},
        'start_seconds': 0, 'end_seconds': duration, 'max_fps_limit': 24,
        'style': {'generation_mode': 'lite'}}, 'live_enabled': False,
        'unverified': ['quality on generated actors', 'emotional motion match']}


def submit_live(*args, **kwargs):
    raise RuntimeError('Paid execution is disabled in this release. A separately approved, quoted capability test is required.')
