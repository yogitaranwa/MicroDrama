# Clean source release

20 October 2026. Base: the supplied yesterday's commit archive, with its single `DramaSaga-main/` root retained. Current code was recovered from the live restricted Drive source export and merged without deleting base-only source/research. The supplied ZIP does not establish a verified Git commit SHA.

## Scope

Included: original modular production/QA/tests, scripts, notebooks, benchmark research; all current audio-first code, form, provider adapters, writers, execution controls, subtitles, local assembly, soundtrack license gate and season ZIP continuation; six unchanged H3 modules actually taken. `CHANGE_SUMMARY.json` lists exact added/changed/removed paths relative to the supplied ZIP. `SOURCE_MANIFEST.json` binds release content hashes and the base archive hash.

Not a full H3 checkout: the earlier source review counted 879 source/documentation/config/prompt files in a source-only extraction. This release includes the six selected modules, their manifest and vendor note, not the other source files, the original repository's media/demo datasets, external services or deployment dependencies. A request for the entire H3 codebase would require a separately scoped source inventory/rights/dependency review, not silently importing everything from its multi-gigabyte archive.

## H3 reuse and rights

Verbatim modules: soundtrack.mjs, tools-film.mjs, render-all.mjs, join.mjs, check-prompt.mjs and comfy_r2v.py, under their supplied relative paths in `vendor/h3-film-reference`. All six match the hashes in that folder's source manifest. Our optional wrapper executes only join.mjs for local assembly; our own Python path remains available. The other modules are reference material, not a complete runnable H3 deployment.

Keep this mixed source release private/restricted. Attribution stays in NOTICE and the vendor folder. No public redistribution or blanket rights clearance is asserted. MiniMax H3 model-weight rights and compute approval are separate; the H3 model entry point refuses. No weights, GPU/Modal/RunPod jobs or vendor agent/service orchestration were run.

## Verification

192 tests passed on the live Drive source download before packaging and are rerun on this clean release and the downloaded ZIP. Provider HTTP is mocked. Own and project-owner local assembly paths use real ffmpeg synthetic-media fixtures; subtitle/name/introduction placements were visually checked. No live text/image/voice/video generation or spend was used for release verification.

Files are screened for credential prefixes and credential/ledger/cache paths. No detected key material, .env, private key, spend ledger, virtual environment, installed dependency, model weight or generated media is included. Static scanning is not a universal secret/malware guarantee. Archived scripts/notebooks are retained as historical source and may install/download/call APIs when explicitly run; they are not executed as part of import.

## Current limits

See AUDIO_FIRST.md for one current status, rather than old appended gap lists. Live route/account/model behavior and pricing, inference quality, emotional voices, lip sync, automatic word alignment, creative continuity and final playback still require scoped real tests. `produce` makes actual previews from accepted local media, not a guaranteed unattended first-time paid film. Archive content and the original benchmark research are preserved as historical material, not current API/pricing promises.
