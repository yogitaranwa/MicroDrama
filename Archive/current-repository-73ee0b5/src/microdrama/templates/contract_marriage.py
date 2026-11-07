"""Contract Marriage microdrama template."""

from ..models import GenreTemplate, Character

CONTRACT_MARRIAGE_TEMPLATE = GenreTemplate(
    id="contract_marriage",
    name="The Cold CEO's Contract Bride",
    genre="Romance",
    vibe="Sultry, intensely jealous, possessive, emotional rollercoaster",
    description=(
        "Bound by a strict 1-year contract with a ruthless corporate heir who swore never to love her, "
        "the heroine signs the divorce papers—only for the CEO to discover her secret value, an impending danger, "
        "or an unexpected child, unleashing his fierce possessiveness."
    ),
    signature_hook="Signed divorce papers are slammed against the mahogany desk, followed by a tear falling onto the ink.",
    climax_tropes=[
        "The CEO pins the heroine against the floor-to-ceiling glass window of his skyscraper office",
        "A malicious mother-in-law or spoiled heiress bursts in with fabricated scandal photos",
        "The heroine attempts to walk out into the pouring rain with a single suitcase",
        "The CEO rips up the divorce agreement in a blind rage of jealousy"
    ],
    cliffhanger_formulas=[
        "He grabs her wrist, pulling her flushed face inches from his: 'You can leave this house... when you pay me back with an heir.'",
        "The medical report slips from her trembling fingers: 'Positive - 6 weeks'. The CEO's eyes widen.",
        "A rival billionaire steps out of a sports car in the rain, offering his hand: 'Ready to leave him for good, darling?'"
    ],
    default_cast=[
        Character(
            name="Seraphina",
            role="Protagonist",
            look="Simple cream cashmere sweater, delicate posture, sorrowful yet fierce hazel eyes",
            voice="Soft-spoken but resolute, stubborn undertone"
        ),
        Character(
            name="Alexander",
            role="Deuteragonist",
            look="Immaculate bespoke dark navy pinstripe suit, broad shoulders, piercing storm-grey gaze",
            voice="Low, commanding, raspy with barely contained possessiveness"
        ),
        Character(
            name="Victoria",
            role="Rival",
            look="Haute couture pearl-embroidered blazer, sharp cheekbones, cruel mocking smile",
            voice="Patronizing, sweet like poison"
        )
    ],
    pacing_rules=(
        "0-3s: Emotional ultimatum or physical gesture of breaking the contract. "
        "15s: Intimate confrontation and forced proximity. "
        "30-40s: External threat or third-party interference sparks intense jealousy. "
        "50-60s: Shocking physical or emotional cliffhanger boundary crossed."
    ),
    suggested_shots=8,
    seconds_per_shot=8
)
