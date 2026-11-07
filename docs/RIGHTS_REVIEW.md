# Rights and audience review

This is not a legal clearance or a new license grant.

## Private H3 reference implementation

The supplied ZIP's `vendor/h3-film-reference/README.md` describes private reference material without a verified root redistribution license. Its `docs/NOTICE` says six implementation files were excluded, but the ZIP actually contains those six files. This mismatch is recorded rather than silently trusted.

The six canonical-root implementation paths are withheld in this review: `agent/h3film/join.mjs`, `agent/h3film/render-all.mjs`, `agent/h3film/check-prompt.mjs`, `research/h3/tools-film.mjs`, `research/h3/soundtrack.mjs`, and `research/h3/runpod/comfy_r2v.py`, all beneath `vendor/h3-film-reference/`. Historical copies are withheld consistently. Exact paths/hashes appear in `WITHHELD_FILES.json`.

The owner has stated that redistribution is permitted and intends to make the repository private. The source notice conflicts with that statement; the concrete permission scope and actual repository audience still need reconciliation before repository inclusion. Private review/backup is different from public publication, but private repository collaborators remain an audience. The original source is preserved privately. The H3 join backend is not a supported runnable route in this package. Source permission would not by itself license model weights or provider access.

## OpenMontage-derived governor claim

The supplied `docs/NOTICE` attributes the `PriceQuoteRequired` concept in `magicdrama/governor.py` to AGPL-v3 OpenMontage and labels it 'local use only'. That wording is a historical notice, not a reliable summary of AGPL obligations or proof that the current file is a derivative. Inspection confirms a small exception class and pricing/spend logic, but no upstream diff/legal analysis has been completed. Do not assert a permissive whole-project license or public/deployment clearance until provenance and applicable license obligations are reviewed. The source and notice are retained; this preview is not clearance to publish.

## Other upstream code

Historical Forge snapshots contain third-party source and their own license files, including identity adapters and talking-video projects. Keep attribution and licenses with those sources. A source-code license does not automatically cover model weights, training data, character likenesses, voices, fonts or generated-media rights. Generated media is excluded from this source review. Upstream copyright/license notices are preserved, even where privacy redaction is applied elsewhere.
