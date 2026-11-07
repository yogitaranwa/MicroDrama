"""Process gates for production runs.

These gates exist because past episode attempts failed on process, not on
model quality:

1. Reference stills were not generated and locked BEFORE moving shots, so
   wardrobe and appearance drifted between shots and had to be repaired
   after the fact.  -> still_first.require_still_lock()
2. Long, complex episodes were attempted before proving one short connected
   scene.  -> scene_proof.require_proof()
3. A draft was handed over with wardrobe changes, long silent stretches and
   unfinished lip-sync, without a continuous playback + listening review.
   -> review.require_signoff()

Every gate fails closed: no lock/signoff file, no render, no delivery.
Set FORGE_GATES=0 to bypass in emergencies (a warning is printed).
"""
from forge.gates.common import GateLocked
from forge.gates.still_first import lock_stills, require_still_lock
from forge.gates.scene_proof import record_proof, signoff_proof, require_proof
from forge.gates.review import review_episode, signoff, require_signoff
from forge.gates.fullspeed import record_fullspeed_review, require_fullspeed_review
from forge.gates.continuity import frame_features, drift_score
from forge.gates.enforce import enforce_render_allowed
from forge.gates.angle_stills import (angle_class, required_still_labels, angle_coverage,
                                      require_angle_stills, cross_angle_flags)
from forge.gates.proof_checklist import (ITEMS, start_checklist, check_item,
                                         checklist_status, require_proof_checklist)

__all__ = [
    "GateLocked",
    "lock_stills", "require_still_lock",
    "record_proof", "signoff_proof", "require_proof",
    "review_episode", "signoff", "require_signoff",
    "record_fullspeed_review", "require_fullspeed_review",
    "frame_features", "drift_score",
    "enforce_render_allowed",
    "angle_class", "required_still_labels", "angle_coverage", "require_angle_stills",
    "cross_angle_flags",
    "ITEMS", "start_checklist", "check_item", "checklist_status", "require_proof_checklist",
]
