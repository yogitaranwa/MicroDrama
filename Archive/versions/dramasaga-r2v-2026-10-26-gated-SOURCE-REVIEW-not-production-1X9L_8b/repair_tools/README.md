# Research-backed audio repair

Standalone CPU repair, not a delivery-gate bypass. No neural weights or paid API calls.

Install from official PyPI into an isolated environment:
`python3 -m pip install --index-url https://pypi.org/simple -r repair_tools/requirements-audio.txt`

Run `python3 repair_tools/audio_repair.py --help` and pass the dry voice MP3, full music source, assembly plan, timed source-line plan and a fresh output directory.
Run `cd repair_tools && python3 -m unittest -v test_audio_repair`.

The output is always REVIEW_REQUIRED. It must never be sent to final assembly as approved audio without actual listening. It cannot fix missing visual actions, voice timbre or emotional performance. Original v3 timings are preserved by default. v44 repair requirements are preparation, not reviewed assets or authorization to generate.

Uses pyloudnorm (MIT) by Christian J. Steinmetz and Joshua D. Reiss, https://github.com/csteinmetz1/pyloudnorm ; paper https://csteinmetz1.github.io/pyloudnorm-eval/paper/pyloudnorm_preprint.pdf . SoundFile uses BSD-3-Clause. FFmpeg is invoked as an installed external tool, no binary redistributed. Music license in MUSIC_ATTRIBUTION.txt must accompany actual media delivery.
