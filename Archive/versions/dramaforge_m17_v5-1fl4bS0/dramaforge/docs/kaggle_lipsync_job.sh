# m17 face-policy gate: refuse multi-face shots, flag profile/sparse shots for
# human review BEFORE burning GPU time (docs/LIPSYNC_PLAN.md caveats).
SPEAKER_ARG=""
if [ -n "$SPEAKER_BOX" ]; then SPEAKER_ARG="--speaker-box $SPEAKER_BOX"; fi
GATE_JSON=$(/tmp/ls/bin/python -m forge.assemble.lipsync /tmp/real.mp4 /tmp/aud.wav --out /tmp/gate_out.mp4 --detector mediapipe $SPEAKER_ARG)
echo "STEP_GATE $GATE_JSON"
case "$GATE_JSON" in *'"refused": true'*) echo "STEP_GATE_REFUSED - skipping inference"; exit 3;; esac
case "$GATE_JSON" in
  *'"review_required": true'*)
    if [ "$REVIEW_OK" = "1" ]; then
      echo "STEP_REVIEW_RECORDED - human review supplied, proceeding"
    else
      echo "STEP_REVIEW_REQUIRED - pausing before inference; set REVIEW_OK=1 only after a real human review of this shot"
      exit 4
    fi;;
esac

# Per-face route: with SPEAKER_BOX set, run inference on the speaker crop
# and composite the result back - bystander pixels are never touched.
INFER_IN=/tmp/real.mp4
if [ -n "$SPEAKER_BOX" ]; then
  IFS=',' read X1 Y1 X2 Y2 <<< "$SPEAKER_BOX"
  ffmpeg -y -i /tmp/real.mp4 -filter:v crop=$((X2-X1)):$((Y2-Y1)):$X1:$Y1 -c:a copy /tmp/real_crop.mp4
  INFER_IN=/tmp/real_crop.mp4
fi

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
  /tmp/ls/bin/python -m scripts.inference --unet_config_path configs/unet/stage2.yaml --inference_ckpt_path checkpoints/latentsync_unet.pt --inference_steps 20 --guidance_scale 1.5 --enable_deepcache --video_path $INFER_IN --audio_path /tmp/aud.wav --video_out_path /kaggle/working/out_$V.mp4 2>&1 | tail -4
  if [ -n "$SPEAKER_BOX" ]; then
    ffmpeg -y -i /tmp/real.mp4 -i /kaggle/working/out_$V.mp4 -filter_complex "[0:v][1:v]overlay=$X1:$Y1[v]" -map "[v]" -map 0:a? -c:a copy /kaggle/working/out_${V}_composited.mp4
    echo STEP_COMPOSITE_DONE_$V
  fi
  echo STEP_INFER_DONE_$V
done
ls -l /kaggle/working/out_*.mp4
