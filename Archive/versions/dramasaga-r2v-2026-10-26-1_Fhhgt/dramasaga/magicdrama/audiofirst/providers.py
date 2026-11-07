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
    # Reference-to-video (/v1/text-to-video with named references) is planned
    # and validated in r2v.py against the verified catalog in
    # magichour_catalog.py; it is not a fixed-audio route and has no accepted
    # result in this project.
    'magichour_reference_to_video': Capabilities(False, False, False, False),
}


def video_request(route, shot, audio_asset, image_asset=None, video_asset=None):
    if route not in CAPABILITIES:
        raise ValueError('Unknown route')
    if route == 'magichour_reference_to_video':
        raise ValueError('Build reference-to-video requests with r2v.build_r2v_request / '
                         'r2v.reference_video_manifest; this legacy builder carries no named references')
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
