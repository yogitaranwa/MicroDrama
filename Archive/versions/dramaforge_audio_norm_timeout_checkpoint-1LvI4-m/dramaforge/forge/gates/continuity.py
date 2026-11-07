"""Continuity check: does a rendered shot still match its locked still?

Free, local, PIL-only. Two signals, combined:
- colour-histogram intersection (wardrobe/location colours survive)
- coarse luminance-grid L1 (broad layout survives)

This is an automated FLAG for the human review, not a verdict: a shot that
trips the threshold must be eyeballed against the locked still before it is
accepted. That eyeball pass is exactly what earlier drafts skipped.
"""

GRID = 16
BINS = 8


def frame_features(image_path, box=None) -> dict:
    """Feature vector for one still/frame. box: relative (l, t, r, b) crop,
    e.g. the torso region for wardrobe checks. Needs Pillow."""
    from PIL import Image
    img = Image.open(image_path).convert("RGB")
    if box is not None:
        w, h = img.size
        img = img.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
    img = img.resize((64, 64))
    px = list(img.getdata())
    hist = [0.0] * (BINS * BINS * BINS)
    step = 256 // BINS
    for r, g, b in px:
        hist[(r // step) * BINS * BINS + (g // step) * BINS + (b // step)] += 1.0
    total = float(len(px))
    hist = [c / total for c in hist]
    gray = img.convert("L").resize((GRID, GRID))
    grid = [v / 255.0 for v in gray.getdata()]
    return {"hist": hist, "grid": grid}


def histogram_intersection(a, b) -> float:
    return sum(min(x, y) for x, y in zip(a, b))


def grid_l1(a, b) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def drift_score(feat_a: dict, feat_b: dict) -> float:
    """0.0 = identical; larger = more drift. Roughly 0..1."""
    colour = 1.0 - histogram_intersection(feat_a["hist"], feat_b["hist"])
    layout = grid_l1(feat_a["grid"], feat_b["grid"])
    return 0.7 * colour + 0.3 * layout


def check_frames_against_lock(frames, locked_features: dict, threshold: float = 0.35) -> dict:
    """frames: iterable of image paths from one rendered shot.
    locked_features: {label: features} from frame_features() on locked stills.
    Returns {'ok': bool, 'worst': (frame, label, score), 'flags': [...]}."""
    flags = []
    worst = (None, None, 0.0)
    for frame in frames:
        f = frame_features(frame)
        for label, ref in locked_features.items():
            s = drift_score(f, ref)
            if s > worst[2]:
                worst = (str(frame), label, s)
            if s > threshold:
                flags.append({"frame": str(frame), "still": label, "score": round(s, 3)})
    return {"ok": not flags, "worst": worst, "flags": flags}
