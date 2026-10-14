"""Psychological Suspense & Time-Loop microdrama template."""

from ..models import GenreTemplate, Character

THRILLER_LOOP_TEMPLATE = GenreTemplate(
    id="thriller_loop",
    name="The Doppelgänger Loop (Do Not Open The Door)",
    genre="Suspense",
    vibe="Paranoid, chilling, claustrophobic, mind-bending psychological dread",
    description=(
        "A psychological thriller masterclass: an unsuspecting protagonist finds an impossible note "
        "written in their own frantic handwriting warning them against a mundane action ('DO NOT OPEN THE DOOR'). "
        "A sudden violent interruption forces their hand, unraveling a fatal time-loop where the predator "
        "is an older, colder version of themselves."
    ),
    signature_hook="A trembling hand unfolds an envelope to reveal blood-red handwriting: 'DO NOT OPEN THE DOOR. The intruder will kill you. - YOU.'",
    climax_tropes=[
        "A thunderous, rhythmic banging that rattles the deadbolt off its hinges",
        "A casual phone call from a loved one contradicting the deadly warning",
        "Arming oneself with a blunt object, creeping down a silent hallway only to find the door swung wide open",
        "A sudden blow to the base of the skull followed by disembodied out-of-body horror"
    ],
    cliffhanger_formulas=[
        "From the closet shadows steps an older version of the protagonist, wiping the iron weapon: 'I told you not to open the door.'",
        "Floating near the ceiling, the protagonist watches her own motionless body as the killer drops the identical note onto her chest.",
        "The killer turns around and locks the deadbolt, their eyes hollow with cold calculation: 'Now the cycle begins again.'"
    ],
    default_cast=[
        Character(
            name="Maya",
            role="Protagonist",
            look="Oversized navy knit sweater, pale skin, frantic wide dark eyes, messy ponytail",
            voice="Trembling, breathless, rising panic"
        ),
        Character(
            name="Future Maya",
            role="Antagonist",
            look="Identical facial features but hardened, cold calculating stare, black trench coat, iron doorstop in gloved hand",
            voice="Chilling, deadened whisper, precise"
        ),
        Character(
            name="Mother",
            role="Ally",
            look="Offscreen voice through speakerphone, cheerful and oblivious",
            voice="Bright, breezy, casual grocery delivery reminder"
        )
    ],
    pacing_rules=(
        "0-3s: Immediate dread: the handwriting and the lethal warning. "
        "15s: Normalcy shattered by violent knocking and conflicting instructions. "
        "30-40s: Arming and creeping down the hall to the open door; sudden blindsided strike. "
        "50-60s: Out-of-body twist revealing the killer's face as the protagonist's future self."
    ),
    suggested_shots=10,
    seconds_per_shot=8
)
