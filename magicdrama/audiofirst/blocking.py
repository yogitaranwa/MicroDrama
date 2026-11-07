"""Blocking: a floor plan with real coordinates, camera positions and where each person stands, so every shot's spatial layout is computed
instead of guessed.

Why: an image or video model given "the same kitchen" and "Mia at the doorway" keeps the background looking similar and moves the people
wherever composes nicely, so a reverse shot can show the table and window behind a camera that could not see them, and she is suddenly
several steps inside the room. With coordinates we can (1) check that people do not teleport between shots, (2) check what is and is not
in frame from each camera, (3) write that into the prompt ("behind her: the doorway and dark hallway; NOT in frame: window, table"), and
(4) draw a layout guide image the image model can follow.

Units: metres. x runs east, y runs north, z up. Facing is a compass angle in degrees (0 = east, 90 = north, 180 = west, 270 = south).
"""
import math

import numpy as np

NEAR = 0.1
SENSOR_WIDTH_MM = 36.0
COMPASS = ('east', 'north-east', 'north', 'north-west', 'west', 'south-west', 'south', 'south-east')


def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n == 0:raise ValueError('Zero-length direction')
    return v / n


def compass(dx, dy):
    return COMPASS[int(((math.degrees(math.atan2(dy, dx)) + 22.5) % 360) // 45)]


class Camera:
    def __init__(self, pos, target, lens=35.0, aspect=16 / 9):
        self.pos, self.target = np.array(pos, float), np.array(target, float)
        f = _unit(self.target - self.pos)
        r = _unit(np.cross(f, [0, 0, 1]))
        self.f, self.r, self.u = f, r, np.cross(r, f)
        self.th = (SENSOR_WIDTH_MM / 2) / lens           # tan(half horizontal fov)
        self.tv = self.th / aspect

    def view(self, p):
        v = np.asarray(p, float) - self.pos
        return np.array([v @ self.r, v @ self.u, v @ self.f])

    def project(self, p):
        """(sx, sy, depth): sx and sy in -1..1 across the frame; None when behind the camera."""
        x, y, z = self.view(p)
        if z < NEAR:return None
        return (x / z) / self.th, (y / z) / self.tv, z

    def yaw(self):
        return compass(self.f[0], self.f[1])


def box_corners(b):
    x0, y0, z0, x1, y1, z1 = b
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


def box_samples(b, n=3):
    x0, y0, z0, x1, y1, z1 = b
    return [(x0 + (x1 - x0) * i / (n - 1), y0 + (y1 - y0) * j / (n - 1), z0 + (z1 - z0) * k / (n - 1)) for i in range(n) for j in range(n) for k in range(n)]


def figure_box(fig, pos, facing, height):
    """A person as a box (0.5 m wide, 0.35 m deep) turned to `facing`."""
    c, s = math.cos(math.radians(facing)), math.sin(math.radians(facing))
    cx, cy = pos
    half_w, half_d = 0.25, 0.175
    pts = []
    for dx in (-half_d, half_d):
        for dy in (-half_w, half_w):
            pts.append((cx + dx * c - dy * s, cy + dx * s + dy * c))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    z0 = 0.0 if fig.get('pose', 'standing') == 'standing' else 0.45
    return (min(xs), min(ys), z0, max(xs), max(ys), float(fig['height']))


def blocked_by_wall(plan, cam_pos, point):
    """True when the straight line from the camera to the point passes through the west wall outside the doorway."""
    if 'doorway' not in plan:return False  # a single open room has no inner wall to hide anything
    x0 = plan['room']['x'][0]
    a, b = cam_pos[0] - x0, point[0] - x0
    if a * b >= 0:return False  # same side of the wall
    t = a / (a - b)
    y = cam_pos[1] + (point[1] - cam_pos[1]) * t
    z = cam_pos[2] + (point[2] - cam_pos[2]) * t
    d = plan['doorway']
    return not (d['y'][0] <= y <= d['y'][1] and 0 <= z <= d['z'])


def coverage(plan, cam, box):
    """Share of sample points on the box that land inside the frame and are not behind the wall."""
    pts = box_samples(box)
    seen = 0
    for p in pts:
        pr = cam.project(p)
        if pr and abs(pr[0]) <= 1 and abs(pr[1]) <= 1 and not blocked_by_wall(plan, cam.pos, p):seen += 1
    return seen / len(pts)


def camera_setup(plan, shot_id):
    """A hashable key for a shot's camera angle (start position, target, lens), rounded so two shots from the same set-up match."""
    sh = plan['shots'][shot_id]
    c = sh['camera']['start']
    return (tuple(round(float(v), 1) for v in c['pos']), tuple(round(float(v), 1) for v in c['target']), round(float(sh['camera'].get('lens', 35.0))))


def shot_state(plan, shot_id, which):
    sh = plan['shots'][shot_id]
    cam = sh['camera'][which]
    camera = Camera(cam['pos'], cam['target'], sh['camera'].get('lens', 35.0))
    figs = {}
    for name, st in sh['figures'].items():
        d = st[which]
        figs[name] = {'pos': d['pos'], 'facing': d['facing'], 'box': figure_box(plan['figures'][name], d['pos'], d['facing'], plan['figures'][name]['height'])}
    return camera, figs


def _where(sx):
    return 'far left' if sx < -0.6 else 'left' if sx < -0.2 else 'centre' if sx <= 0.2 else 'right' if sx <= 0.6 else 'far right'


def _facing_words(fig_pos, facing, cam_pos):
    to_cam = _unit([cam_pos[0] - fig_pos[0], cam_pos[1] - fig_pos[1], 0])
    c = math.cos(math.radians(facing)) * to_cam[0] + math.sin(math.radians(facing)) * to_cam[1]
    return 'facing the camera' if c > 0.8 else 'turned three-quarters toward the camera' if c > 0.3 else 'in profile' if c > -0.3 else 'seen from behind'


def facing_cos(fig_pos, facing, cam_pos):
    to_cam = _unit([cam_pos[0] - fig_pos[0], cam_pos[1] - fig_pos[1], 0])
    return math.cos(math.radians(facing)) * to_cam[0] + math.sin(math.radians(facing)) * to_cam[1]


def is_visible(plan, cam, box):
    """(visible, coverage). A big thing close to the camera (a doorway one metre away) is visible when its centre is in frame even if its top and bottom are not."""
    cov = coverage(plan, cam, box)
    centre = [(a + b) / 2 for a, b in zip(box[:3], box[3:])]
    pr = cam.project(centre)
    centre_in = bool(pr and abs(pr[0]) <= 1 and abs(pr[1]) <= 1 and not blocked_by_wall(plan, cam.pos, centre))
    return (centre_in or cov >= 0.2), cov


def view_report(plan, shot_id, which='start'):
    """What is in frame and what is not, computed from the geometry."""
    cam, figs = shot_state(plan, shot_id, which)
    inside, outside = [], []
    for f in plan['features']:
        vis, cov = is_visible(plan, cam, f['box'])
        (inside if vis else outside).append((f['name'], cov, f))
    people = []
    for name, st in figs.items():
        vis, cov = is_visible(plan, cam, st['box'])
        cov = max(cov, 0.5) if vis else 0.0
        c = [(sum(v) / 2) for v in zip(st['box'][:3], st['box'][3:])]
        pr = cam.project(c)
        people.append({'name': name, 'coverage': cov, 'screen': _where(pr[0]) if pr else None, 'distance': round(pr[2], 1) if pr else None,
                       'facing': _facing_words(st['pos'], st['facing'], cam.pos) if cov > 0 else None, 'facing_cos': facing_cos(st['pos'], st['facing'], cam.pos)})
    # structural background: which wall(s) fill the back of the frame
    back = []
    for wall, probe in plan.get('walls', {}).items():
        pr = cam.project(probe)
        if pr and abs(pr[0]) <= 1 and abs(pr[1]) <= 1 and not blocked_by_wall(plan, cam.pos, probe):back.append((pr[0], wall))
    return {'camera': {'looking': cam.yaw(), 'pos': [round(x, 2) for x in cam.pos]}, 'people': people, 'visible': sorted([(n, c) for n, c, _ in inside]),
            'not_visible': sorted(n for n, _, _ in outside), 'walls': [w for _, w in sorted(back)]}


def framing_text(plan, shot_id, max_not=4):
    """The prompt paragraph: where the camera stands, who is where, what is behind them and what must NOT appear."""
    sh, parts = plan['shots'][shot_id], []
    for which, label in (('start', 'Start'), ('end', 'End')):
        if which == 'end' and sh['camera']['start'] == sh['camera']['end'] and all(f['start'] == f['end'] for f in sh['figures'].values()):
            break
        r = view_report(plan, shot_id, which)
        ppl = [f"{p['name']} ({p['screen']}, {p['distance']} m, {p['facing']})" for p in r['people'] if p['coverage'] > 0.2]
        vis = [n for n, _ in r['visible']][:3]
        banned = list(dict.fromkeys(sh.get('must_not_show', {}).get(which, []) + r['not_visible']))[:max_not]
        seg = f"{label}: camera looks {r['camera']['looking']}"
        if ppl:seg += '; in frame ' + ', '.join(ppl)
        if vis:seg += '; also visible: ' + ', '.join(vis)
        if banned:seg += '; NOT in frame (do not draw): ' + ', '.join(banned)
        parts.append((label, seg[len(f'{label}: '):] + '.'))
    if len(parts) == 2 and parts[0][1] == parts[1][1]:parts = parts[:1]  # the same picture at both ends of the shot: say it once
    text = ' '.join((f'{label}: ' if len(parts) == 2 else 'Throughout: ') + body for label, body in parts)
    if len(sh['figures']) == 1:  # image and video models add a second person unless told the room holds one
        text += f" Only {next(iter(sh['figures']))} is in the room: no other person appears anywhere in the frame."
    return text


def check_blocking(story):
    """Problems a continuity supervisor would flag, computed from the plan. Empty list when the blocking is consistent."""
    plan, problems = story['plan'], []
    prev_id, prev = None, None
    for s in story['shots']:
        sid = s['id']
        sh = plan['shots'].get(sid)
        if not sh:
            problems.append(f'{sid}: no blocking entry in plan.shots')
            continue
        for which in ('start', 'end'):
            cam, figs = shot_state(plan, sid, which)
            r = view_report(plan, sid, which)
            names_visible = {n for n, _ in r['visible']} | {p['name'] for p in r['people'] if p['coverage'] > 0.2}
            for need in sh.get('must_show', {}).get(which, []):
                if need not in names_visible:problems.append(f'{sid} ({which}): "{need}" should be in frame but the camera at {r["camera"]["pos"]} looking {r["camera"]["looking"]} does not see it')
            for ban in sh.get('must_not_show', {}).get(which, []):
                if ban in names_visible:problems.append(f'{sid} ({which}): "{ban}" would be in frame but is behind or beside this camera; the model must not draw it')
        spoken = [d['speaker'] for d in (s.get('sound') or {}).get('dialogue', []) or [] if not d.get('offscreen')]
        r = view_report(plan, sid, 'end')
        for who in spoken:
            p = next((p for p in r['people'] if p['name'] == who), None)
            if not p or p['coverage'] < 0.4:problems.append(f'{sid}: {who} speaks but is not in frame')
            elif p['facing_cos'] < -0.3:problems.append(f'{sid}: {who} speaks with their back to the camera')
        if prev:
            for name, st in sh['figures'].items():
                if name in prev['figures'] and not sh.get('reposition'):
                    a, b = prev['figures'][name]['end']['pos'], st['start']['pos']
                    if math.dist(a, b) > 0.4:problems.append(f'{sid}: {name} ends {prev_id} at {a} but starts here at {b} ({math.dist(a, b):.1f} m apart); a person cannot teleport between shots')
        prev_id, prev = sid, sh
    return problems


# ---------------------------------------------------------------- layout guide renderer (painter's algorithm)

def _clip_near(poly):
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ina, inb = a[2] >= NEAR, b[2] >= NEAR
        if ina:out.append(a)
        if ina != inb:
            t = (NEAR - a[2]) / (b[2] - a[2])
            out.append(a + (b - a) * t)
    return out


def _quad(a, b, c, d):
    return [np.array(p, float) for p in (a, b, c, d)]


def _box_faces(b):
    x0, y0, z0, x1, y1, z1 = b
    return [_quad((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)), _quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
            _quad((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)), _quad((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)),
            _quad((x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)), _quad((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))]


def _hex(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def render_layout(plan, shot_id, which='start', size=(960, 540), labels=False):
    """A flat-shaded picture of exactly what this camera sees: walls, doorway, hallway, furniture and the people as coloured blocks.
    Used as a layout reference for the image model (no text on it unless `labels` is set for human review)."""
    from PIL import Image, ImageDraw
    cam, figs = shot_state(plan, shot_id, which)
    if 'doorway' not in plan:return _render_open_room(plan, cam, figs, size, labels)
    W, H = size
    img = Image.new('RGB', size, (20, 20, 24))
    draw = ImageDraw.Draw(img)
    rx, ry, rz = plan['room']['x'], plan['room']['y'], plan['room']['z']
    hx, hy, hz = plan['hallway']['x'], plan['hallway']['y'], plan['hallway']['z']
    d, w = plan['doorway'], plan['window']
    shade = lambda c, k: tuple(int(max(0, min(255, v * k))) for v in c)

    def poly(p3, color, outline=(15, 15, 15)):
        pts = [cam.view(p) for p in p3]
        pts = _clip_near(pts)
        if len(pts) < 3:return None
        pix = [((x / z / cam.th + 1) / 2 * W, (1 - y / z / cam.tv) / 2 * H) for x, y, z in pts]
        draw.polygon(pix, fill=color, outline=outline)
        return pix

    hall = [(_quad((hx[0], hy[0], 0), (hx[1], hy[0], 0), (hx[1], hy[1], 0), (hx[0], hy[1], 0)), (70, 55, 45)),
            (_quad((hx[0], hy[0], hz), (hx[1], hy[0], hz), (hx[1], hy[1], hz), (hx[0], hy[1], hz)), (60, 60, 66)),
            (_quad((hx[0], hy[0], 0), (hx[1], hy[0], 0), (hx[1], hy[0], hz), (hx[0], hy[0], hz)), (52, 58, 70)),
            (_quad((hx[0], hy[1], 0), (hx[1], hy[1], 0), (hx[1], hy[1], hz), (hx[0], hy[1], hz)), (52, 58, 70)),
            (_quad((hx[0], hy[0], 0), (hx[0], hy[1], 0), (hx[0], hy[1], hz), (hx[0], hy[0], hz)), (38, 40, 52))]
    hall.sort(key=lambda t: -np.linalg.norm(np.mean(t[0], axis=0) - cam.pos))
    if cam.pos[0] >= rx[0]:
        for q, c in hall:poly(q, c)
    # kitchen shell (the west wall pieces are kept apart: which side of them the camera is on decides what covers what)
    west = [(_quad((rx[0], ry[0], 0), (rx[0], d['y'][0], 0), (rx[0], d['y'][0], rz), (rx[0], ry[0], rz)), (196, 190, 172)),
            (_quad((rx[0], d['y'][1], 0), (rx[0], ry[1], 0), (rx[0], ry[1], rz), (rx[0], d['y'][1], rz)), (196, 190, 172)),
            (_quad((rx[0], d['y'][0], d['z']), (rx[0], d['y'][1], d['z']), (rx[0], d['y'][1], rz), (rx[0], d['y'][0], rz)), (196, 190, 172))]
    shell = [(_quad((rx[0], ry[0], 0), (rx[1], ry[0], 0), (rx[1], ry[1], 0), (rx[0], ry[1], 0)), (112, 82, 58)),
             (_quad((rx[0], ry[0], rz), (rx[1], ry[0], rz), (rx[1], ry[1], rz), (rx[0], ry[1], rz)), (205, 205, 200)),
             (_quad((rx[0], ry[0], 0), (rx[1], ry[0], 0), (rx[1], ry[0], rz), (rx[0], ry[0], rz)), (150, 170, 168)),   # south wall
             (_quad((rx[0], ry[1], 0), (rx[1], ry[1], 0), (rx[1], ry[1], rz), (rx[0], ry[1], rz)), (186, 180, 164)),   # north wall
             (_quad((rx[1], ry[0], 0), (rx[1], ry[1], 0), (rx[1], ry[1], rz), (rx[1], ry[0], rz)), (176, 170, 150))]   # east wall
    wy, wz = w['span'], w['z']
    window = _quad((rx[1] - 0.01, wy[0], wz[0]), (rx[1] - 0.01, wy[1], wz[0]), (rx[1] - 0.01, wy[1], wz[1]), (rx[1] - 0.01, wy[0], wz[1]))
    things, hall_things = [], []
    for f in plan['features']:
        if f.get('render', True):(hall_things if f['box'][3] <= 0.06 else things).append((f['name'], f['box'], _hex(f.get('color', '#888888'))))
    for name, st in figs.items():
        x0_, y0_, z0_, x1_, y1_, z1_ = st['box']
        color = _hex(plan['figures'][name]['color'])
        target = hall_things if x1_ <= 0 else things
        head = 0.24
        target.append((name, (x0_, y0_, z0_, x1_, y1_, z1_ - head - 0.04), color))                                    # body
        cx, cy = (x0_ + x1_) / 2, (y0_ + y1_) / 2
        target.append((name + ' head', (cx - 0.11, cy - 0.11, z1_ - head, cx + 0.11, cy + 0.11, z1_), tuple(min(255, int(v * 1.35)) for v in color)))
        if plan['figures'][name].get('pose') == 'seated':                                                              # thighs reach out in front
            fx, fy = math.cos(math.radians(st['facing'])), math.sin(math.radians(st['facing']))
            target.append((name + ' legs', (min(cx, cx + 0.45 * fx) - 0.15, min(cy, cy + 0.45 * fy) - 0.15, 0.4, max(cx, cx + 0.45 * fx) + 0.15, max(cy, cy + 0.45 * fy) + 0.15, 0.6), shade(color, 0.8)))
    for group in (hall_things, things):
        group.sort(key=lambda t: -np.linalg.norm(np.array([(t[1][0] + t[1][3]) / 2, (t[1][1] + t[1][4]) / 2, (t[1][2] + t[1][5]) / 2]) - cam.pos))

    def draw_boxes(group):
        for name, bx, color in group:
            for i, q in enumerate(sorted(_box_faces(bx), key=lambda q: -np.linalg.norm(np.mean(q, axis=0) - cam.pos))):poly(q, shade(color, 0.7 + 0.1 * (i % 4)))
            if labels:
                pr = cam.project([(bx[0] + bx[3]) / 2, (bx[1] + bx[4]) / 2, bx[5]])
                if pr and abs(pr[0]) < 1 and abs(pr[1]) < 1:draw.text(((pr[0] + 1) / 2 * W - 12, (1 - pr[1]) / 2 * H - 14), name, fill=(255, 255, 255))

    if cam.pos[0] >= rx[0]:     # camera in the kitchen: hallway is far, then the kitchen, near things last
        draw_boxes(hall_things)
        for q, c in west + shell:poly(q, c)
        poly(window, (90, 130, 190))
        draw_boxes(things)
    else:                       # camera in the hallway: the kitchen is far, the west wall hides most of it, the hallway is near
        for q, c in shell:poly(q, c)
        poly(window, (90, 130, 190))
        draw_boxes(things)
        for q, c in west:poly(q, c)
        for q, c in sorted(hall, key=lambda t: -np.linalg.norm(np.mean(t[0], axis=0) - cam.pos)):poly(q, c)
        draw_boxes(hall_things)
    return img


def _render_open_room(plan, cam, figs, size, labels):
    """Layout guide for a single closed room (no inner wall): floor, ceiling, four walls, wall-mounted and standing features, the people as blocks."""
    from PIL import Image, ImageDraw
    W, H = size
    img = Image.new('RGB', size, (20, 20, 24))
    draw = ImageDraw.Draw(img)
    rx, ry, rz = plan['room']['x'], plan['room']['y'], plan['room']['z']
    shade = lambda c, k: tuple(int(max(0, min(255, v * k))) for v in c)

    def poly(p3, color):
        pts = _clip_near([cam.view(p) for p in p3])
        if len(pts) < 3:return
        draw.polygon([((x / z / cam.th + 1) / 2 * W, (1 - y / z / cam.tv) / 2 * H) for x, y, z in pts], fill=color, outline=(15, 15, 15))

    walls = [(_quad((rx[0], ry[0], 0), (rx[1], ry[0], 0), (rx[1], ry[1], 0), (rx[0], ry[1], 0)), (150, 150, 148)),
             (_quad((rx[0], ry[0], rz), (rx[1], ry[0], rz), (rx[1], ry[1], rz), (rx[0], ry[1], rz)), (215, 215, 210)),
             (_quad((rx[0], ry[0], 0), (rx[1], ry[0], 0), (rx[1], ry[0], rz), (rx[0], ry[0], rz)), (176, 180, 176)),
             (_quad((rx[0], ry[1], 0), (rx[1], ry[1], 0), (rx[1], ry[1], rz), (rx[0], ry[1], rz)), (196, 192, 184)),
             (_quad((rx[0], ry[0], 0), (rx[0], ry[1], 0), (rx[0], ry[1], rz), (rx[0], ry[0], rz)), (188, 186, 178)),
             (_quad((rx[1], ry[0], 0), (rx[1], ry[1], 0), (rx[1], ry[1], rz), (rx[1], ry[0], rz)), (184, 180, 170))]
    for q, c in walls:poly(q, c)
    things = [(f['name'], f['box'], _hex(f.get('color', '#888888'))) for f in plan['features'] if f.get('render', True)]
    for name, st in figs.items():
        x0_, y0_, z0_, x1_, y1_, z1_ = st['box']
        color, head = _hex(plan['figures'][name]['color']), 0.24
        cx, cy = (x0_ + x1_) / 2, (y0_ + y1_) / 2
        things.append((name, (x0_, y0_, z0_, x1_, y1_, z1_ - head - 0.04), color))
        things.append((name + ' head', (cx - 0.11, cy - 0.11, z1_ - head, cx + 0.11, cy + 0.11, z1_), tuple(min(255, int(v * 1.35)) for v in color)))
    things.sort(key=lambda t: -np.linalg.norm(np.array([(t[1][0] + t[1][3]) / 2, (t[1][1] + t[1][4]) / 2, (t[1][2] + t[1][5]) / 2]) - cam.pos))
    for name, bx, color in things:
        for i, q in enumerate(sorted(_box_faces(bx), key=lambda q: -np.linalg.norm(np.mean(q, axis=0) - cam.pos))):poly(q, shade(color, 0.7 + 0.1 * (i % 4)))
        if labels:
            pr = cam.project([(bx[0] + bx[3]) / 2, (bx[1] + bx[4]) / 2, bx[5]])
            if pr and abs(pr[0]) < 1 and abs(pr[1]) < 1:draw.text(((pr[0] + 1) / 2 * W - 12, (1 - pr[1]) / 2 * H - 14), name, fill=(255, 255, 255))
    return img


def render_floor_plan(plan, shot_id, size=(720, 520)):
    """Top-down plan with the camera, its view cone and the people, for human review."""
    from PIL import Image, ImageDraw
    img = Image.new('RGB', size, (245, 245, 240))
    dr = ImageDraw.Draw(img)
    x0, x1 = plan.get('hallway', plan['room'])['x'][0] - 0.3, plan['room']['x'][1] + 0.3
    y0, y1 = plan['room']['y'][0] - 0.3, plan['room']['y'][1] + 0.3
    sc = min(size[0] / (x1 - x0), size[1] / (y1 - y0))
    P = lambda x, y: ((x - x0) * sc, size[1] - (y - y0) * sc)
    rx, ry = plan['room']['x'], plan['room']['y']
    if 'hallway' in plan:
        hy, hx = plan['hallway']['y'], plan['hallway']['x']
        dr.rectangle([P(hx[0], hy[1]), P(hx[1], hy[0])], fill=(225, 225, 230), outline=(80, 80, 80))
    dr.rectangle([P(rx[0], ry[1]), P(rx[1], ry[0])], fill=(250, 245, 230), outline=(60, 60, 60), width=3)
    if 'doorway' in plan:dr.line([P(rx[0], plan['doorway']['y'][0]), P(rx[0], plan['doorway']['y'][1])], fill=(250, 245, 230), width=5)
    for f in plan['features']:
        b = f['box']
        if f.get('render', True):dr.rectangle([P(b[0], b[4]), P(b[3], b[1])], fill=_hex(f.get('color', '#888888')), outline=(40, 40, 40))
        dr.text(P(b[0], b[4]), f['name'][:18], fill=(0, 0, 0))
    sh = plan['shots'][shot_id]
    for which, col in (('start', (30, 160, 60)), ('end', (200, 90, 20))):
        cam, figs = shot_state(plan, shot_id, which)
        cx, cy = cam.pos[0], cam.pos[1]
        for sgn in (-1, 1):
            ang = math.atan2(cam.f[1], cam.f[0]) + sgn * math.atan(cam.th)
            dr.line([P(cx, cy), P(cx + 2.2 * math.cos(ang), cy + 2.2 * math.sin(ang))], fill=col, width=2)
        dr.ellipse([P(cx - 0.1, cy + 0.1), P(cx + 0.1, cy - 0.1)], fill=col)
        for name, st in figs.items():
            px, py = st['pos']
            c = _hex(plan['figures'][name]['color'])
            dr.ellipse([P(px - 0.2, py + 0.2), P(px + 0.2, py - 0.2)], fill=c if which == 'end' else None, outline=c, width=3)
            dr.text(P(px + 0.1, py + 0.1), name + (' end' if which == 'end' else ' start'), fill=c)
    dr.text((8, 8), f'{shot_id}: green = camera at start, orange = camera at end', fill=(0, 0, 0))
    return img
