"""Execute the approved 4-shot R2V probe. User approved up to 1,104 credits
(2026-10-26 02:23 IST, WhatsApp "yes use" to the exact scope question).

Hard rules from approval + main: exactly these 4 jobs, stop after 4, no
rerolls, no upgrades, NO auto-resubmit; on ANY validation error or unknown
API outcome: STOP immediately and report the raw outcome.
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
KEY_FILE = None  # RETIRED 2026-10-26: un-gated paid probe path; the vault path is removed from source. Paid generation runs ONLY through production_runner.py stages (approval-ref + cap gates).
RECEIPTS = ROOT / "probe-2026-10-26" / "receipts.json"

LOCAL = {
    "ref-draconia-front-close.png": "/downloads/ref-draconia-front-close.png",
    "ref-draconia-fullbody.png": "/downloads/ref-draconia-fullbody.png",
    "ref-harry-fullbody.png": "/downloads/ref-harry-fullbody.png",
    "ref-yule-ball-location.png": "/downloads/ref-yule-ball-location.png",
    "e01s07l1-then-count-faster.wav": str(ROOT / "probe-2026-10-26/audio/e01s07l1-then-count-faster.wav"),
    "e01s08l1-show-off.wav": str(ROOT / "probe-2026-10-26/audio/e01s08l1-show-off.wav"),
    "e01s09l1-efficient.wav": str(ROOT / "probe-2026-10-26/audio/e01s09l1-efficient.wav"),
    "e01s10l1-i-definitely-planned-that.wav": str(ROOT / "probe-2026-10-26/audio/e01s10l1-i-definitely-planned-that.wav"),
}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stop(msg, receipts):
    receipts["stopped"] = msg
    RECEIPTS.write_text(json.dumps(receipts, indent=2))
    print("STOP:", msg)
    sys.exit(2)


def main():
    raise SystemExit("RETIRED: this un-gated paid probe script is preserved for history only. "
                     "Paid generation runs ONLY through production_runner.py stages with fresh approval-ref + cap.")
    token = KEY_FILE.read_text().strip()
    H = {"Authorization": "Bearer " + token}
    manifest = json.loads((ROOT / "probe-2026-10-26/probe-manifest.json").read_text())
    bank = json.loads((ROOT / "harry-draconia-reference-bank.json").read_text())
    receipts = {"manifest_id": manifest["id"], "manifest_sha256": manifest["manifest_sha256"],
                "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "uploads": [], "jobs": []}

    # 1) verify local image hashes against the bank before anything leaves
    bank_hash = {r["id"]: r["sha256"] for r in bank["references"]}
    for name, path in LOCAL.items():
        h = sha256(path)
        rid = name[:-4]
        if rid in bank_hash and h != bank_hash[rid]:
            stop("hash mismatch for %s vs bank" % name, receipts)

    # 2) upload URLs
    items = [{"extension": n.rsplit(".", 1)[1],
              "type": "audio" if n.endswith(".wav") else "image"} for n in LOCAL]
    r = requests.post(API + "/v1/files/upload-urls", headers=H,
                      json={"items": items}, timeout=60)
    if r.status_code != 200:
        stop("upload-urls HTTP %s: %s" % (r.status_code, r.text[:500]), receipts)
    returned = r.json().get("items") or r.json()
    if not isinstance(returned, list) or len(returned) != len(items):
        stop("upload-urls unexpected shape: %s" % r.text[:500], receipts)
    path_for = {}
    for (name, path), item in zip(sorted(LOCAL.items()), returned):
        up = requests.put(item["upload_url"], data=Path(path).read_bytes(), timeout=120)
        if up.status_code not in (200, 201, 204):
            stop("PUT %s HTTP %s" % (name, up.status_code), receipts)
        path_for["api-assets/PENDING_UPLOAD/" + name] = item["file_path"]
        receipts["uploads"].append({"name": name, "sha256": sha256(path),
                                    "file_path": item["file_path"]})
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
        receipts["jobs"].append({"shot_id": job["shot_id"], "job_id": data["id"],
                                 "credits_charged": data["credits_charged"],
                                 "quoted": job["quote"]["amount"]})
        print("submitted", job["shot_id"], data["id"], "charged", data["credits_charged"])
        time.sleep(1)

    receipts["total_charged"] = sum(j["credits_charged"] for j in receipts["jobs"])
    RECEIPTS.write_text(json.dumps(receipts, indent=2))
    print("total charged:", receipts["total_charged"], "cap: 1104")
    if receipts["total_charged"] > 1104:
        print("WARNING: charge exceeds cap - report, do not continue")


if __name__ == "__main__":
    main()
