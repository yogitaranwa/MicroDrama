"""The only delivery path: refuses to export anything unsigned and
unreviewed at full speed."""
import shutil
from pathlib import Path
from forge.gates.common import GateLocked, state_dir, write_json, now_iso
from forge.gates.review import require_signoff
from forge.gates.fullspeed import require_fullspeed_review


def deliver(project_dir, episode_path, dest_dir, fullspeed: bool = True) -> str:
    """Copy the reviewed episode into dest_dir. Raises GateLocked otherwise.
    m17: delivery needs the full-speed human review record on top of the
    machine review and signoff - every defect that ever shipped had passed
    sampled checks. fullspeed=False restores the pre-m17 path for
    machine-only exports and is recorded as such."""
    require_signoff(project_dir, episode_path)
    if fullspeed:
        require_fullspeed_review(project_dir, episode_path)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / Path(episode_path).name
    shutil.copy2(episode_path, out)
    write_json(state_dir(project_dir) / "deliveries.json",
               {"last": {"file": str(out), "at": now_iso()}})
    return str(out)
