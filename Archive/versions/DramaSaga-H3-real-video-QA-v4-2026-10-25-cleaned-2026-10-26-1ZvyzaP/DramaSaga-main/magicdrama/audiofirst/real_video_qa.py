"""Real rendered-video face, identity-screen and mouth-aperture extraction.

This module is deliberately fail-closed: missing faces, ambiguous faces and
unknown identity remain failures.  YuNet supplies detector scores, SFace
supplies identity similarity, and MediaPipe supplies raw mouth geometry.  None
of those values is a calibrated confidence score, identity proof, or phoneme
match.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Iterable


def _sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _require_file(path: str | Path, label: str) -> Path:
    p = Path(path)
    if not p.is_file():
        raise ValueError(f'{label} model/file required: {p}')
    return p


def _mouth_open(landmarks) -> float:
    def distance(a: int, b: int) -> float:
        pa, pb = landmarks[a], landmarks[b]
        return math.hypot(pa.x - pb.x, pa.y - pb.y)
    width = distance(61, 291)
    if width <= 1e-6:
        raise ValueError('Degenerate mouth landmarks')
    return distance(13, 14) / width


def _padded_box(face, width: int, height: int, padding: float) -> tuple[int, int, int, int]:
    x, y, w, h = [float(v) for v in face[:4]]
    px, py = w * padding, h * padding
    x0 = max(0, int(math.floor(x - px)))
    y0 = max(0, int(math.floor(y - py)))
    x1 = min(width, int(math.ceil(x + w + px)))
    y1 = min(height, int(math.ceil(y + h + py)))
    if x1 <= x0 or y1 <= y0:
        raise ValueError('Invalid face box')
    return x0, y0, x1, y1


def extract_real_video_mouth_track(
    video_path: str | Path,
    dialogue_lines: list[dict],
    reference_images: dict[str, list[str | Path]],
    *,
    face_landmarker_path: str | Path,
    yunet_path: str | Path,
    sface_path: str | Path,
    audio_path: str | Path | None = None,
    target_step_seconds: float = 0.04,
    min_detector_score: float = 0.60,
    min_face_width_px: float = 48.0,
    min_identity_score: float = 0.50,
    min_identity_margin: float = 0.10,
    max_seconds: float = 180.0,
    model_provenance: dict | None = None,
) -> dict:
    """Extract a dense real-video mouth/identity-screen track.

    The returned track maps requested 25 Hz observation times to the nearest
    decoded frame.  If the video itself is 24 fps, those are still only 24 fps
    pixels; the track records the actual decoded frame count, source frame and
    sampling error instead of pretending padded frames exist.
    """
    if target_step_seconds != 0.04:
        raise ValueError('Real-video QA requires 25 Hz / 0.04s target sampling')
    if not 0 < min_detector_score <= 1:
        raise ValueError('Detector threshold must be in (0, 1]')
    if not 0 < min_identity_score <= 1 or not 0 <= min_identity_margin <= 1:
        raise ValueError('Invalid identity screen thresholds')
    video = _require_file(video_path, 'Rendered video')
    face_model = _require_file(face_landmarker_path, 'MediaPipe face-landmarker')
    yunet_model = _require_file(yunet_path, 'YuNet')
    sface_model = _require_file(sface_path, 'SFace')
    if not dialogue_lines:
        raise ValueError('Dialogue lines required')
    if not reference_images or any(not v for v in reference_images.values()):
        raise ValueError('At least one reference image per speaker required')
    for line in dialogue_lines:
        if float(line['start']) < 0 or float(line['end']) <= float(line['start']) or not line.get('speaker'):
            raise ValueError('Invalid dialogue line timing/speaker')
        if line['speaker'] not in reference_images:
            raise ValueError(f'No reference images for speaker {line["speaker"]}')
    try:
        import cv2
        import mediapipe as mp
        import numpy as np
        from mediapipe.tasks.python import vision
    except ImportError as exc:
        raise ValueError('Install pinned official PyPI mediapipe and opencv-contrib-python first') from exc

    detector = cv2.FaceDetectorYN.create(str(yunet_model), '', (320, 320), min_detector_score, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(str(sface_model), '')
    landmarker = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(face_model)),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.30,
        min_face_presence_confidence=0.30,
        min_tracking_confidence=0.30,
    ))

    def detect_faces(image):
        height, width = image.shape[:2]
        detector.setInputSize((width, height))
        ok, faces = detector.detect(image)
        if faces is None:
            return []
        return [f for f in faces.tolist() if float(f[-1]) >= min_detector_score and float(f[2]) >= min_face_width_px]

    def face_feature(image, face):
        aligned = recognizer.alignCrop(image, np.array(face[:-1], dtype=np.float32))
        return recognizer.feature(aligned)

    reference_features: dict[str, list[dict]] = {}
    reference_failures = []
    for speaker, paths in reference_images.items():
        reference_features[speaker] = []
        for raw_path in paths:
            path = _require_file(raw_path, f'{speaker} reference')
            image = cv2.imread(str(path))
            if image is None:
                raise ValueError(f'Unreadable reference image: {path}')
            faces = detect_faces(image)
            if not faces:
                reference_failures.append(f'{speaker}: no usable face in {path.name}')
                continue
            # The reference path is owner-labeled.  Within that image choose the
            # largest detected face rather than inventing identity from pixels.
            face = max(faces, key=lambda f: float(f[2]) * float(f[3]))
            reference_features[speaker].append({
                'path': str(path), 'sha256': _sha256(path), 'detector_score': float(face[-1]),
                'feature': face_feature(image, face),
            })
        if not reference_features[speaker]:
            raise ValueError(f'No usable reference face for {speaker}: ' + '; '.join(reference_failures))

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError(f'Cannot decode rendered video: {video}')
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    decoded_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    reported_duration = float(cap.get(cv2.CAP_PROP_DURATION) or 0) if hasattr(cv2, 'CAP_PROP_DURATION') else 0.0
    if not fps > 0 or decoded_frames <= 0:
        cap.release()
        raise ValueError('Rendered video must expose fps and decoded frame count')
    actual_duration = decoded_frames / fps
    max_line_end = max(float(line['end']) for line in dialogue_lines)
    if max_line_end > actual_duration + target_step_seconds:
        cap.release()
        raise ValueError('Dialogue extends beyond decoded rendered video')
    if actual_duration > max_seconds:
        cap.release()
        raise ValueError('Rendered video exceeds QA duration limit')
    target_count = int(math.floor(max_line_end / target_step_seconds + 1e-9)) + 1
    target_entries: dict[int, dict] = {}
    target_errors: dict[int, float] = {}
    frame_index = -1

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_index += 1
        frame_time = frame_index / fps
        target_index = int(round(frame_time / target_step_seconds))
        if target_index < 0 or target_index >= target_count:
            if frame_time > max_line_end + 0.05:
                break
            continue
        target_time = target_index * target_step_seconds
        error = abs(frame_time - target_time)
        if target_index in target_errors and error >= target_errors[target_index]:
            continue
        height, width = frame.shape[:2]
        detected = detect_faces(frame)
        observations = []
        for face_index, face in enumerate(detected):
            feature = face_feature(frame, face)
            similarities = {}
            for speaker, refs in reference_features.items():
                similarities[speaker] = max(
                    float(recognizer.match(feature, ref['feature'], cv2.FaceRecognizerSF_FR_COSINE))
                    for ref in refs
                )
            ranked = sorted(similarities.items(), key=lambda item: item[1], reverse=True)
            best_speaker, best_score = ranked[0]
            second_score = ranked[1][1] if len(ranked) > 1 else -1.0
            margin = best_score - second_score
            identity_matched = best_score >= min_identity_score and margin >= min_identity_margin
            x0, y0, x1, y1 = _padded_box(face, width, height, 0.35)
            crop = frame[y0:y1, x0:x1]
            mouth_visible = False
            mouth_open = None
            mouth_failure = 'identity_not_matched'
            if identity_matched:
                rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                landmarks_result = landmarker.detect(mp_image)
                if len(landmarks_result.face_landmarks) == 1:
                    try:
                        mouth_open = _mouth_open(landmarks_result.face_landmarks[0])
                        mouth_visible = True
                        mouth_failure = None
                    except ValueError as exc:
                        mouth_failure = str(exc)
                elif not landmarks_result.face_landmarks:
                    mouth_failure = 'mouth_landmarks_missing'
                else:
                    mouth_failure = 'mouth_landmarks_ambiguous'
            observations.append({
                't': round(target_time, 6),
                'speaker_id': best_speaker if identity_matched else f'unknown-{face_index}',
                'face_visible': bool(identity_matched),
                'mouth_visible': bool(mouth_visible),
                'mouth_open': mouth_open,
                'identity_status': 'matched' if identity_matched else 'unknown_or_ambiguous',
                'identity_screened': bool(identity_matched),
                'identity_verified': False,
                'identity_similarity': round(best_score, 6),
                'identity_margin': round(margin, 6),
                'identity_scores': {k: round(v, 6) for k, v in similarities.items()},
                'detector_score': round(float(face[-1]), 6),
                'bbox_xywh': [round(float(v), 3) for v in face[:4]],
                'mouth_failure': mouth_failure,
                'source_frame_index': frame_index,
                'source_frame_seconds': round(frame_time, 6),
                'sample_time_error_seconds': round(error, 6),
            })
        target_entries[target_index] = {'observations': observations, 'detections': len(detected)}
        target_errors[target_index] = error
    cap.release()
    landmarker.close()

    entries = []
    frame_summaries = []
    speakers = sorted(reference_images)
    for target_index in range(target_count):
        t = round(target_index * target_step_seconds, 6)
        item = target_entries.get(target_index)
        if item is None:
            frame_summaries.append({'t': t, 'decoded_frame': None, 'failure': 'no decoded frame near target sample'})
            continue
        observations = item['observations']
        entries.extend(observations)
        by_speaker = {speaker: [o for o in observations if o['speaker_id'] == speaker] for speaker in speakers}
        frame_summaries.append({
            't': t,
            'decoded_frame': observations[0]['source_frame_index'] if observations else None,
            'decoded_frame_count': decoded_frames,
            'detected_faces': item['detections'],
            'matched': {speaker: len(items) for speaker, items in by_speaker.items() if items},
            'ambiguous_speakers': [speaker for speaker, items in by_speaker.items() if len(items) > 1],
            'max_sample_time_error_seconds': max((o['sample_time_error_seconds'] for o in observations), default=None),
        })

    model_hashes = {
        'face_landmarker_sha256': _sha256(face_model),
        'yunet_sha256': _sha256(yunet_model),
        'sface_sha256': _sha256(sface_model),
    }
    return {
        'video_sha256': _sha256(video),
        'audio_sha256': _sha256(audio_path) if audio_path else None,
        'source': {
            'kind': 'validated_local_extractor',
            'engine': 'opencv-yunet+sface and mediapipe-face-landmarker',
            'status_detail': 'detector_score_identity_similarity_and_raw_mouth_aperture_not_calibrated_confidence_identity_proof_or_phoneme_matching',
            'models': model_hashes,
            'model_provenance': model_provenance or {},
            'thresholds': {
                'min_detector_score': min_detector_score,
                'min_face_width_px': min_face_width_px,
                'min_identity_score': min_identity_score,
                'min_identity_margin': min_identity_margin,
            },
        },
        'video': {
            'fps': fps,
            'decoded_frame_count': decoded_frames,
            'decoded_duration_seconds': round(actual_duration, 6),
            'container_duration_seconds': round(reported_duration, 6),
            'target_sample_rate_hz': 25,
            'target_sample_step_seconds': target_step_seconds,
            'nearest_decoded_frame_mapping': True,
        },
        'references': {
            speaker: [{k: v for k, v in ref.items() if k != 'feature'} for ref in refs]
            for speaker, refs in reference_features.items()
        },
        'dialogue_lines': dialogue_lines,
        'entries': entries,
        'frame_summaries': frame_summaries,
    }


def write_real_video_mouth_track(out_path: str | Path, *args, **kwargs) -> dict:
    result = extract_real_video_mouth_track(*args, **kwargs)
    out = Path(out_path)
    if out.exists():
        raise ValueError('Fresh output path required')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n')
    return result
