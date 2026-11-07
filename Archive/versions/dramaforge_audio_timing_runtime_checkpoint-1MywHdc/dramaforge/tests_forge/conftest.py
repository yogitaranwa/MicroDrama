"""Shared fixtures for the forge suite (m19).

m17's lip-sync tests read /tmp/shots/multiface.mp4 but never created it -
they only passed where a stale file already existed. Generate a real,
tiny ffmpeg-encoded clip once per session so those tests exercise the
actual code path everywhere."""
import os
import subprocess

import pytest


@pytest.fixture(scope="session", autouse=True)
def multiface_fixture_clip():
    path = "/tmp/shots/multiface.mp4"
    if not os.path.isfile(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             "testsrc=duration=2:size=320x240:rate=10",
             "-pix_fmt", "yuv420p", path], check=True)
    return path
