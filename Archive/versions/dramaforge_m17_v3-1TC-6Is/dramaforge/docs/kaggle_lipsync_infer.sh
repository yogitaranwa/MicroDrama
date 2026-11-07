# m17 face-policy gate: refuse multi-face shots, flag profile/sparse shots for
# human review BEFORE burning GPU time (docs/LIPSYNC_PLAN.md caveats).
GATE_JSON=$(/tmp/ls/bin/python -m forge.assemble.lipsync /tmp/real.mp4 /tmp/aud.wav --out /tmp/gate_out.mp4 --detector mediapipe)
echo "STEP_GATE $GATE_JSON"
case "$GATE_JSON" in *'"refused": true'*) echo "STEP_GATE_REFUSED - skipping inference"; exit 3;; esac

export MPLBACKEND=agg
ls /kaggle/working/LatentSync/checkpoints
for V in LatentSync LatentSync_mp; do
  cd /kaggle/working/$V
  /tmp/ls/bin/python -m scripts.inference --unet_config_path configs/unet/stage2.yaml --inference_ckpt_path checkpoints/latentsync_unet.pt --inference_steps 20 --guidance_scale 1.5 --enable_deepcache --video_path /tmp/real.mp4 --audio_path /tmp/aud.wav --video_out_path /kaggle/working/out_$V.mp4 2>&1 | tail -6
  echo STEP_INFER_DONE_$V
done
ls -l /kaggle/working/out_*.mp4
