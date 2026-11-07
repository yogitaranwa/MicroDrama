"""Single chokepoint consulted before any paid video render."""
from forge.gates.common import GateLocked, bypassed
from forge.gates.still_first import require_still_lock
from forge.gates.scene_proof import require_proof


def enforce_render_allowed(project_dir, mode: str) -> None:
    """mode: 'proof' or 'episode'.

    'proof'   - the one short connected proof scene; needs locked stills.
    'episode' - anything beyond the proof scene; needs locked stills AND a
                signed-off proof scene.
    """
    if bypassed():
        return
    require_still_lock(project_dir)
    if mode == "episode":
        require_proof(project_dir)
    elif mode != "proof":
        raise GateLocked(f"unknown render mode {mode!r}; expected 'proof' or 'episode'")
