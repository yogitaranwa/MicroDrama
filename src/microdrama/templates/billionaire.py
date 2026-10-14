"""Hidden Billionaire microdrama template."""

from ..models import GenreTemplate, Character

BILLIONAIRE_TEMPLATE = GenreTemplate(
    id="hidden_billionaire",
    name="The Hidden Billionaire (Secret Tycoon)",
    genre="Family drama",
    vibe="Extravagant, humiliating, vengeful, exhilaratingly cathartic",
    description=(
        "The ultimate microdrama archetype: an unassuming, modest protagonist is mocked "
        "and publicly degraded by snobbish in-laws or corrupt executives, unaware that the protagonist "
        "is actually the reclusive heir to a trillion-dollar empire about to reclaim his throne."
    ),
    signature_hook="A glass of champagne is violently splashed into the protagonist's face during an opulent gala as the antagonist sneers.",
    climax_tropes=[
        "Security is ordered to physically throw the protagonist out into the rain",
        "A black titanium centurion card is slammed onto the marble counter",
        "The billionaire patriarch arrives with an armed security detail and freezes in shock",
        "The rival arrogantly mocks: 'You couldn't afford this napkin if you worked ten lifetimes!'"
    ],
    cliffhanger_formulas=[
        "The city's most feared tycoon pushes past security, drops to one knee, and proclaims: 'Welcome home, Chairman.'",
        "The rival's phone buzzes with catastrophic alerts: 'Sir! Every creditor has pulled our funding! Who did you offend?!'",
        "The protagonist wipes the wine off his cheek, smiles icily, and whispers: 'Your company was bought five minutes ago.'"
    ],
    default_cast=[
        Character(
            name="Leo",
            role="Protagonist",
            look="Understated charcoal grey turtleneck, observant sharp eyes, hidden aura of supreme authority",
            voice="Deep, measured, calm even under extreme provocation"
        ),
        Character(
            name="Richard",
            role="Antagonist",
            look="Flashy tuxedo, diamond lapel pin, sneering expression, slicked back hair",
            voice="Arrogant, mocking, piercing laughter"
        ),
        Character(
            name="Evelyn",
            role="Ally",
            look="Elegant emerald silk evening gown, conflicted expression, aristocratic posture",
            voice="Tense, urgent, breathy"
        )
    ],
    pacing_rules=(
        "0-3s: Immediate visceral humiliation or physical disrespect. "
        "15s: Escalation with ruthless verbal mockery and threats of ruined lives. "
        "30-40s: An undeniable symbol of supreme power enters (phone call, elder billionaire, black card). "
        "50-60s: Jaw-dropping cliffhanger reveal that flips the power dynamic completely."
    ),
    suggested_shots=8,
    seconds_per_shot=8
)
