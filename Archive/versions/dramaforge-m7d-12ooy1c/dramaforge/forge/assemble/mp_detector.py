"""MediaPipe FaceMesh stand-in for LatentSync's InsightFace detector (commercial-safe).

LatentSync's affine_transform only reads a few landmark groups from the 106-point
array: brow centres (43,48,49,51,50 and 101-105) and the nose centre (74,77,83,86).
We fill those slots from MediaPipe FaceMesh (Apache-2.0) points, then add a
per-region offset (in units of face width) calibrated against InsightFace on the
same frames, so the crop matches the baseline.

STATUS: re-created after a sandbox wipe from the documented design and the logged
calibration. The tested original lived in the Kaggle payload. Re-run the
Draconia SSIM check (baseline 0.991) before shipping.
"""
import numpy as np

# Calibration run: 13 frames, mean (dx, dy) in face-width units per region.
CALIB_MEAN = {"left_brow": (0.0286, 0.0485), "right_brow": (-0.0705, 0.0180), "nose": (-0.0232, -0.1060)}
CALIB_STD = {"left_brow": (0.0121, 0.0104), "right_brow": (0.0187, 0.0113), "nose": (0.0121, 0.0223)}

# MediaPipe FaceMesh indices for the region centres (standard topology).
MP_LEFT_BROW = [70, 63, 105, 66, 107]
MP_RIGHT_BROW = [336, 296, 334, 293, 300]
MP_NOSE = [1, 2, 98, 327]

LS_BROW_SLOTS = [43, 48, 49, 51, 50] + list(range(101, 106))
LS_NOSE_SLOTS = [74, 77, 83, 86]


def _centre(pts, idx):
    return pts[idx].mean(axis=0)


def landmarks_106(image_bgr):
    """Return a (106, 2) array in pixel coordinates, or None if no face is found."""
    import cv2
    import mediapipe as mp

    h, w = image_bgr.shape[:2]
    with mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=False) as fm:
        res = fm.process(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    if not res.multi_face_landmarks:
        return None
    pts = np.array([[p.x * w, p.y * h] for p in res.multi_face_landmarks[0].landmark])
    face_w = np.ptp(pts[:, 0])
    out = np.zeros((106, 2))
    lb = _centre(pts, MP_LEFT_BROW) + np.array(CALIB_MEAN["left_brow"]) * face_w
    rb = _centre(pts, MP_RIGHT_BROW) + np.array(CALIB_MEAN["right_brow"]) * face_w
    nose = _centre(pts, MP_NOSE) + np.array(CALIB_MEAN["nose"]) * face_w
    for i, s in enumerate(LS_BROW_SLOTS):
        out[s] = lb if i < len(LS_BROW_SLOTS) // 2 else rb
    for s in LS_NOSE_SLOTS:
        out[s] = nose
    return out
