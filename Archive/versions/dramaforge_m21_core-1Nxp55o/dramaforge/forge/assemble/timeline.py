"""Edit decision list via OpenTimelineIO (Apache-2.0): one source of truth for shots, dialogue and music.
Exports .otio (and FCP7 XML/CMX EDL via OTIO adapters) so the cut opens in Resolve/Premiere; MoviePy renders from it."""
from typing import Dict, List
import opentimelineio as otio

def build_timeline(shots: List[Dict], fps: int = 24, name: str = "episode") -> otio.schema.Timeline:
    """shots: [{n, clip, seconds, audio (optional wav path), lines:[{speaker,text}]}]"""
    tl = otio.schema.Timeline(name=name)
    video = otio.schema.Track(name="video", kind=otio.schema.TrackKind.Video)
    dialog = otio.schema.Track(name="dialogue", kind=otio.schema.TrackKind.Audio)
    for s in shots:
        dur = otio.opentime.RationalTime(round(s["seconds"] * fps), fps)
        rng = otio.opentime.TimeRange(otio.opentime.RationalTime(0, fps), dur)
        vc = otio.schema.Clip(name=f"shot{s['n']:02d}", source_range=rng,
                              media_reference=otio.schema.ExternalReference(target_url=s["clip"]))
        vc.metadata["forge"] = {"lines": s.get("lines", [])}
        video.append(vc)
        if s.get("audio"):
            ac = otio.schema.Clip(name=f"voice{s['n']:02d}", source_range=rng,
                                  media_reference=otio.schema.ExternalReference(target_url=s["audio"]))
            dialog.append(ac)
        else:
            dialog.append(otio.schema.Gap(source_range=rng))
    tl.tracks.extend([video, dialog])
    return tl

def export(tl, path: str):
    otio.adapters.write_to_file(tl, path)
    return path

def durations(path: str) -> List[float]:
    tl = otio.adapters.read_from_file(path)
    return [c.duration().to_seconds() for c in tl.video_tracks()[0]]
