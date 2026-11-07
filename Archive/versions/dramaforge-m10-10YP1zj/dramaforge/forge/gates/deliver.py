"""The only delivery path: refuses to export anything unsigned."""
import shutil
from pathlib import Path
from forge.gates.common import GateLocked, state_dir, write_json, now_iso
from forge.gates.review import require_signoff


def deliver(project_dir, episode_path, dest_dir) -> str:
    """Copy the signed-off episode into dest_dir. Raises GateLocked otherwise."""
    require_signoff(project_dir, episode_path)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / Path(episode_path).name
    shutil.copy2(episode_path, out)
    write_json(state_dir(project_dir) / "deliveries.json",
               {"last": {"file": str(out), "at": now_iso()}})
    return str(out)
