# v12 REVIEW DRAFT - v11 plus durable financial lock (2026-10-26)

All v9/v10/v11 bounds still apply: s16 9s timing PROPOSED, wardrobe pin
PROVISIONAL, no budget approval, v7 remains delivered, no 100% claims,
code/test proofs only (no visual proof).

New in v12 (local code/test only, no paid generation):
Durable financial lock. If the provider ever settles a job ABOVE the approved
estimate, the receipts record a settle_up_unreconciled marker that blocks
every spend path (frames, video, lip-sync, legacy route) across fresh
invocations - a restart cannot drop it. Read-only work stays open: resume
polling completes submitted jobs, assemble/edit/dry-run run normally, and
ordinary stop reasons never lock. Clearing requires an explicit
--reconcile-settle-up '<reason>' after checking the provider account; the
reason and prior marker are kept in settle_up_history. The lock is not
payment approval and never clears itself.

Suite: 59/59 local tests green.
