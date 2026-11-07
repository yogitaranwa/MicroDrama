"""Single chokepoint consulted before any paid video render."""
import json
import os
from forge.gates.common import GateLocked, bypassed, state_dir
from forge.gates.still_first import require_still_lock
from forge.gates.scene_proof import require_proof
from forge.gates.angle_stills import require_angle_stills
from forge.gates.proof_checklist import CHECKLIST_NAME, require_proof_checklist

# Where the script stage writes the shot/reverse-shot plan (m11). When this
# file exists, every render must also pass the angle-still gate; when it does
# not, behaviour is exactly the pre-m11 flow.
DEFAULT_PLAN = os.path.join("out", "e01_plan.json")


def _load_plan(project_dir):
    path = os.path.join(str(project_dir), DEFAULT_PLAN)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as fh:
            plan = json.load(fh)
        return plan if isinstance(plan, list) and plan else None
    except (OSError, ValueError):
        return None


def enforce_render_allowed(project_dir, mode: str, planned_shots=None) -> None:
    """mode: 'proof' or 'episode'.

    'proof'   - the one short connected proof scene; needs locked stills.
    'episode' - anything beyond the proof scene; needs locked stills AND a
                signed-off proof scene.

    Additive m11 wiring, both opt-in, old behaviour unchanged without them:
    - planned_shots (or the plan file written by the script stage): every
      camera angle in the plan must be covered by a locked still.
    - a started proof checklist (.forge/proof_checklist.json) must be fully
      checked before episode renders.
    """
    if bypassed():
        return
    require_still_lock(project_dir)
    if planned_shots is None:
        planned_shots = _load_plan(project_dir)
    if planned_shots:
        require_angle_stills(project_dir, planned_shots)
    if mode == "episode":
        require_proof(project_dir)
        if (state_dir(project_dir) / CHECKLIST_NAME).exists():
            require_proof_checklist(project_dir)
    elif mode != "proof":
        raise GateLocked(f"unknown render mode {mode!r}; expected 'proof' or 'episode'")
