# m17 face-policy gate: refuse multi-face shots, flag profile/sparse shots for
# human review BEFORE burning GPU time (docs/LIPSYNC_PLAN.md caveats).
GATE_JSON=$(/tmp/ls/bin/python -m forge.assemble.lipsync /tmp/real.mp4 /tmp/aud.wav --out /tmp/gate_out.mp4 --detector mediapipe)
echo "STEP_GATE $GATE_JSON"
case "$GATE_JSON" in *'"refused": true'*) echo "STEP_GATE_REFUSED - skipping inference"; exit 3;; esac

set -x
cd /kaggle/working
pip -q install uv >/dev/null 2>&1
uv venv /tmp/ls --python 3.10 && echo STEP_VENV
git clone -q https://github.com/bytedance/LatentSync.git LatentSync && echo STEP_CLONE
cd LatentSync
uv pip install -q --python /tmp/ls/bin/python -r requirements.txt mediapipe scikit-image huggingface_hub 2>&1 | tail -5
echo STEP_PIP
apt-get -qq install -y libgl1 >/dev/null 2>&1
/tmp/ls/bin/python -c "
from huggingface_hub import hf_hub_download as d
for f in ['latentsync_unet.pt','whisper/tiny.pt']: print(d('ByteDance/LatentSync-1.5',f,local_dir='checkpoints'))"
echo STEP_CKPT
cd /kaggle/working && cp -r LatentSync LatentSync_mp && cp /tmp/mpfd.py LatentSync_mp/latentsync/utils/face_detector.py
for V in LatentSync LatentSync_mp; do
  cd /kaggle/working/$V
  /tmp/ls/bin/python -m scripts.inference --unet_config_path configs/unet/stage2.yaml --inference_ckpt_path checkpoints/latentsync_unet.pt --inference_steps 20 --guidance_scale 1.5 --enable_deepcache --video_path /tmp/real.mp4 --audio_path /tmp/aud.wav --video_out_path /kaggle/working/out_$V.mp4 2>&1 | tail -4
  echo STEP_INFER_DONE_$V
done
ls -l /kaggle/working/out_*.mp4
