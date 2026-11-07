"""Build the MuseTalk 1.5 shell command for one shot (run on a GPU host)."""
import os
from pathlib import Path

# Observed on the Kaggle GPU run (m17, LatentSync 1.5): the face-restore
# pass smears any text pixels inside the face box - pre-burned captions in the
# input come out unreadable. Captions must be burned AFTER lip-sync.
POST_NOTES = ["burn captions after lip-sync; the face-restore pass smears "
              "existing text pixels inside the face box"]


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
    from forge.assemble import stage_log
    stage_log.check_clean_for_lipsync(video)  # GateLocked when captioned
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
    job = {"engine": engine, "cmd": cmd, "face_policy": verdict,
           "post_notes": POST_NOTES}
    if not (os.path.exists(video) and stage_log.record(video, stage_log.PLANNED)):
        job["stage_log"] = ("not written for this input; caption ordering "
                            "not tracked (read-only or missing input)")
    return job


def multiface_cmds(video: str, audio_wav: str, out: str, box,
                   engine: str = DEFAULT_ENGINE, repo: str = "LatentSync") -> list:
    """Per-face pipeline for a multi-face shot WITH a speaker assignment:
    crop the speaking face region, sync the crop, composite it back.
    The unassigned multi-face case stays refused in lipsync_job - this plan
    exists so an assigned speaker in a group shot is a supported route,
    not a gate bypass. Runs on the GPU host like the single-face command."""
    x1, y1, x2, y2 = [int(v) for v in box]
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"speaker box must be x1,y1,x2,y2 with positive area: {box}")
    w, h = x2 - x1, y2 - y1
    crop = (f"ffmpeg -y -i {video} -filter:v crop={w}:{h}:{x1}:{y1} "
            "-c:a copy /tmp/face_crop.mp4")
    sync = (latentsync_cmd("/tmp/face_crop.mp4", audio_wav, "/tmp/face_sync.mp4", repo)
            if engine == "latentsync" else
            musetalk_cmd("/tmp/face_crop.mp4", audio_wav, "/tmp/face_sync_dir", repo))
    back = (f"ffmpeg -y -i {video} -i /tmp/face_sync.mp4 -filter_complex "
            f"[0:v][1:v]overlay={x1}:{y1}[v] -map [v] -map 0:a? -c:a copy {out}")
    return [crop, sync, back]


def lipsync_job_multiface(video: str, audio_wav: str, out: str, speaker_box,
                          engine: str = DEFAULT_ENGINE, detect_fn=None,
                          every_s: float = 0.5) -> dict:
    """A multi-face shot with an assigned speaker face: the policy verdict is
    still computed and kept (multi-face => human review flag), but instead of
    refusing, the job plans the per-face pipeline for the assigned face."""
    from forge.assemble import stage_log
    stage_log.check_clean_for_lipsync(video)  # GateLocked when captioned
    if detect_fn is not None:
        verdict = precheck_shot(video, detect_fn, every_s)
    else:
        verdict = {"verdict": "unchecked",
                   "reasons": ["no face detector supplied; policy not run"]}
    if verdict["verdict"] not in ("unsupported", "unchecked"):
        raise ValueError(
            f"lipsync_job_multiface is for multi-face shots; policy says "
            f"{verdict['verdict']} - use lipsync_job")
    # Fail closed when another detected face intersects the speaker crop:
    # the composite would alter that face's pixels too.
    if detect_fn is not None:
        from forge.assemble.face_policy import box_area
        frames = sample_detections(video, detect_fn, every_s)
        sx1, sy1, sx2, sy2 = [float(v) for v in speaker_box]
        for dets in frames:
            for d in dets:
                bx1, by1, bx2, by2 = [float(v) for v in d.get("box", (0, 0, 0, 0))]
                ix = max(0.0, min(sx2, bx2) - max(sx1, bx1))
                iy = max(0.0, min(sy2, by2) - max(sy1, by1))
                inter = ix * iy
                if inter == 0:
                    continue
                # the speaker's own face is expected inside its box; another
                # face whose centre falls outside the box is a bystander
                cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2
                inside = sx1 <= cx <= sx2 and sy1 <= cy <= sy2
                if not inside and inter > 0.05 * box_area(d["box"]):
                    from forge.gates.common import GateLocked
                    raise GateLocked(
                        "per-face route refused: another face overlaps the "
                        f"speaker crop by {int(inter)}px^2; compositing "
                        "would modify the bystander face")
    cmds = multiface_cmds(video, audio_wav, out, speaker_box, engine)
    job = {"engine": engine, "route": "per-face", "cmds": cmds,
           "face_policy": {**verdict, "review_required": True},
           "post_notes": POST_NOTES}
    if not (os.path.exists(video) and stage_log.record(video, stage_log.PLANNED)):
        job["stage_log"] = ("not written for this input; caption ordering "
                            "not tracked (read-only or missing input)")
    return job


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
    ap.add_argument("--speaker-box", default=None,
                    help="x1,y1,x2,y2 of the speaking face; routes a multi-face "
                         "shot to the per-face pipeline instead of refusing")
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
        if args.speaker_box:
            box = tuple(float(v) for v in args.speaker_box.split(","))
            job = {"refused": False,
                   **lipsync_job_multiface(args.video, args.audio_wav, args.out,
                                           box, engine=args.engine,
                                           detect_fn=detect_fn,
                                           every_s=args.every_s)}
            print(json.dumps(job))
            return 0
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
