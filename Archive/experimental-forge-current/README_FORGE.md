Layout: ViMax tree at root (agents/pipelines), plus forge/ (guard, llm, audio, assemble) and tools/*magichour*.
Config: configs/nvidia_magichour.yaml. Paid calls are locked: they need FORGE_LIVE=1 and an approved cap in .forge/ledger.json.
Tests: python -m pytest tests_forge

## Process gates (m10)

Hard gates added after the failed full-episode attempts, which broke on
process, not on the models: moving shots were generated before reference
stills were locked, a long episode was attempted before one short connected
scene was proven, and a draft went out without a continuous watch+listen
review. The gates fail closed and run BEFORE any credit is reserved
(`GateLocked` subclasses `SpendLocked`):

1. **Stills first** - `forge.gates.lock_stills(project_dir, {...})` sha256-pins
   every character/location reference still. Editing a still mid-production
   invalidates the lock; re-lock deliberately.
2. **Proof scene** - one connected scene (max 4 shots, 30 s, ONE location)
   must be assembled (`record_proof`), watched and approved by a named human
   (`signoff_proof`) before episode-scale renders (`require_proof`).
3. **Review before delivery** - `review_episode` writes a machine report
   (timeline coverage, silent stretches > 3 s, continuity flags, lip-sync
   state), a named human signs off after actually watching and listening
   (`signoff`), and `forge.gates.deliver.deliver` is the only export path -
   it refuses unsigned or since-changed cuts.

Wiring: `VideoGeneratorMagicHourAPI` calls `enforce_render_allowed` before
reserving credits (`render_mode="proof"` for the proof scene itself, default
`"episode"`). `forge.gates.continuity` adds a free PIL-only drift check of
rendered frames against locked stills, as review flags, not verdicts.

CLI: `python -m forge.gates status DIR` shows every gate's state;
`lock-stills`, `record-proof`, `signoff-proof`, `review`, `signoff`,
`deliver` run the flow by hand.

Emergency bypass: `FORGE_GATES=0` (prints a warning). Tests:
`python -m pytest tests_forge/test_gates.py`

## DramaSaga-derived planning upgrades (m14, additive)

`forge/planning/` adds four free pre-render layers: model route/duration/credit checks, bounded director prompts, story-state continuity, and generic floor-plan blocking. They extend the existing plan -> angle-still -> render-manifest flow; when no route, bible, or layout is supplied, the old flow and legacy manifest behavior remain unchanged.

Use `python3 -m forge.gates plan-check PROJECT_DIR ...` to write `out/e01_planning_upgrades.json`, or pass `--model`/`--director-bible` to `render-plan` for a route-aware manifest. See `docs/M14_DRAMASAGA_PLANNING.md` for the JSON shapes and limits. Route-aware execution is fail-closed: generator model/resolution, snapped duration, audio setting, and ledger estimate must match the quoted route before a live call. These checks are not proof of generated acting, voice, lip-sync or final-watch quality.

## Hardening (m15, additive)

m15 adds failure handling and regression guards without changing either
flow: ledger amount validation, atomic money/gate-state writes, corrupt
state failing closed, non-retryable LLM errors no longer burning the paid
fallback, the Claude fallback cap checked against the next call's reserve,
transient-tolerant Magic Hour polling that names the job id, default-on
resumable episode renders via `execute_plan` (m16; `fresh=True` to deliberately regenerate) (fingerprint-bound
to plan/route/still bytes; unknown submit outcomes recover or fail closed,
never blindly resubmit), a dialogue-preservation proof on the shot plan,
loud errors for unknown voices and non-audio paid TTS responses, ffmpeg path
escaping for caption burns, and pace/join edge cases that used to crash.
See docs/M15_HARDENING.md. Tests:
`python -m pytest tests_forge/test_hardening_m15.py` (62 tests).

## Local model additions (m21, optional)

Full pinned source for MultiTalk, InfiniteTalk, VACE and PuLID lives under
`third_party/`. See `third_party/VENDORED.md` and `docs/releases/m20_status.md`
for licenses and real runtime blockers. Model weights are not included.

`forge.integrations.plan_bridge.prepare_audio_driven_jobs` accepts selected
existing render-plan jobs and explicit per-person audio. It does not render.
`forge.integrations.execute.execute_audio_job` is the opt-in local GPU path:
current project gates, pinned inputs, weights paths and CUDA are rechecked
before the actual subprocess. It does not rent compute or approve spending.
A successful process exit is still an unreviewed output, never automatic QA.

PuLID's bundled `pipeline.py` is SDXL-Lightning. Use `pulid_sdxl_driver`;
the old FLUX-shaped wrapper fails closed rather than silently using wrong
arguments. Its upstream constructor can fetch models if they are uncached.
Keep separate upstream environments, review licenses and provision models
before execution. No new backend replaces existing routes or review gates.

`forge.integrations.script_v9.normalize_v9` preserves existing v9 dialogue
while mapping it to the shot-planning schema. The older accepted 13-second
ballroom audio is a separate proof and does not match v9's dialogue.

## Local model execution status

See `docs/LOCAL_MODEL_EXECUTION.md` for the new gate-enforcing visual paths,
explicit InfiniteTalk checkpoint and separate environment instructions.
`out/acceptance/current_inventory.json` separates implemented code, actual
execution evidence and remaining work per component. Full new-model and E01
acceptance is incomplete. Local tests are not a replacement for GPU model
execution, visual review or final episode approval.
