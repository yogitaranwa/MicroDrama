"""Build the bounded contiguous R2V probe manifest. No network, no spend.

Probe scope (user approval request 2026-10-26): UP TO 1,104 existing Magic
Hour credits, 23s across exactly 4 contiguous E01 shots (e01s07..e01s10) on
minimax-h3 @720p, stop after 4 jobs, no automatic rerolls/upgrades/resubmits,
full-speed human watch/listen review before any further spend.

This manifest is PREPARED_NOT_SUBMITTED. Upload file_paths are placeholders;
the live upload phase replaces them only after manifest approval.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from magicdrama.audiofirst import r2v

ROOT = Path(__file__).resolve().parent
MODEL = "minimax-h3"
RESOLUTION = "720p"
ASPECT = "9:16"

# Contiguous shot ids and the dialogue line attached to each (speaker marked
# visible where the speaker is on screen; s08/s09 speakers are offscreen).
PROBE_SHOTS = [
    ("e01s07", "e01s07l1-then-count-faster.wav", "audio_e01s07"),
    ("e01s08", "e01s08l1-show-off.wav", "audio_e01s08"),
    ("e01s09", "e01s09l1-efficient.wav", "audio_e01s09"),
    ("e01s10", "e01s10l1-i-definitely-planned-that.wav", "audio_e01s10"),
]

CUT_STATES = [
    {"cut": "e01s07->e01s08", "end": "Draconia grinning mid-dance, close; both dancing on the corrected beat",
     "start": "wide of the same floor position, both dancing"},
    {"cut": "e01s08->e01s09", "end": "Harry's right wrist wrapped by a silver string, two cut strings falling",
     "start": "Draconia at Harry's wrapped wrist; the wrap must be visible"},
    {"cut": "e01s09->e01s10", "end": "Draconia pulling Harry upright, both back in dance hold",
     "start": "wide, both upright in dance hold"},
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    bank = json.loads((ROOT / "harry-draconia-reference-bank.json").read_text())
    episode = json.loads((ROOT / "e01-shots.json").read_text())
    shots = {s["id"]: s for s in episode["shots"]}
    uploads = {r["id"]: {"file_path": "api-assets/PENDING_UPLOAD/" + r["id"] + ".png",
                         "sha256": r["sha256"]}
               for r in bank["references"]}

    jobs = []
    total = 0
    for shot_id, wav, audio_name in PROBE_SHOTS:
        shot = shots[shot_id]
        image_refs = r2v.select_shot_references(shot, bank, uploads)
        wav_path = ROOT / "probe-2026-10-26" / "audio" / wav
        audio_ref = {"id": audio_name, "name": r2v.validate_reference_name(audio_name),
                     "file_path": "api-assets/PENDING_UPLOAD/" + wav,
                     "kind": "audio", "sha256": sha256(wav_path)}
        refs = image_refs + [audio_ref]
        request = r2v.build_r2v_request(shot, refs, MODEL, RESOLUTION, ASPECT, audio=True)
        total += request["quote"]["amount"]
        jobs.append({
            "id": "probe-r2v-" + shot_id,
            "shot_id": shot_id,
            "provider": "magichour",
            "request": {"method": request["method"], "endpoint": request["endpoint"],
                        "body": request["body"]},
            "quote": request["quote"],
            "reference_binding": {
                "images": [{"id": r["id"], "name": r["name"]} for r in image_refs],
                "audio": {"name": audio_ref["name"], "source_wav": wav,
                          "sha256": audio_ref["sha256"],
                          "sliced_from": "accepted E01 production-package mp3 per e01-dialogue-lines.json"}},
        })

    manifest = {
        "id": "probe-r2v-e01s07-s10-2026-10-26",
        "status": "prepared_not_submitted",
        "created": "2026-10-26",
        "model": MODEL, "resolution": RESOLUTION, "aspect_ratio": ASPECT,
        "catalog_verified_on": r2v.VERIFIED_ON,
        "jobs": jobs,
        "budget": {"cap_credits": 1104, "quoted_total_credits": total,
                   "scope": "exactly these 4 jobs; stop after 4; no rerolls, no model upgrades, no auto-resubmit on failure; on ANY validation error or unknown API outcome: STOP immediately, no fallback, no auto-retry, report the raw outcome"},
        "contiguity": {"sequence": [s for s, _, _ in PROBE_SHOTS], "declared_cut_states": CUT_STATES},
        "review_required_before_further_spend": [
            "full-speed human watch+listen of actual API output",
            "audio-content identification (reference words / other speech / ambience / silence)",
            "lip-motion plausibility against heard words (human judgment; mouth-tracker is a screen only)",
            "identity vs bank PNGs per visible character per shot",
            "action vs script beat per shot",
            "emotional delivery vs E01 detailing addendum lines 6-9",
            "cut-by-cut end/start state match per declared_cut_states"],
        "documented_unknowns": [
            "audio-reference semantics undocumented (soundtrack vs voice direction vs exact waveform)",
            "whether audio references count toward the 10-reference cap",
            "per-reference size/format limits",
            "audio:true toggle vs audio-reference interaction; audio:true is an EXPERIMENTAL choice so the job can carry an audio track at all - whether the model uses the reference is exactly what the probe measures, no quality claim is made or implied"],
        "destination": {"drive_folder_id": "1ImqQb81qldPfKrdsWzacYgnqtz0734Tn",
                        "note": "probe outputs and review notes land in the dramasaga folder"},
    }
    manifest["manifest_sha256"] = r2v.signature(manifest)
    out = ROOT / "probe-2026-10-26" / "probe-manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print("jobs:", len(jobs), "total quote:", total, "cap: 1104", "OK" if total <= 1104 else "OVER CAP")
    for j in jobs:
        b = j["request"]["body"]
        print(" ", j["shot_id"], b["end_seconds"], "s refs:", len(b["references"]),
              "quote:", j["quote"]["amount"])
    print("manifest_sha256:", manifest["manifest_sha256"][:16], "->", out)


if __name__ == "__main__":
    main()
