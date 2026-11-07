"""PySceneDetect (BSD-3) QA: every generated shot clip must be one continuous take (no accidental cuts/morphs)."""
from scenedetect import detect, ContentDetector

def scenes(path: str, threshold: float = 27.0):
    return [(a.get_seconds(), b.get_seconds()) for a, b in detect(path, ContentDetector(threshold=threshold))]

def single_take(path: str, threshold: float = 27.0) -> bool:
    return len(scenes(path, threshold)) <= 1
