# RIFE 24->60 Kaggle test plan (pending user's GitHub exception for hzwer/Practical-RIFE)

Goal: ONE free test proving/disproving high-quality 60fps on OUR content. Input:
Drive file interp-test-input-e01s08-24fps.mp4 (e01s08.mp4, 720x1296, 24fps, 7.292s, 175 frames,
contains the fast string-whip motion where minterpolate measured SSIM 0.713 worst-case).

Notebook cells (driven by me through the Kaggle browser UI, interactive session - no user Run chore):
1. Markdown: purpose, source links (repo, MIT LICENSE, weights note), process flow.
2. Setup: git clone --depth 1 https://github.com/hzwer/Practical-RIFE; download a pinned model
   version (train_log flownet.pkl, per repo model list); pip install only official-PyPI deps
   (torch is preinstalled on Kaggle GPU images; opencv-python-headless if absent).
3. Runtime check: nvidia-smi capture (proves actual GPU + type, recorded as evidence).
4. Convert input mp4 to PNG frame sequence (ffmpeg or cv2).
5. Run RIFE inference 24->48 and 24->60 outputs (both saved; 48 is a fallback quality point).
6. Reconstruction self-check: rebuild 24fps from even frames only via RIFE, PSNR/SSIM vs the
   dropped odd frames; report mean/min - comparable to the minterpolate baseline (25.8/0.837 mean,
   0.713 min on this same clip family).
7. Reassemble mp4s (crf 16, audio copied), write outputs + metrics.json back to Drive.
8. Timing capture: wall time per stage (evidence for minutes-per-episode claim, replacing estimate).

Success criteria (measurable, human playback still final):
- reconstruction SSIM min on fast frames > minterpolate's 0.713 on the same frames, AND
- no visible rubber-band artifacts in the dense grid, AND
- total runtime supports ~90s episodes inside Kaggle weekly quota (30h, demand-variable).

Stop conditions: any paid prompt, quota block, driver/Vulkan/CUDA failure, or license surprise ->
stop, screenshot, report. No other repos/models without a new exception.
