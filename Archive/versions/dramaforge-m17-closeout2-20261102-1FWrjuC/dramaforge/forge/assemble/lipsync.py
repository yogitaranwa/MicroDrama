"""Build the MuseTalk 1.5 shell command for one shot (run on a GPU host)."""
from pathlib import Path

def musetalk_cmd(video: str, audio_wav: str, out_dir: str, repo: str = "MuseTalk") -> str:
    cfg = Path(out_dir) / "task.yaml"
    yaml = f'task_0:\n video_path: "{video}"\n audio_path: "{audio_wav}"\n'
    return (f"mkdir -p {out_dir} && printf '{yaml}' > {cfg} && cd {repo} && MPLBACKEND=agg "
            f"python -m scripts.inference --inference_config {cfg} --result_dir {out_dir} "
            "--unet_model_path models/musetalkV15/unet.pth "
            "--unet_config models/musetalkV15/musetalk.json --version v15")


def latentsync_cmd(video: str, audio_wav: str, out_mp4: str, repo: str = "LatentSync") -> str:
    """Default engine: LatentSync 1.5 (weights from ByteDance/LatentSync-1.5)."""
    return (f"cd {repo} && MPLBACKEND=agg python -m scripts.inference "
            "--unet_config_path configs/unet/stage2.yaml "
            "--inference_ckpt_path checkpoints/latentsync_unet.pt "
            f"--inference_steps 20 --guidance_scale 1.5 --enable_deepcache "
            f"--video_path {video} --audio_path {audio_wav} --video_out_path {out_mp4}")

DEFAULT_ENGINE = "latentsync"


def sample_detections(video: str, detect_fn, every_s: float = 0.5) -> list:
    """Per-sample face detections for one shot. detect_fn(frame_bgr) ->
    [{'landmarks': (N,2) px, 'box': (x1,y1,x2,y2)}]; on a GPU host pass
    mp_detector.FaceDetector wrapped to that shape."""
    import cv2
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError(f"cannot open video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(fps * every_s)))
    frames, idx = [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            frames.append(detect_fn(frame) or [])
        idx += 1
    cap.release()
    return frames


def precheck_shot(video: str, detect_fn, every_s: float = 0.5) -> dict:
    """The face-coverage verdict for one shot BEFORE a lip-sync run."""
    from forge.assemble.face_policy import classify_shot
    return classify_shot(sample_detections(video, detect_fn, every_s))


def lipsync_job(video: str, audio_wav: str, out: str, engine: str = DEFAULT_ENGINE,
                detect_fn=None, every_s: float = 0.5) -> dict:
    """Build the GPU command for one shot, gated on the face policy: a shot
    the shipping detector was never validated on (multi-face) is refused, a
    profile/sparse-face shot is built but flagged for human review first.
    Without a detect_fn the policy cannot run and the job is marked
    'unchecked' - never silently 'ok'."""
    from forge.gates.common import GateLocked
    if detect_fn is not None:
        verdict = precheck_shot(video, detect_fn, every_s)
    else:
        verdict = {"verdict": "unchecked",
                   "reasons": ["no face detector supplied; policy not run"]}
    if verdict["verdict"] == "unsupported":
        raise GateLocked(
            "lip-sync refused: shot is multi-face, which the shipping "
            f"detector was never validated on: {verdict['reasons']}")
    cmd = latentsync_cmd(video, audio_wav, out) if engine == "latentsync"         else musetalk_cmd(video, audio_wav, out)
    return {"engine": engine, "cmd": cmd, "face_policy": verdict}


def main(argv=None) -> int:
    """CLI: python -m forge.assemble.lipsync VIDEO AUDIO --out OUT
    [--engine latentsync|musetalk] [--detector none|opencv]
    Prints the gated job as JSON; exit 3 when the face policy refuses."""
    import argparse, json, sys
    ap = argparse.ArgumentParser(prog="forge.assemble.lipsync")
    ap.add_argument("video")
    ap.add_argument("audio_wav")
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", default=DEFAULT_ENGINE, choices=["latentsync", "musetalk"])
    ap.add_argument("--detector", default="mediapipe", choices=["none", "mediapipe"])
    ap.add_argument("--every-s", type=float, default=0.5)
    args = ap.parse_args(argv)
    detect_fn = None
    if args.detector == "mediapipe":
        import cv2
        import mediapipe as mp
        fm = mp.solutions.face_mesh.FaceMesh(static_image_mode=True,
                                             max_num_faces=4)

        def detect_fn(frame):
            h, w = frame.shape[:2]
            res = fm.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if not res.multi_face_landmarks:
                return []
            out = []
            for face in res.multi_face_landmarks:
                pts = [(p.x * w, p.y * h) for p in face.landmark]
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                out.append({"landmarks": pts,
                            "box": (min(xs), min(ys), max(xs), max(ys))})
            return out
    try:
        job = lipsync_job(args.video, args.audio_wav, args.out,
                          engine=args.engine, detect_fn=detect_fn,
                          every_s=args.every_s)
    except Exception as exc:  # GateLocked or detector failure
        from forge.gates.common import GateLocked
        if isinstance(exc, GateLocked):
            print(json.dumps({"refused": True, "reason": str(exc)}))
            return 3
        raise
    print(json.dumps({"refused": False, **job}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
