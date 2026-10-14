"""Alpha / Mafia Forbidden Romance microdrama template."""

from ..models import GenreTemplate, Character

WEREWOLF_MAFIA_TEMPLATE = GenreTemplate(
    id="werewolf_mafia",
    name="The Alpha's Claim (Mafia Don's Obsession)",
    genre="Romance",
    vibe="Dangerous, primal, brooding, dark romance, breathless tension",
    description=(
        "A fierce heroine on the run from her cruel family or rival faction is cornered in the shadows "
        "by the city's most ruthless syndicate head / Alpha. Instead of killing her, he senses her scent "
        "or hidden legacy and declares total ownership."
    ),
    signature_hook="A gun clicks against the heroine's collarbone in a neon-lit alley; a massive shadowed figure grabs the barrel with bare hands.",
    climax_tropes=[
        "The enemy henchmen freeze as amber eyes flash in the dark",
        "The Don blocks an attack with his bare back, shielding the heroine",
        "A blood oath or bite mark glowing under moonlight",
        "The heroine discovers she holds the key to the entire syndicate's bloodline"
    ],
    cliffhanger_formulas=[
        "He pins her against the brick wall, dark tattoos curling up his neck: 'You belong to my territory now. Run again, and I burn this city.'",
        "Gunfire erupts outside as the rival Don steps into the moonlight: 'Release my daughter, Alpha, or we start a war.'",
        "Her eyes glow silver in the reflection of his blade: 'You thought I was prey... think again.'"
    ],
    default_cast=[
        Character(
            name="Aria",
            role="Protagonist",
            look="Torn black leather jacket, messy braided hair, defiant dark eyes, blood scrape on temple",
            voice="Breathless, defiant, fearless"
        ),
        Character(
            name="Kaelen",
            role="Deuteragonist",
            look="Imposing muscular build, black tactical coat, silver wolf ring, predatory golden eyes",
            voice="Baritone, guttural, lethal calm"
        ),
        Character(
            name="Vance",
            role="Antagonist",
            look="Silver-tipped cane, scarred jawline, blood-spattered velvet coat",
            voice="Raspy, sinister, mocking"
        )
    ],
    pacing_rules=(
        "0-3s: Immediate lethal ambush or cornered flight. "
        "15s: Savage intervention of the powerful protector. "
        "30-40s: Intimate physical clash between predator and protector. "
        "50-60s: Territory claim or war declaration on the cliffhanger."
    ),
    suggested_shots=8,
    seconds_per_shot=8
)
