"""Execute the approved 4-shot R2V probe, v5 re-bind. Authority: user
WhatsApp 2026-10-26 02:47:27 IST "good generate then" + 02:47:52 IST "Yes" to
the exact +144-credit question (cap 1,248). Hard rules: exactly these 4 jobs,
stop after 4, no rerolls, no upgrades, NO auto-resubmit; on ANY validation
error or unknown API outcome: STOP immediately and report the raw outcome.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from magicdrama.audiofirst import r2v

API = "https://api.magichour.ai"
ROOT = Path(__file__).resolve().parent
KEY_FILE = Path("/home/sandbox/.vault/magic-hour-api-key-70da61/password")
RECEIPTS = ROOT / "probe-2026-10-26" / "receipts-v5.json"

LOCAL = {
    "ref-draconia-front-close.png": "/downloads/ref-draconia-front-close.png",
    "ref-draconia-fullbody.png": "/downloads/ref-draconia-fullbody.png",
    "ref-harry-fullbody.png": "/downloads/ref-harry-fullbody.png",
    "ref-yule-ball-location.png": "/downloads/ref-yule-ball-location.png",
    "audio-new/e01-line-06.mp3": str(ROOT / "probe-2026-10-26/audio-new/e01-line-06.mp3"),
    "audio-new/e01-line-07.mp3": str(ROOT / "probe-2026-10-26/audio-new/e01-line-07.mp3"),
    "audio-new/e01-line-08.mp3": str(ROOT / "probe-2026-10-26/audio-new/e01-line-08.mp3"),
    "audio-new/e01-line-09.mp3": str(ROOT / "probe-2026-10-26/audio-new/e01-line-09.mp3"),
}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stop(msg, receipts):
    receipts["stopped"] = msg
    RECEIPTS.write_text(json.dumps(receipts, indent=2))
    print("STOP:", msg)
    sys.exit(2)


def main():
    token = KEY_FILE.read_text().strip()
    H = {"Authorization": "Bearer " + token}
    manifest = json.loads((ROOT / "probe-2026-10-26/probe-manifest-v5-draft.json").read_text())
    bank = json.loads((ROOT / "harry-draconia-reference-bank.json").read_text())
    receipts = {"manifest_id": manifest["id"], "manifest_sha256": manifest["manifest_sha256"],
                "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "uploads": [], "jobs": []}

    # 1) verify local image hashes against the bank before anything leaves
    bank_hash = {r["id"]: r["sha256"] for r in bank["references"]}
    for name, path in LOCAL.items():
        h = sha256(path)
        rid = name.rsplit("/", 1)[-1][:-4]
        if rid in bank_hash and h != bank_hash[rid]:
            stop("hash mismatch for %s vs bank" % name, receipts)

    # 2) upload URLs - ONE request per asset: multi-item responses come back
    # type-grouped, not request-ordered (learned from 2026-10-26 stop).
    path_for = {}
    for name, path in sorted(LOCAL.items()):
        ext = name.rsplit(".", 1)[1].lower()
        typ = "audio" if ext in ("wav", "mp3") else "image"
        r = requests.post(API + "/v1/files/upload-urls", headers=H,
                          json={"items": [{"extension": ext, "type": typ}]}, timeout=60)
        if r.status_code != 200:
            stop("upload-urls %s HTTP %s: %s" % (name, r.status_code, r.text[:500]), receipts)
        returned = r.json().get("items")
        if not isinstance(returned, list) or len(returned) != 1:
            stop("upload-urls %s unexpected shape: %s" % (name, r.text[:500]), receipts)
        item = returned[0]
        if item["file_path"].rsplit(".", 1)[-1].lower() != ext:
            stop("upload-url extension mismatch for %s -> %s" % (name, item["file_path"]), receipts)
        up = requests.put(item["upload_url"], data=Path(path).read_bytes(), timeout=120)
        if up.status_code not in (200, 201, 204):
            stop("PUT %s HTTP %s" % (name, up.status_code), receipts)
        path_for["api-assets/PENDING_UPLOAD/" + name] = item["file_path"]
        receipts["uploads"].append({"name": name, "sha256": sha256(path),
                                    "file_path": item["file_path"]})
        print("uploaded", name, "->", item["file_path"])
    print("uploaded", len(receipts["uploads"]), "assets")

    # 3) submit 4 jobs sequentially, stop on anything unexpected
    for job in manifest["jobs"]:
        body = job["request"]["body"]
        body = dict(body)
        body["references"] = [{"file_path": path_for[ref["file_path"]], "name": ref["name"]}
                              for ref in body["references"]]
        r2v.validate_request_shape(body["model"], body["end_seconds"], body["resolution"],
                                   body["aspect_ratio"], len(body["references"]),
                                   audio=body.get("audio", False))
        r = requests.post(API + "/v1/text-to-video", headers=H, json=body, timeout=60)
        if r.status_code != 200:
            stop("submit %s HTTP %s: %s" % (job["shot_id"], r.status_code, r.text[:500]), receipts)
        data = r.json()
        if not data.get("id") or not isinstance(data.get("credits_charged"), int):
            stop("submit %s unexpected response: %s" % (job["shot_id"], r.text[:500]), receipts)
        if data["credits_charged"] != job["quote"]["amount"]:
            stop("submit %s charged %s != quoted %s" % (job["shot_id"], data["credits_charged"], job["quote"]["amount"]), receipts)
        receipts["jobs"].append({"shot_id": job["shot_id"], "job_id": data["id"],
                                 "credits_charged": data["credits_charged"],
                                 "quoted": job["quote"]["amount"]})
        print("submitted", job["shot_id"], data["id"], "charged", data["credits_charged"])
        time.sleep(1)

    receipts["total_charged"] = sum(j["credits_charged"] for j in receipts["jobs"])
    RECEIPTS.write_text(json.dumps(receipts, indent=2))
    print("total charged:", receipts["total_charged"], "cap: 1248")
    if receipts["total_charged"] > 1248:
        print("WARNING: charge exceeds cap - report, do not continue")


if __name__ == "__main__":
    main()
