import os, json

class VideoBackend:
    name = "abstract"
    def generate_shot(self, shot, brief, out_dir):
        raise NotImplementedError
    def assemble(self, shot_paths, out_path):
        raise NotImplementedError

class DryRunBackend(VideoBackend):
    name = "dry_run"
    def generate_shot(self, shot, brief, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        p = os.path.join(out_dir, f"shot_{shot.idx:02d}.json")
        refs = {c.name: c.ref_image for c in brief.characters if c.name in shot.characters}
        json.dump({"visual": shot.visual, "camera": shot.camera, "dur_s": shot.dur_s, "refs": refs,
                   "dialogue": shot.dialogue, "speaker": shot.speaker}, open(p, "w"), indent=1)
        return p
    def assemble(self, shot_paths, out_path):
        json.dump(shot_paths, open(out_path, "w"), indent=1)
        return out_path


class LockedError(RuntimeError):
    pass

class MagicHourBackend(VideoBackend):
    name = "magic_hour"

    def __init__(self, api_key=None, unlocked=False, governor=None):
        if not unlocked:
            raise LockedError("Magic Hour backend is locked. It runs only after the owner unpauses the step and supplies the key from the credit-holding account.")
        if not api_key:
            raise LockedError("no Magic Hour API key supplied")
        self.api_key = api_key
        self.governor = governor

    def generate_shot(self, shot, brief, out_dir):
        raise NotImplementedError("endpoint wiring waits for probes P-1 and P-2 (reference count and name binding)")

    def assemble(self, shot_paths, out_path):
        raise NotImplementedError("assembly waits for the first rendered shots")
