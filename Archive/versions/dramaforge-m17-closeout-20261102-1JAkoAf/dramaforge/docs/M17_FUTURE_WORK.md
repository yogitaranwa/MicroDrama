# m17: the report's Future Work items, in code

Each item names what is implemented and tested, and what stays pending and
why. Nothing below claims a paid render, a GPU run, or a human judgment that
did not happen.

## Verification (this sandbox)

- 394 tests + 30 subtests pass (367 + 30 before m17, +27 m17 tests).
- Caveat: the project targets Python >=3.12; this sandbox ran Python 3.10
  with a tomli-backed tomllib shim. **The 3.12 run is still not done**: the
  sandbox has no 3.12 interpreter and the install rules allow official
  registries only (PyPI/npm/apt); no 3.12 exists in those for this box, so a
  standalone build needs the owner's approval first.
- The one-gigabyte archive boundary test runs for real: a full 1 GiB
  decompressed payload is streamed, counted and hashed at the exact limit
  (member content is compressible zeros, so the zip on disk stays small).

## 1. Season archive - `forge/season_archive.py` (DONE)

`build_manifest` / `write_archive` / `read_archive` / `continuity_report` /
`require_continuity`. Manifest lists every asset with path, kind, bytes,
sha256. Read time: hostile paths rejected (zip-slip), member count capped,
size limit enforced on declared sizes before extraction AND on actual
decompressed bytes while streaming; over-limit or corrupt archives abort
with no partial output left; every extracted file is re-hashed against the
manifest; extras and missing files fail. CPython's zipfile already caps
output at the declared member size and CRC-checks it, so the streaming
counter is the guard for readers that do not; both paths have tests.
Continuity: the next season is checked against inherited characters,
wardrobe and sets by path; missing inherited assets lock the gate, changed
bytes and additions are reported.

## 2. Form-based intake - `forge/intake.py` (DONE)

`validate_form` enforces genre (non-empty), num_characters (1..8), the
1000-character description limit, and per-character reference images in
`upload` mode (existing, non-empty image file) or `generate` mode (prompt
recorded for the still step; nothing is generated here). `bind_to_planning`
persists the form and returns the outline prompt, the visual bible in
`forge.planning.director`'s shape, and the per-character still plan for the
still-lock gate.

## 3. Non-spending preflight + bounded quality test - `forge/preflight.py` (DONE)

`preflight` walks the exact render graph (`_load_plan` + `build_render_jobs`)
with route-aware duration snapping and credit quotes, checks locked stills,
gate-state readability and budget headroom, and writes `.forge/preflight.json`.
It proves zero spend by snapshotting the ledger before and after; any change
fails closed. `bounded_quality_check` runs the local, free QA on ONE
already-rendered episode (duration, streams, hard cuts via PySceneDetect,
black frames and silent stretches via ffmpeg, caption stream) and refuses
files over 300 s so the check stays bounded.

## 4. Full-speed review gate - `forge/gates/fullspeed.py` (DONE, behavior change)

`record_fullspeed_review` requires a named reviewer, watched_full_speed AND
listened true, a verdict (`approved`/`issues`) and validated timestamped
observations; the machine review must already cover the same bytes.
`require_fullspeed_review` fails closed on a missing record, a verdict of
`issues`, or changed bytes. **deliver() now requires it** by default
(`fullspeed=False` restores the old path); the existing delivery test was
updated accordingly. CLI: `python -m forge.gates fullspeed ...`.

## 5. Lip-sync face policy - `forge/assemble/face_policy.py` (code DONE; GPU runs PENDING)

`classify_pose` (front vs profile from nose/eye symmetry), `select_face`
(main face + multi-face ambiguity), `classify_shot` (per-shot verdict
ok/review/unsupported). Pure numpy over FaceMesh-shaped landmarks, fully
tested offline. `mp_detector.py` itself is UNCHANGED: its Kaggle validation
covers single front faces only, and the real profile and multi-face model
runs still belong to the free Kaggle T4 path (docs/LIPSYNC_PLAN.md) - not
done here (no GPU in this sandbox).
Python 3.12 suite run: PENDING, blocked on an interpreter (see Verification).

## 6. Vertical 9:16 episode set - `forge/assemble/vertical.py` (no-spend half DONE; model regeneration HELD)

No-spend path executed: all nine episodes in the Drive folder were reframed
to 720x1280 locally. `scene_track` detects shot boundaries (PySceneDetect)
and holds ONE stable crop per shot at the shot's median face position
(center when a shot has too few detections); frames stream through
ffmpeg/libx264 and the source audio is copied through untouched. A
continuous gliding crop was tried first and rejected: flickering detections
cut speakers in half. Model REGENERATION at 9:16 is the paid path and stays
held for cost approval. Wide two-shots can only show one speaker at 32%
width; which framing is right is a human review call (item 4 owns it).
Full-speed human review of the nine reframes: PENDING (they are reviewed
outputs only after a person watches and listens).

## 7. Viewer reception study - `forge/reception.py` (instrumentation DONE; study PENDING)

`record_viewing` appends validated viewing records (named viewer, episode,
pace and music-level ratings 1..5, timestamped moments) to a JSONL store;
`aggregate` gives per-episode means and distributions. Corrupt lines are
skipped and counted, never treated as data. Recruiting viewers and running
the study is human work and has not been done.

## Integration (m17 closeout, 2026-11-02 20:35 IST)

All m17 paths are wired into real entry points and covered by `tests_forge/test_integration_m17.py` (8 tests, end-to-end via CLIs and forge functions):

- Season archive: `python -m forge.season_archive create <project> --season N --episodes a.mp4 b.mp4` / `check` / `read --episode N` (enforces read-time byte cap on actual streamed bytes).
- Intake: `python -m forge.intake --title T --genre G --characters 2 --description "..." --image ref.png --project-dir P` writes `.forge/intake.json`; `forge.script_run.active_brief()` binds it into the planning layer (used by `forge.script_run` main).
- Preflight: `python -m forge.preflight <project>` (graph preflight, non-spending) and `python -m forge.preflight --quality <episode.mp4>` (bounded quality check).
- Full-speed review gate: `python -m forge.gates fullspeed <reviewer> --episode EP --verdict approved --obs "..."` records a supplied human review; `forge.gates.deliver()` now requires it (never auto-attests).
- Vertical: `python -m forge.assemble.vertical <episode.mp4> --out out.mp4` (scene-aware local crop conversion, not model regeneration).
- Reception: `python -m forge.reception new <study> --episodes ...` / `record --viewer V --episode EP --pace 4 --music 5 --notes "..."` / `summary`.

Dependency changes: none new (moviepy, opencv-python-headless<5, scenedetect, ffmpeg/ffprobe already in the m15/m16 environment).

Real-episode bounded quality check (not synthetic): `EP03 - The Yule Ball Announcement (approved).mp4` — 73.1s, 1280x720 (landscape), 31 scenes, 30 hard cuts, 1 audio stream, no caption stream, issues: none, ok: true (2026-11-02T20:34:45+0530).

Full suite after integration: 402 passed, 30 subtests passed (Python 3.10 venv).
