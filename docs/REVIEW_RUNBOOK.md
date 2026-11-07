# Review runbook

## 1. Inspect before executing

Unzip into a new directory. Read the root README, findings, verification and rights review. Do not overlay this on an existing working project. Do not execute notebooks or archived scripts during inventory review. There is no root `.git` directory and no credentials are required for reviewing source.

## 2. Environment

Use a fresh Python environment. Inspect `requirements.txt`; its supplied pins include versions that have not been checked against a package index in this consolidation. No dependency upgrades or installability claims are made. Preserve the source file rather than quietly replacing dependencies. FFmpeg/ffprobe must be available for media tests. Some historical repair tools need optional packages not listed in the old README's counted test suite.

The verification environment reused an existing local Python environment, not a clean install from this requirements file. Reproduce that limitation when interpreting results.

## 3. Offline entry points

`python audiofirst.py --help` lists the canonical commands. The supplied `examples/pilot/brief.json` plus `examples/pilot/story.json` are the lowest-risk planning inputs: no model needs to invent a story. Keep outputs outside source tracking. Review missing-image labels rather than treating an animatic as generated film.

Run `python -m unittest discover -s tests -v` from the root. The current baseline is one known FFmpeg audio-mixing error, not a green suite. See verification. Do not adjust test expectations merely to obtain green output.

## 4. Before any generation

Choose one short dialogue proof first, not an entire multi-location episode. Establish a script, exact spoken-audio waveform/duration, character and wardrobe references, shot state, actual backend capability and current quote. Obtain approval for exact costs. Unknown jobs stay unknown until reconciled; never auto-resubmit a timeout. Review one actual full-duration clip before continuation.

## 5. Before assembly or delivery

Bind every accepted clip to current inputs and measured duration. Check that spoken audio is not cropped. Assemble in explicit shot order, probe actual output streams/duration, inspect the pixels and listen at playback speed. Tests and transcripts do not establish emotional delivery, believable action or lip sync. Final acceptance must name the actual file and checks performed.

## 6. Git review gate

This package is a preview. Do not push it automatically. Repository visibility, collaborator audience, unresolved rights, review approval, exact new commit message, force-update capability and live master SHA all remain checks before the requested history/consolidation operation.
