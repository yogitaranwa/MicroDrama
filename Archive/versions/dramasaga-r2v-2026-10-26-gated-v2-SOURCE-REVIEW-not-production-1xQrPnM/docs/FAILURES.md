# Failure cases, root causes and fixes

2026-10-25. This file is the curated public summary of the project's private
failure audit. The full audit with evidence files stays private. Evidence
classes: [S] source/request/receipt read directly, [V] sampled-pixel
inspection, [H] historical record, [W] vendor/repository documentation,
[T] recorded test result, [P] proposed path, not implemented.

## Current status

- No episode or season is accepted. Production is stopped.
- All verification to date is mock/synthetic. No generated media has passed
  full-speed playback review plus human listening.

## Generation failures

### F22 - Recognition/argument test: costume and framing drift [S][V][H]
A 33.6s image-to-video test with explicit same-face, same-costume,
off-camera-gaze prompts still produced wardrobe changes (plain tie/waistcoat
becoming striped tie/sweater neckline), framing drift, near-lens gaze and
changing background geometry. Root cause: the selected one-image silent I2V
route does not enforce requested consistency; a separate mouth-sync pass
addresses a different variable and cannot certify camera, wardrobe or
eyelines. Fix direction: explicit reference/state contracts and view
selection (now implemented as `magicdrama/audiofirst/references.py` and the
continuity contract), plus a materially different tested control route.
More negative prompt words alone are not an evidence-backed fix.

### F23 - Continuity pilot: camera/eyeline control still failed [S][V][H]
A pilot with LOCKED STATIC CAMERA / NEVER into camera prose still showed
push-in, framing change and near-lens gaze. Root cause: prose constraints do
not become hard camera/gaze controls in the chosen route. This is an
empirical counterexample to "negative prompting solved it".

### F24 - Free VACE test failed before synthesis [H][S]
The Wan2.1-VACE-1.3B trial on a free T4 stopped at prompt embedding with
`RuntimeError: Inplace update to inference tensor outside InferenceMode`.
This is a test-code/PyTorch-mode compatibility bug, not evidence of VRAM
limits or of VACE being unable to perform the action. No playable output.
A candidate code remedy (correct inference-mode boundary or cloned tensor)
is a hypothesis, not a tested patch.

### F25 - Paid voice submission timeout unresolved [H]
One historical scene-5 voice submission may have charged but the take was
not recovered; history API access returned 401s. A timeout is UNKNOWN, not
failed and not free. Exact charge/result needs provider reconciliation
before any resubmission.

## Source-level failures and hardening fixes

| Finding | Root cause | Fix in this codebase |
|---|---|---|
| F26 validation/encoding mismatch | Assembler approved one asset set, then encoded hardcoded/globbed paths, so approved bytes and encoded bytes could differ | Legacy custom assembler retired (raises before execution); supported assembly uses an exact ordered input map |
| F27 review receipt not bound to requirements | A previously approved asset hash stayed valid after required action/timing changed | Receipts now bind requirement/beat, validate times/coverage, reject duplicates and out-of-beat lines |
| F28 gate bypass | Independent stitch/assembly/submission paths ran outside the acceptance path | Identified unsafe paths retired before network/key reads |
| F29 duplicate spend risk | Generic POST retry, in-memory batch totals, CSV substring match treated as completion | Durable adapter: dependency checks, shared billing reservations, resume identity, illegal reset rejection, empty-output hold, redirect refusal; unknown jobs retain reservations |
| F30 bare `pixel_checked=True` accepted as evidence | Boolean flag with no binding | Media review binds exact output bytes and shot input to named, timezone-aware review with explicit action/identity/wardrobe/camera/eyeline/prop/speaker/expression/lip checks |
| F31 ignored mechanical errors | Failed FFmpeg commands ignored; silent openings, missing audio, duration mismatches shipped | Detector timeouts, error stops, geometry/duration checks, fresh outputs, output locks |

Hardening scope is precise: 133 tests passing at that revision (now 189
across both pipelines), mocks and synthetic local media only. Seven
`repair_tools` tests require pyloudnorm and are not counted. Gates stop
predictable misuse; they do not generate a fix and cannot prove anyone
watched or listened.

## Pipeline-approach additions (2026-10-25, v2)

- `magicdrama/audiofirst/references.py`: canonical reference bank with named
  views (front, three-quarter, profile, back, full-body, close, wide,
  detail). Per-shot framing must match a banked view per visible character;
  a missing view is an explicit gap, never a silent substitution. Targets
  F22/F23 identity and framing drift.
- `magicdrama/audiofirst/routes.py`: route capability registry. Routes
  declare camera/eyeline/wardrobe/prop-action/audio/structure capabilities
  as supported / unverified / unsupported with the failure evidence above
  attached. Hard shot requirements block routes with failure evidence; an
  operator override needs a named operator and reason and never erases the
  evidence.
- `magicdrama/audiofirst/continuity.py`: story state schema extended with
  per-character eyeline and prop counts. Eyeline changes across cuts in a
  continuous scene are flagged; within a shot they must be declared with
  from/to/reason like any other state transition.
- Fail-closed integration: the live planning entry
  (`magicdrama/audiofirst/runner.py`) enforces these contracts when a
  project declares them. A declared `reference_bank` must cover every
  shot's framing per visible character or planning raises; a declared
  `generation.route` blocked by failure evidence stops planning unless a
  named operator records an override (evidence retained). Reports are
  written to `reference-coverage.json` and `route-plan.json`. The E01
  still-first pipeline enforces the same contracts through
  `microdrama/reviewgate.validate_requirements`, so gate-check, assembly
  and receipt scaffolding all fail closed on a broken continuity contract
  or a blocked route. Projects that declare no contracts run unchanged.

## Episode-level defects (E01 audit)

21 findings (D1-D21) are tracked in DEFECT_REPAIR_LEDGER.md: missing or
static actions, unreadable mouths in wide shots, inert reactions, melted
anatomy, loudness/silence problems, and process gaps. The ledger maps each
finding to the repair and acceptance evidence required. None is accepted;
the episode remains rejected.

## Evidence gaps that remain open

- Emotional naturalness of voice performances: requires human listening;
  not verifiable from transcripts, timing or loudness.
- Phoneme-level lip-sync on shots where faces are too small to read.
- Identity fidelity against locked character reference images (shots were
  compared to each other, not to references).
- Voice-timbre consistency across all lines.
- Real-playback audibility of the music bed and beat cues.

## Process rules adopted

- Delivery requires one full-speed continuous watch and one human listen;
  delivery notes must name the exact checks performed.
- Lip-sync only shots where the face is readable at delivery size.
- Music level checked by listening at phone-speaker volume; music from
  frame 0.
- Run the test suite in the build environment; clear script-validation
  warnings before render.
