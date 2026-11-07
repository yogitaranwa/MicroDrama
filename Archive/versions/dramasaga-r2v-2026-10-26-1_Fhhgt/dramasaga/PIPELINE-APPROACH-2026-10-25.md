# Pipeline approach changes, 2026-10-25 (v2)

Built from the updated FAILURE.TXT audit and the research log. Code-only;
no generation, paid calls or installs.

## Added

1. `magicdrama/audiofirst/references.py` - canonical reference bank with
   named views and per-shot coverage checks. Missing views are explicit
   gaps; no silent substitution of a different view.
2. `magicdrama/audiofirst/routes.py` - generation-route capability
   registry (supported / unverified / unsupported) with project failure
   evidence attached (F22/F23 prompt drift, F24 VACE pre-synthesis
   failure, D7 unreadable-mouth sync spend). Hard shot requirements block
   routes with failure evidence; operator overrides need a named operator
   and reason and never erase the evidence.
2b. Integration (fail-closed): `magicdrama/audiofirst/runner.py` (the live
   planning entry) now enforces declared contracts: when the brief or story
   declares `reference_bank`, coverage must pass or planning raises; when it
   declares `generation.route`/`hard_requirements`, the selected route must
   not be blocked by project failure evidence (named-operator overrides
   allowed, evidence retained). Reports are written to
   reference-coverage.json and route-plan.json. Stories without these
   declarations run unchanged.

3. `magicdrama/audiofirst/continuity.py` - story state schema now also
   accepts per-character `eyeline` and prop `count` (optional,
   backward-compatible). Eyeline changes across cuts in a continuous
   scene are flagged; within a shot they must be declared in `changes`
   like any other state transition.

## Limits

- Contracts and the registry are planning/evidence tools. They do not
  make a generator obey, do not verify generated pixels, and do not
  prove anyone watched or listened.
- Tests: 111 passing (mocks/synthetic logic only). The separate
  pyloudnorm-blocked repair tests remain uncounted.
