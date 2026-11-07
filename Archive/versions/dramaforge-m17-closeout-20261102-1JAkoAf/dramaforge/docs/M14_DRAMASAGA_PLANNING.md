# M14: DramaSaga-derived planning upgrades

Added 2026-11-02 as an additive planning layer. The old m13-compatible flow still works when these options are not used: `dialogue_shots` still creates the shot/reverse-shot plan, `angle_stills` still gates references, and `render_plan.dry_run()` still uses the legacy flat estimate unless a model route is explicitly supplied.

## New files

- `forge/planning/routes.py` - model route capabilities, duration snapping and credit quotes from Magic Hour's official model table as read on 2026-11-02. It does not submit jobs or refresh prices by itself.
- `forge/planning/director.py` - bounded director prompts with set lock, character lock, camera, lighting, continuity and end-state sections.
- `forge/planning/continuity.py` - story-state ledger for character/prop/knowledge changes. Every change needs a story reason.
- `forge/planning/blocking.py` - generic room coordinates, camera field-of-view, occlusion, must-show/must-not-show and teleport checks. No project-specific room or cast names are built in.

## Use

Validate and enrich an existing `out/e01_plan.json` without spending:

```bash
python3 -m forge.gates plan-check PROJECT_DIR \
  --bible bible.json \
  --layout layout.json \
  --model veo3.1-lite \
  --resolution 720p \
  --audio \
  --credit-cap 5000
```

This writes `out/e01_planning_upgrades.json` and, when a layout is supplied, `out/e01_layout.svg`.

Build the ordinary render manifest with the old behavior:

```bash
python3 -m forge.gates render-plan PROJECT_DIR
```

Build it with the new optional route/director layer:

```bash
python3 -m forge.gates render-plan PROJECT_DIR \
  --director-bible bible.json \
  --model veo3.1-lite \
  --resolution 720p \
  --audio
```

`render_plan.dry_run(..., route_name=...)` snaps every shot to a duration the selected model accepts and writes the route quote into `.forge/render_manifest.json`. `execute_plan(..., route_name=...)` refuses to start if any route validation fails. The paid path still goes through the existing generator, gates and ledger. Route-aware execution is fail-closed: generator model/resolution, snapped duration, audio setting, and ledger estimate must match the quoted route before a live call. The Magic Hour generator exposes an additive `audio` request/credit option; it is off by default, preserving non-audio estimates and request bodies.

## Visual bible shape

```json
{
  "style": "Photorealistic vertical microdrama",
  "locations": {"kitchen": "Small blue kitchen, window on the left wall."},
  "characters": {"Asha": "Short black hair, red jacket, same face and wardrobe as the locked stills."},
  "lighting": {"kitchen": "Cool window light with a warm practical over the table."},
  "camera_rules": {"default": "One clear setup; no unmotivated camera change."}
}
```

## Layout shape

```json
{
  "width": 10,
  "depth": 8,
  "cameras": {"wide": {"x": 5, "y": 0, "angle": 90, "fov": 80}},
  "actors": {
    "Asha": {"x": 3, "y": 4, "facing": 270},
    "Ravi": {"x": 8, "y": 4, "facing": 270}
  },
  "obstacles": [{"name": "table", "x": 6.5, "y": 0.5, "width": 1, "depth": 5}]
}
```

Shots opt into blocking with a `blocking` object:

```json
{"camera": "wide", "must_show": ["Asha"], "must_not_show": ["Ravi"]}
```

## Limits

These are planning checks, not generated-quality proof. They do not certify acting, voice quality, lip sync, semantic continuity or publishability. Keep the existing proof scene, checklist, playback and listening review. Route prices are a dated snapshot and must be rechecked before a real paid run.

Tests: full repository regression `python3 -m pytest -q` (302 tests plus 30 subtests passed in the isolated validation venv).
