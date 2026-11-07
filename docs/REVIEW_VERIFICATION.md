# Review verification

Date: 6 November 2026. Scope: canonical sanitized root, not every archived version.

## Executed

Command: `python -m unittest discover -s tests -v`, run from the staged root using an existing validation environment.

Environment: Python 3.11.17; ffmpeg version 4.4.2-0ubuntu0.22.04.1 Copyright (c) 2000-2021 the FFmpeg developers. Reused existing environment, not a clean install from requirements.txt.

Result: **261 tests run, 260 passed, 1 errored**, 40.331 seconds. Failing test: `test_edit_profile.EditEffectTests.test_a_steady_music_bed_and_a_trimmed_lead_in_assemble_to_the_exact_frames`.

Failure path: `native_mix.assemble_native_episode` -> `_run` -> FFmpeg audio filter graph. Error: `The following filters could not choose their formats: Parsed_sidechaincompress_20`. FFmpeg then reported filter reinitialization/input-output failure. No source modification applied. Whether dependency/environment differences explain it is unverified.

Static Python syntax parsing: zero syntax errors in the staged source at initial scan. Syntax checking does not establish successful imports or runtime behavior.

## Not executed or not established

- No clean dependency installation or package-index validation of supplied pins.
- No live generation, paid request or new model inference for this consolidation.
- No independent runtime test of every historical archived version.
- No full-speed acceptance watch/listen of an episode in this consolidation.
- No corrected full-audio GPU test; that prepared job was paused before launch.
- No remote commit, branch update, visibility change or force push.

Historical test counts in source documents remain historical. Experimental Forge's earlier 567 passing tests plus 30 subtests are a separate code-family result and do not override the canonical-root error.


## Expanded archive/privacy pass

42 further recovered archives were added under `Archive/expanded-versions/` without rebuilding or replacing the selected canonical source. Legacy partial account identifiers, account URLs and private message references were redacted. Required upstream attribution and license files are preserved. All staged Python files parse. No new inference or paid generation was performed. Earlier source-only package checksums are superseded by this package manifest.
