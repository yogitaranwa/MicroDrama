# Pipeline approach changes, 2026-10-25 (v2)

Built from the updated FAILURE.TXT audit and the research log. Code-only;
no generation, paid calls or installs.

## Added

1. `microdrama/continuity.py` - continuity contracts:
   - Canonical reference bank with named views (front, three_quarter,
     profile, back, full_body, close, wide, detail). A shot's framing must
     match a banked view per visible character. A missing view is an
     explicit gap; the planner never substitutes another view and labels
     it as the requested one. (Mechanism adapted from open-source
     reference-selection approaches.)
   - Per-shot start/end state: position, facing, eyeline, wardrobe,
     emotion, lighting, prop hand/count. Cut transitions flag unexplained
     changes; only physical fields may reset across a scene change.
   - Scripted actions must be structured as before/contact/after phases,
     each with review items. Schema completeness only - only media review
     can establish the phases occurred.
   - CLI: `python3 run_pipeline.py validate-continuity --contract c.json`
1b. Integration (fail-closed): `microdrama/reviewgate.validate_requirements`
   now enforces declared contracts for every gate consumer (gate-check,
   assemble, receipt scaffolding). A requirements config may declare a
   `continuity` contract (must pass) and a `generation` section (selected
   route must not be blocked by project failure evidence; operator
   overrides need a named operator and reason; unknown routes rejected).
   Undeclared sections keep legacy behavior.

2. `microdrama/routes.py` - route capability registry:
   - Routes declare camera/eyeline/wardrobe/prop-action/audio/structure
     capabilities as supported / unverified / unsupported, with the
     project evidence attached (F22/F23 prose-prompt drift, F24 VACE
     pre-synthesis failure, D7 unreadable-mouth sync spend).
   - Hard shot requirements block routes with failure evidence. An
     operator override needs a named operator and reason, and never
     erases the evidence.
   - CLI: `python3 run_pipeline.py plan-route --requirements r.json`

## Limits

- These contracts and the registry are planning and evidence tools. They
  do not make a generator obey, do not verify generated pixels, and do
  not prove anyone watched or listened.
- "unverified" means no accepted result in this project, not that the
  route cannot work.
- Tests: 78 passing (mocks/synthetic logic only). The separate
  pyloudnorm-blocked repair tests remain uncounted.
