"""Automatic shot-boundary QA with PySceneDetect (BSD-3) + OpenTimelineIO (Apache-2.0) timeline export."""
import opentimelineio as otio
from scenedetect import detect, ContentDetector

def cuts(video, threshold=27.0):
    """Detected scenes as (start_s, end_s); n scenes means n-1 hard cuts."""
    return [(s.seconds, e.seconds) for s, e in detect(video, ContentDetector(threshold=threshold))]

def unexpected_cuts(video, expected_shots):
    """A single generated shot should contain no hard cut; flag if it does."""
    found = cuts(video)
    return {"expected": expected_shots, "found": len(found), "ok": len(found) <= expected_shots}

def write_timeline(shots, out_path, fps=30):
    """shots: [(name, seconds)] -> .otio file usable by other editors."""
    tl = otio.schema.Timeline(name="episode")
    tr = otio.schema.Track(name="V1")
    for name, secs in shots:
        tr.append(otio.schema.Clip(name=name, source_range=otio.opentime.TimeRange(
            otio.opentime.RationalTime(0, fps), otio.opentime.RationalTime(secs * fps, fps))))
    tl.tracks.append(tr)
    otio.adapters.write_to_file(tl, out_path)
    return out_path
