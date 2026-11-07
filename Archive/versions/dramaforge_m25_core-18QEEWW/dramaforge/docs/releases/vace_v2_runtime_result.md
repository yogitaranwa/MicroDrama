# VACE Version2 runtime result

Observed 2026-11-06 05:03 IST. Version2 failed after2801.8s.

- Isolated install steps00-08 passed.
- CLIhelp failed because inherited matplotlib inline backend was unsupported.
- Mixed-dtype GPU numerical comparison passed.
- Pinned official weights download completed at174.2s.
- WanVace construction completed at339.6s.
- Generation remained in CPU-half T5 encoder forward stacks until the2700s subprocess timeout. No video.

Version3 uses a test-only source-preserving wrapper placing the encoder onGPU1. It requires finite encoder outputs and keeps the existing output API. It is unaccepted until the actual result and any video are reviewed. Also sets MPLBACKEND=Agg. Third-party source files are unchanged.

Source notebook: [private-project-source]

This evidence does not establish full coding completion, production routing, E01 completion, or paid-use permission.
