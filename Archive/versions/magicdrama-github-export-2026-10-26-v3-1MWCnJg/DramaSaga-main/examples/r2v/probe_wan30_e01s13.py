"""ONE approved Wan 3.0 probe, e01s13, 720p 4s, cap 384 credits.
Authority: user WhatsApp 2026-10-26 07:34:56 IST "I approve you / Just do the check"
([private-record-reference])
replying to main's Wan-actual-FPS check message; main delegated one probe under
384 cap, no retries, no broader production. Stop-on-error is literal.
"""
import hashlib, json, sys, time
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from magicdrama.audiofirst.magichour_catalog import quote_credits, validate_request_shape

API = "https://api.magichour.ai"
ROOT = Path(__file__).resolve().parent
KEY_FILE = Path("/home/sandbox/.vault/magic-hour-api-key-70da61/password")
RECEIPTS = ROOT / "probe-2026-10-26" / "receipts-wan30-e01s13.json"
OUT = Path("/tmp/probe-out/wan30-e01s13.mp4")

ASSETS = [
    ("/downloads/ref-harry-front-close.png", "harry_front_close", "image"),
    ("/downloads/ref-harry-speaking-profile.png", "harry_speaking_profile", "image"),
    ("/tmp/rev/e01-l12-harry.mp3", "audio_e01s13", "audio"),
]
BANK_HASH = {
    "harry_front_close": "9a813a6c92e65f4d4b11c856609aa563842ac046bcd7f593c9069df4a2aafb46",
    "harry_speaking_profile": "adead16dd28e7aa821ed3e98f5fb20553343f1c53bd3711250ee16d7594ae909",
}
PROMPT = ("Static locked camera, no movement, medium close on Harry on a candlelit Yule Ball "
          "dance floor. Harry looks down at glowing waltz-grid lines on the floor, recognizes "
          "the pattern, and deliberately breaks his dance step wrong on purpose; controlled, "
          "cold decision on his face. Keep @harry_front_close and @harry_speaking_profile "
          "identical to the references in face, hair, glasses, wardrobe and proportions. "
          "Spoken dialogue and delivery follow @audio_e01s13.")


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
    receipts = {"probe": "wan30-e01s13", "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "uploads": [], "job": None}

    for path, name, _ in ASSETS:
        if name in BANK_HASH and sha256(path) != BANK_HASH[name]:
            stop("hash mismatch for " + name, receipts)

    quote = quote_credits("wan-3.0", 4, "720p")
    assert quote == 384, quote
    validate_request_shape("wan-3.0", 4, "720p", "9:16", len(ASSETS), audio=True)

    paths = {}
    for path, name, typ in ASSETS:
        ext = path.rsplit(".", 1)[1].lower()
        r = requests.post(API + "/v1/files/upload-urls", headers=H,
                          json={"items": [{"extension": ext, "type": typ}]}, timeout=60)
        if r.status_code != 200:
            stop("upload-urls %s HTTP %s: %s" % (name, r.status_code, r.text[:500]), receipts)
        items = r.json().get("items")
        if not isinstance(items, list) or len(items) != 1:
            stop("upload-urls %s unexpected shape: %s" % (name, r.text[:500]), receipts)
        item = items[0]
        up = requests.put(item["upload_url"], data=Path(path).read_bytes(), timeout=120)
        if up.status_code not in (200, 201, 204):
            stop("PUT %s HTTP %s" % (name, up.status_code), receipts)
        paths[name] = item["file_path"]
        receipts["uploads"].append({"name": name, "sha256": sha256(path), "file_path": item["file_path"]})
        print("uploaded", name)

    body = {
        "name": "e01s13-wan30-probe",
        "model": "wan-3.0",
        "end_seconds": 4,
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "audio": True,
        "references": [{"file_path": paths[n], "name": n} for _, n, _ in ASSETS],
        "style": {"prompt": PROMPT},
    }
    r = requests.post(API + "/v1/text-to-video", headers=H, json=body, timeout=60)
    if r.status_code != 200:
        stop("submit HTTP %s: %s" % (r.status_code, r.text[:800]), receipts)
    data = r.json()
    if not data.get("id") or data.get("credits_charged") != 384:
        stop("submit unexpected response: %s" % r.text[:800], receipts)
    receipts["job"] = {"id": data["id"], "credits_charged": data["credits_charged"]}
    RECEIPTS.write_text(json.dumps(receipts, indent=2))
    print("submitted", data["id"], "charged", data["credits_charged"])

    job_id = data["id"]
    deadline = time.time() + 480
    while time.time() < deadline:
        time.sleep(15)
        s = requests.get(API + "/v1/video-projects/" + job_id, headers=H, timeout=60)
        if s.status_code != 200:
            stop("status HTTP %s: %s" % (s.status_code, s.text[:500]), receipts)
        st = s.json()
        status = st.get("status")
        print("status", status)
        if status == "complete":
            dl = (st.get("downloads") or [{}])[0].get("url")
            if not dl:
                stop("complete but no download url: %s" % s.text[:500], receipts)
            OUT.parent.mkdir(parents=True, exist_ok=True)
            vid = requests.get(dl, timeout=180)
            if vid.status_code != 200:
                stop("download HTTP %s" % vid.status_code, receipts)
            OUT.write_bytes(vid.content)
            receipts["output"] = str(OUT)
            receipts["download_url"] = dl
            RECEIPTS.write_text(json.dumps(receipts, indent=2))
            print("downloaded", OUT, len(vid.content), "bytes")
            return
        if status in ("error", "canceled"):
            stop("job %s: %s" % (status, s.text[:500]), receipts)
    stop("timeout waiting for completion", receipts)


if __name__ == "__main__":
    main()
