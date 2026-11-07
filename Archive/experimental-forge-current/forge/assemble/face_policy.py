"""Face-coverage policy for lip-sync: profile poses and multi-face shots are
caught BEFORE a lip-sync run, not discovered in review.

The shipping detector (forge/assemble/mp_detector.py) is validated on one
front-facing subject only; its own doc says profile and multi-face shots are
untested. This module is the shot-level policy that classifies detections so
such shots are routed to human review instead of silently mis-synced. It is
pure numpy over landmark/box detections, so the policy is fully testable
offline; the model-level validation on real profile and multi-face footage
still belongs to the Kaggle lip-sync runs (docs/LIPSYNC_PLAN.md).

Landmark indices follow MediaPipe FaceMesh, which mp_detector.py emits.
"""
import numpy as np

NOSE_TIP = 1
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 263
FOREHEAD = 10
CHIN = 152

# A face is front-on when the shorter nose-to-eye span is at least this
# fraction of the longer one. Below it, one side of the face is turning away.
FRONT_MIN_RATIO = 0.6
# A second face this large relative to the main face makes a shot multi-face.
AMBIGUOUS_FACE_RATIO = 0.25
# Verdict thresholds over the sampled frames of one shot.
MAX_NO_FACE_FRACTION = 0.2
MAX_PROFILE_FRACTION = 0.5


def _pt(landmarks, idx):
    return np.asarray(landmarks[idx], dtype=float)


def face_width(landmarks) -> float:
    xs = np.asarray(landmarks, dtype=float)[:, 0]
    return float(xs.max() - xs.min())


def box_area(box) -> float:
    x1, y1, x2, y2 = [float(v) for v in box]
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def classify_pose(landmarks) -> dict:
    """front / profile from nose-to-eye-corner symmetry. Profile direction
    names the side of the face more visible to the camera."""
    lm = np.asarray(landmarks, dtype=float)
    if lm.ndim != 2 or lm.shape[0] <= max(NOSE_TIP, LEFT_EYE_OUTER, RIGHT_EYE_OUTER) or lm.shape[1] < 2:
        raise ValueError("landmarks must be an (N, 2+) array covering the FaceMesh indices")
    nose = _pt(lm, NOSE_TIP)[:2]
    d_left = float(np.linalg.norm(nose - _pt(lm, LEFT_EYE_OUTER)[:2]))
    d_right = float(np.linalg.norm(nose - _pt(lm, RIGHT_EYE_OUTER)[:2]))
    longer, shorter = max(d_left, d_right), min(d_left, d_right)
    ratio = shorter / longer if longer > 0 else 0.0
    if ratio >= FRONT_MIN_RATIO:
        return {"pose": "front", "symmetry": round(ratio, 3)}
    side = "left" if d_left > d_right else "right"
    return {"pose": "profile", "visible_side": side, "symmetry": round(ratio, 3)}


def select_face(detections) -> dict:
    """Which face a lip-sync run would take, and whether the shot is really
    multi-face. detections: [{'landmarks': (N,2), 'box': (x1,y1,x2,y2)}]."""
    if not detections:
        return {"index": None, "n_faces": 0, "ambiguous": False}
    areas = [box_area(d.get("box", (0, 0, 0, 0))) for d in detections]
    main = int(np.argmax(areas))
    ambiguous = any(i != main and a >= AMBIGUOUS_FACE_RATIO * areas[main]
                    for i, a in enumerate(areas) if areas[main] > 0)
    return {"index": main, "n_faces": len(detections), "ambiguous": ambiguous,
            "main_area": areas[main]}


def classify_shot(frames, min_face_fraction: float = 1.0 - MAX_NO_FACE_FRACTION,
                  max_profile_fraction: float = MAX_PROFILE_FRACTION) -> dict:
    """One shot's per-frame detections -> a lip-sync routing verdict.

    frames: list (sampled frames) of detection lists as select_face takes.
    verdict 'ok': single front face in enough frames. 'review': face missing
    in too many frames, or profile poses beyond the tolerated fraction - a
    human must look before syncing. 'unsupported': genuinely multi-face
    frames, which the shipping detector has never been validated on."""
    n = len(frames)
    if n == 0:
        raise ValueError("classify_shot needs at least one sampled frame")
    no_face, multi, profile = [], [], []
    for i, dets in enumerate(frames):
        sel = select_face(dets)
        if sel["index"] is None:
            no_face.append(i)
            continue
        if sel["n_faces"] > 1 and sel["ambiguous"]:
            multi.append(i)
        pose = classify_pose(dets[sel["index"]]["landmarks"])
        if pose["pose"] == "profile":
            profile.append(i)
    reasons = []
    if multi:
        reasons.append(f"multi-face frames: {multi}")
    if len(no_face) / n > 1.0 - min_face_fraction:
        reasons.append(f"no face in {len(no_face)}/{n} sampled frames: {no_face}")
    if len(profile) / n > max_profile_fraction:
        reasons.append(f"profile pose in {len(profile)}/{n} sampled frames: {profile}")
    if multi:
        verdict = "unsupported"
    elif reasons:
        verdict = "review"
    else:
        verdict = "ok"
    return {"verdict": verdict, "reasons": reasons,
            "frames": n, "no_face": no_face, "multi_face": multi,
            "profile": profile}
