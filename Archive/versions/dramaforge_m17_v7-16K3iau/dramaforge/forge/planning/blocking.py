"""Generic floor-plan blocking checks for planned shots.

Coordinates are arbitrary units in a rectangular room. Camera and actor
positions are supplied by the caller; this module has no project-specific room
or cast assumptions. All checks are local and free.
"""
import html
import math
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

Point = Tuple[float, float]


def _num(value, label: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be numeric")
    if not math.isfinite(out):
        raise ValueError(f"{label} must be finite")
    return out


def _point(value, label: str) -> Point:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} needs x and y")
    return _num(value.get("x"), label + ".x"), _num(value.get("y"), label + ".y")


def _angle_to(a: Point, b: Point) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360


def _angle_delta(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def _inside_rect(p: Point, rect: Mapping) -> bool:
    x, y = p
    left = _num(rect.get("x"), "obstacle.x")
    top = _num(rect.get("y"), "obstacle.y")
    width = _num(rect.get("width"), "obstacle.width")
    depth = _num(rect.get("depth", rect.get("height")), "obstacle.depth")
    return left <= x <= left + width and top <= y <= top + depth


def _segments_cross(a: Point, b: Point, c: Point, d: Point) -> bool:
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return (o1 == 0 and min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])) or \
           (o2 == 0 and min(a[0], b[0]) <= d[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= d[1] <= max(a[1], b[1])) or \
           (o3 == 0 and min(c[0], d[0]) <= a[0] <= max(c[0], d[0]) and min(c[1], d[1]) <= a[1] <= max(c[1], d[1])) or \
           (o4 == 0 and min(c[0], d[0]) <= b[0] <= max(c[0], d[0]) and min(c[1], d[1]) <= b[1] <= max(c[1], d[1])) or \
           ((o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0))


def _blocked_by_rect(a: Point, b: Point, rect: Mapping) -> bool:
    if _inside_rect(a, rect) or _inside_rect(b, rect):
        return True
    x, y = _num(rect.get("x"), "obstacle.x"), _num(rect.get("y"), "obstacle.y")
    w = _num(rect.get("width"), "obstacle.width")
    h = _num(rect.get("depth", rect.get("height")), "obstacle.depth")
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return any(_segments_cross(a, b, corners[i], corners[(i + 1) % 4]) for i in range(4))


def validate_layout(layout: Mapping) -> Dict:
    errors: List[str] = []
    warnings: List[str] = []
    try:
        width = _num(layout.get("width"), "layout.width")
        depth = _num(layout.get("depth"), "layout.depth")
        if width <= 0 or depth <= 0:
            errors.append("layout width/depth must be positive")
        for group in ("cameras", "actors"):
            for name, item in (layout.get(group) or {}).items():
                try:
                    x, y = _point(item, f"{group}.{name}")
                    if not (0 <= x <= width and 0 <= y <= depth):
                        errors.append(f"{group}.{name} is outside the room")
                except ValueError as e:
                    errors.append(str(e))
        for rect in layout.get("obstacles") or []:
            try:
                x = _num(rect.get("x"), "obstacle.x")
                y = _num(rect.get("y"), "obstacle.y")
                w = _num(rect.get("width"), "obstacle.width")
                h = _num(rect.get("depth", rect.get("height")), "obstacle.depth")
                if w <= 0 or h <= 0:
                    errors.append(f"obstacle {rect.get('name', '?')} has non-positive size")
                elif x < 0 or y < 0 or x + w > width or y + h > depth:
                    errors.append(f"obstacle {rect.get('name', '?')} is outside the room")
            except ValueError as e:
                errors.append(str(e))
    except ValueError as e:
        errors.append(str(e))
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def visible_from(layout: Mapping, camera_name: str, actor: Mapping,
                 obstacles: Optional[List[Mapping]] = None) -> bool:
    cameras = layout.get("cameras") or {}
    if camera_name not in cameras:
        raise ValueError(f"unknown camera {camera_name!r}")
    cam = cameras[camera_name]
    cp = _point(cam, f"camera {camera_name}")
    ap = _point(actor, "actor")
    if math.dist(cp, ap) < 1e-9:
        return False
    direction = _angle_to(cp, ap)
    facing = _num(cam.get("angle", cam.get("facing", 0)), f"camera {camera_name}.angle")
    fov = _num(cam.get("fov", 70), f"camera {camera_name}.fov")
    if _angle_delta(direction, facing) > fov / 2:
        return False
    return not any(_blocked_by_rect(cp, ap, r) for r in (obstacles if obstacles is not None else layout.get("obstacles") or []))


def facing_away(actor: Mapping, camera: Mapping) -> bool:
    ap = _point(actor, "actor")
    cp = _point(camera, "camera")
    actor_facing = _num(actor.get("facing", actor.get("angle", 0)), "actor.facing")
    return _angle_delta(actor_facing, _angle_to(ap, cp)) > 120


def validate_shot_blocking(layout: Mapping, shot: Mapping,
                           previous_positions: Optional[Mapping[str, Point]] = None) -> Dict:
    block = shot.get("blocking") or {}
    explicit = bool(block or shot.get("must_show") or shot.get("must_not_show"))
    if not explicit:
        return {"shot": shot.get("plan_n", shot.get("n")), "checked": False,
                "errors": [], "warnings": ["no blocking data"]}
    errors: List[str] = []
    warnings: List[str] = []
    camera_name = block.get("camera", shot.get("blocking_camera"))
    if not camera_name:
        errors.append("blocking camera is required")
        camera = None
    else:
        camera = (layout.get("cameras") or {}).get(camera_name)
        if camera is None:
            errors.append(f"unknown blocking camera {camera_name!r}")
    actors = dict(layout.get("actors") or {})
    actors.update(block.get("positions") or {})
    speaker = shot.get("speaker")
    default_must_show = [speaker] if speaker and shot.get("kind", "speaker") == "speaker" else []
    must_show = block.get("must_show", shot.get("must_show", default_must_show)) or []
    must_not_show = block.get("must_not_show", shot.get("must_not_show", [])) or []
    visible: Dict[str, bool] = {}
    if camera is not None:
        for name in set(must_show) | set(must_not_show):
            if name not in actors:
                errors.append(f"unknown actor {name!r}")
                continue
            try:
                visible[name] = visible_from(layout, camera_name, actors[name])
            except ValueError as e:
                errors.append(str(e))
        for name in must_show:
            if visible.get(name) is False:
                errors.append(f"{name} must be visible but is outside frame or occluded")
            if visible.get(name) and facing_away(actors[name], camera):
                warnings.append(f"{name} appears to have their back to camera")
        for name in must_not_show:
            if visible.get(name):
                errors.append(f"{name} must not be visible but is in frame")
    max_move = _num(block.get("max_move", layout.get("max_move", 4.0)), "max_move")
    allow_move = bool(block.get("allow_move", False))
    if previous_positions and not allow_move:
        for name, value in (block.get("positions") or {}).items():
            if name in previous_positions:
                try:
                    p = _point(value, f"positions.{name}")
                    moved = math.dist(previous_positions[name], p)
                    if moved > max_move:
                        errors.append(f"{name} moves {moved:.1f} units between shots; mark allow_move or split the move")
                except ValueError as e:
                    errors.append(str(e))
    return {"shot": shot.get("plan_n", shot.get("n")), "checked": True,
            "camera": camera_name, "visible": visible, "errors": errors,
            "warnings": warnings}


def validate_plan_blocking(layout: Mapping, shots: Iterable[Mapping]) -> Dict:
    layout_report = validate_layout(layout)
    entries: List[Dict] = []
    errors: List[Dict] = []
    previous: Dict[str, Point] = {}
    for i, shot in enumerate(shots, 1):
        entry = validate_shot_blocking(layout, shot, previous)
        entries.append(entry)
        for error in entry["errors"]:
            errors.append({"shot": entry["shot"], "error": error})
        for name, value in ((shot.get("blocking") or {}).get("positions") or {}).items():
            try:
                previous[name] = _point(value, f"positions.{name}")
            except ValueError:
                pass
    checked = sum(1 for e in entries if e["checked"])
    return {"ok": not layout_report["errors"] and not errors,
            "layout": layout_report, "shots": entries,
            "checked_shots": checked, "errors": errors}


def layout_svg(layout: Mapping, width_px: int = 640) -> str:
    """Return a simple SVG guide for review; no image dependency."""
    report = validate_layout(layout)
    if not report["ok"]:
        raise ValueError("invalid layout: " + "; ".join(report["errors"]))
    w = _num(layout.get("width"), "layout.width")
    h = _num(layout.get("depth"), "layout.depth")
    margin = 24
    scale = (width_px - 2 * margin) / w
    height_px = int(h * scale + 2 * margin)

    def px(point: Point) -> Point:
        return margin + point[0] * scale, margin + point[1] * scale

    def fmt(value: float) -> str:
        return f"{value:.2f}".rstrip("0").rstrip(".")

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" height="{height_px}">',
             f'<rect x="0" y="0" width="{width_px}" height="{height_px}" fill="#111827"/>',
             f'<rect x="{margin}" y="{margin}" width="{fmt(w * scale)}" height="{fmt(h * scale)}" fill="none" stroke="#e5e7eb" stroke-width="2"/>']
    for rect in layout.get("obstacles") or []:
        x, y = px((_num(rect["x"], "obstacle.x"), _num(rect["y"], "obstacle.y")))
        rw = _num(rect["width"], "obstacle.width") * scale
        rh = _num(rect.get("depth", rect.get("height")), "obstacle.depth") * scale
        parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(rw)}" height="{fmt(rh)}" fill="#6b7280" opacity="0.65"/>')
        parts.append(f'<text x="{fmt(x + 4)}" y="{fmt(min(y + 16, margin + h * scale - 4))}" font-size="14" fill="#fff">{html.escape(str(rect.get("name", "obstacle")))}</text>')
    for name, actor in (layout.get("actors") or {}).items():
        x, y = px((_num(actor["x"], "actor.x"), _num(actor["y"], "actor.y")))
        parts.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="10" fill="#60a5fa"/>')
        parts.append(f'<text x="{fmt(x + 14)}" y="{fmt(y + 5)}" font-size="14" fill="#bfdbfe">{html.escape(str(name))}</text>')
    for name, cam in (layout.get("cameras") or {}).items():
        x, y = px((_num(cam["x"], "camera.x"), _num(cam["y"], "camera.y")))
        parts.append(f'<rect x="{fmt(x - 8)}" y="{fmt(y - 8)}" width="16" height="16" fill="#f59e0b"/>')
        parts.append(f'<text x="{fmt(x + 12)}" y="{fmt(max(y + 5, 16))}" font-size="14" fill="#fde68a">{html.escape(str(name))}</text>')
    parts.append('</svg>')
    return "".join(parts)
