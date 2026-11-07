# Pre-production design discipline (m18)

Applied from a reviewed creator breakdown of a shoot-then-transform
workflow (user-supplied reference, a paid tool promotion - the discipline,
not the tool, is what was taken).

- `forge.planning.design_prep.asset_sheet` - one blueprint-style design
  sheet per recurring asset (character/prop/creature/vehicle/set piece):
  the appearance lock that stops per-shot drift.
- `location_sheet` - one sheet per scene location (description, fixed key
  features, time of day, lighting).
- `build_design_bible` - validated collection; duplicate names rejected.
- `validate_design_coverage(plan, bible)` - FAIL-CLOSED gate: any shot
  using a location without a sheet, a speaker without a character sheet,
  or an explicitly listed asset without a sheet blocks the plan with the
  full missing list. Nothing is invented to fill a gap.
- `attach_motion_anchor(shot, plate)` - binds a real local footage plate
  to a shot; the plate's camera movement and cut timing are the reference
  the generated shot must match. Missing/empty/non-video plates raise.
- `plate_cut_times` / `shots_from_plate` - ffmpeg scene detection recovers
  the plate's cuts locally and produces one timed shot skeleton per
  segment, each pre-anchored. Free; no service calls.

Integration: render jobs carry `motion_source` through the manifest
(forge/render_plan.py), and the director prompt gains a MOTION ANCHOR
section when a shot is anchored (forge/planning/director.py).

Limits: this module prepares and validates; it does not generate media,
does not verify that any generator honours the anchor, and does not claim
any external tool's output quality.
