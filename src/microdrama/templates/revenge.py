"""Revenge & Stolen Identity microdrama template."""

from ..models import GenreTemplate, Character

REVENGE_TEMPLATE = GenreTemplate(
    id="revenge_comeback",
    name="Revenge of the Stolen Identity",
    genre="Suspense",
    vibe="Cold, glamorous, calculated, venomous",
    description=(
        "Presumed dead after a devastating betrayal, the ruined protagonist returns years later "
        "under a dangerous alter-ego. Infiltrating the inner circle of those who ruined her life, "
        "she dismantles their empire piece by piece."
    ),
    signature_hook="A masked woman in a blood-red gown steps out of a rain-drenched limousine, stepping on a wedding invitation.",
    climax_tropes=[
        "A whispered private secret that only the dead person could possibly know",
        "A sudden projection onto the grand ballroom screen revealing the affair or embezzlement",
        "A champagne glass shattered on marble during a toast",
        "The rival gasps while clutching her throat as she realizes her necklace was stolen"
    ],
    cliffhanger_formulas=[
        "She leans in close to the trembling groom, removing her veil: 'Did you really think fire was enough to kill me?'",
        "The audio system echoes with the secret confession recorded minutes before the fatal car crash",
        "Police sirens wail outside as the protagonist holds up the missing ledger, smiling serenely"
    ],
    default_cast=[
        Character(
            name="Scarlett",
            role="Protagonist",
            look="Crimson satin gown, dark crimson lipstick, piercing green eyes, diamond choker hiding a delicate scar",
            voice="Velvety, icy, seductive, razor-sharp"
        ),
        Character(
            name="Damian",
            role="Antagonist",
            look="Tailored black designer suit, gold watch, guilty nervous sweat at the collar",
            voice="Stammering, defensive, desperate"
        ),
        Character(
            name="Chloe",
            role="Rival",
            look="Pristine white lace bridal gown, flawless makeup masking vicious malice",
            voice="High-pitched, hysterical, spiteful"
        )
    ],
    pacing_rules=(
        "0-3s: Striking, unforgettable visual arrival of the avenger. "
        "15s: Infiltration and close encounter with the betrayers. "
        "30-40s: An acoustic or visual trap is sprung—the secret begins to leak. "
        "50-60s: Identity unmasking or definitive trap sprung on the cliffhanger."
    ),
    suggested_shots=8,
    seconds_per_shot=8
)
