# v11 REVIEW DRAFT - v10 plus spend-safety hardening (2026-10-26)

All v9/v10 bounds still apply: s16 9s timing PROPOSED, wardrobe pin
PROVISIONAL, no budget approval, v7 remains delivered, no 100% claims,
code/test proofs only (no visual proof).

New in v11 (local code/test only, no paid generation):
1. Unknown reference names in the manifest are now hard validation errors at
   every stage gate (previously: silently dropped from prompts, crash in the
   frames stage).
2. The deprecated legacy whole-shot route refuses beat-subdivided selections
   BEFORE any spend: its output cannot enter the assemble stage, so running it
   would burn credits on unusable video. Already-verified historical shots
   still skip cleanly on resume.
3. Per-frame billing settle drift is reconciled, not just recorded: a
   settle-down adjusts the receipts ledger; a settle-UP (provider charges more
   than the approved estimate) halts the run with a reconcile instruction.

Suite: 58/58 local tests green.
