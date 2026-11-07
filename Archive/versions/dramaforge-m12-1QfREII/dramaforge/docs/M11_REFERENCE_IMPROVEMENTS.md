# M11: reference-based quality additions (additive only)

Added after reviewing a reference dialogue scene that held character
identity, wardrobe and set across every camera angle. Its methods, now in
code:

1. **Separate speaking shots** - `forge/dialogue_shots.py`
   `expand_episode()` splits every multi-speaker scripted shot into
   single-speaker clips (shot / reverse-shot), and inserts short silent
   reaction close-ups where a question lands before an answer. No generated
   clip ever carries two speakers, so each clip is small enough to check and
   cheap enough to replace. Pure planning; no model calls, no credits.

2. **Approve every angle as a still first** - `forge/gates/angle_stills.py`
   Derives the stills a planned shot list needs
   (`character:<name>:angle:<front|reverse|closeup|wide|tracking>` plus
   `location:<place>`) and fails closed while the still lock does not cover
   every angle the plan uses. `cross_angle_flags()` adds a PIL-only
   wardrobe-region comparison between a character's angle stills, as review
   flags, not verdicts. Reads the existing still lock; never re-locks.

3. **Restrained actions, dialogue-driven tension** - `forge/action_budget.py`
   Lints each shot's action text: more than two distinct movements, long
   sequential action chains, or camera-blocking movement under heavy
   dialogue are flagged before a prompt becomes a paid render.

4. **Caption hierarchy** - `forge/assemble/hook_captions.py`
   One ASS file with two layers: white word-by-word dialogue (bottom) and
   larger yellow hook/cliffhanger text (top). Pure editing; no generation.

5. **Proof review that names what was checked** - `forge/gates/proof_checklist.py`
   The proof-scene signoff now has an itemised companion: identity match,
   wardrobe match, set match, approved voices, lip-sync, no dead air,
   intelligible dialogue. Each item needs a named reviewer's check, and the
   checklist invalidates if the proof video changes afterwards.

Tests: `python3 -m pytest tests_forge/test_dialogue_shots.py
tests_forge/test_action_budget.py tests_forge/test_angle_stills.py
tests_forge/test_proof_checklist.py tests_forge/test_hook_captions.py`
(32 tests, plus the existing gate suite still passes.)

## Wiring (approved 2026-11-02, additive - old behaviour preserved)

- `forge/gates/enforce.py`: `enforce_render_allowed()` gained an optional
  `planned_shots` argument. When a plan exists - passed in, or written by
  the script stage at `out/e01_plan.json` - every render must also pass the
  angle-still gate. Episode renders additionally require a COMPLETED proof
  checklist once a project has started one (.forge/proof_checklist.json
  exists). With no plan file and no checklist, the gate behaves exactly as
  before.
- `forge/script_run.py`: new `write_plan_and_lint()` writes `e01_plan.json`
  (shot/reverse-shot plan) and `e01_action_lint.json` (action-budget report)
  after the script text; existing outputs are untouched.
- `forge/assemble/compose.py`: new `burn_caption_hierarchy()` burns the
  two-layer captions; `compose()` and `burn_captions()` are unchanged.
- `forge/gates/__main__.py`: new CLI commands `angle-stills`,
  `start-checklist`, `check`, `checklist`; `status` also prints checklist
  progress. Old commands unchanged.
- `forge/gates/__init__.py` re-exports the new gate functions.

Tests: `python3 -m pytest tests_forge/test_wiring.py` covers both the new
wiring and that the old flow is unchanged without the new artifacts.
