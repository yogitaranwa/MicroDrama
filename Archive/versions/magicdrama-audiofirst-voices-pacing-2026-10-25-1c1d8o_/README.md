# Voice pacing pipeline update - 2026-10-25

Adds Eleven v3 pacing tags to the audio-first dialogue planner: [rushed], [urgent], [rapid-fire], [interrupting], [clipped]. This addresses the user's feedback that the first sample had the right voices but felt very slow. It changes request text only; no provider call was made.

Validation: 229 unittest tests pass via `python3 -m unittest discover -s tests -q`.
