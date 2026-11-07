# E01 correction report and still-first plan

## Recovered instruction

Searchable WhatsApp history recovered the earlier instruction at 9:40:32 AM IST:

> Reference images should be too many so that consistency maintains in video

The exact 1000 number appeared in the user's correction at 2:56:44 PM IST, then the user clarified at 2:59:33 PM IST:

> 1000 is just a number
> You decide that number how many are required for consistency

Conclusion: the still-first requirement is real, but the count should be coverage-based. The first cut violated the still-first requirement by generating separate moving shots from text plus one reference each, then checking consistency afterward.

## Separate diagnosis

### Script

Problem: v2 used too many compressed fragments, including "Efficient," "You didn't," "Then count faster" and "Show off." Those lines made the voices feel artificial even when the audio timing was technically aligned.

Correction: v3 uses complete natural sentences. The episode now has 12 shots and 15 spoken lines. It keeps the same story and cliffhanger but gives each line a clear human intent.

### Voice

Problem: the accepted voice identities were not the main failure. The fragmented script made the delivery feel chopped up, and the user could not separate script faults from video faults.

Correction: keep the accepted Draconia and Harry voice IDs. Regenerate only after v3 script direction is locked. Review the dialogue as a standalone audio scene before any moving video is made.

### Visual

Problem: the first cut generated 18 moving shots separately. Each shot had a prompt and limited references, but there was no 1000-candidate still pool and no shot-by-shot still continuity gate. That allowed face, prop and expression drift, including the sword-like objects in shot 8.

Correction: generate and select stills before motion. Every candidate still carries shot, beat, action, camera, expression, wardrobe and required props. A still cannot enter the video stage until face, wardrobe, prop and expression checks pass.

### Stitching

Problem: too many micro-cuts amplified the fragmented dialogue and made continuity harder to hold.

Correction: reduce E01 from 18 shots to 12 longer shots, with motivated transitions and a final assembled continuity pass. Stitch QA includes shot-boundary identity, prop state, black frames, audio timing and visible speaker checks.

## Right-sized still plan

- 12 shots x 7 key beats = 84 required still states.
- 3 candidates per required state = 252 candidate stills.
- The selected continuity set keeps 84 canonical stills plus alternates.
- Stage 1 is a small priced batch to verify model quality and actual charge behavior.
- Stage 2 fills the 252-candidate pool only after script, voices and model choice are stable.

## Current Magic Hour cost grounding

Docs list image generation rates from 5 credits per image for lower-cost models to 40-150+ credits per image for stronger models. Actual cost can vary by model, resolution and image count, so the first priced batch response must be recorded before scaling.

Estimated floor cost at 252 stills:

- `seedream-v4` at docs floor 40 credits/image: about 10,080 credits.
- `nano-banana-2.1` at docs floor 50 credits/image: about 12,600 credits.

Additional expected video generation for a 90-105 second E01:

- MiniMax H3 at 720p: 48 credits/second, about 4,560 credits for 95 seconds.
- Lip Sync Pro for 40-60 seconds of visible dialogue: about 1,920-2,880 credits at 2 credits/frame and 24fps.
- Retry allowance: about 3,000-8,000 credits depending on visual QA failures.

Bounded incremental forecast: about 19,500-29,000 credits. Already spent: 7,291 credits. Projected total: about 26,800-36,300 credits.

These are estimates, not a quote. The projected existing balance after the completed shot 8 correction is 153,869 credits. No new paid generation is running now.

Source: https://docs.magichour.ai/api-reference/models and https://docs.magichour.ai/tools/image/image-generator


## First route validation, 3:02 PM IST

After the user approved the quoted forecast with "Ok try please," one paid still was submitted through AI Image Editor with five character/location references. Job `cmvnmqcuo018xje01pq6egb0h` completed, charged 50 credits and produced a 576x1024 vertical still. Visual inspection found a clear wooden wand, no sword/blade/metal cuffs, flexible magical ribbons and recognizable Harry/Draconia identities.

Important route constraint: MiniMax H3 image-to-video accepts a start image and an end image. The full still pool is therefore used to select start/end anchors and to QA pose/action continuity. It does not hard-pin every mid-shot frame through the public API.


## Editorial pass v3.1

Main reviewed the actual v3 script and rejected it as an initial draft: the table count was wrong, some complete sentences still sounded stiff, quips competed with the threat, and several causal links were not visible. V3.1 fixes the script before further voice or still generation: fifteen lines, visible cause-and-effect, natural contractions, fixed Harry/Draconia hair and outfit rules, and a final reveal that Draconia's warning was intercepted.

A first ElevenLabs v3 voice sample was generated before that editorial correction arrived. It used 1,005 submitted characters and is preserved locally, but it is not part of the production path and will not be reused for the revised script.


## Voice pass v3.2

The revised fifteen-line script was rendered once with the accepted Draconia and Harry voice identities. The 49.5 second sample had fifteen segments and 709 submitted characters. Automated readback was mostly accurate, but it heard "armor's" as "arm", so the line was simplified to "The armor is moving. We need that trolley." before the corrected pass. This is transcript/structure QA only, not a claim of human listening or final emotional quality.


## Three-image still QA correction

The first v3.1 three-image continuity batch was rejected as final anchors after direct visual inspection. Shot 3 showed ice skates/blades and the wrong frozen-guest action. Shot 12 added a jeweled top tiara/crown not present in the accepted reference. Hair, face and broad outfit identity were close in places, but that is only a partial pass. The character bible now explicitly locks formal dress shoes, no skates/blades, no tiara/crown, and only the accepted small braid pin. No full still pool has launched.


## Voice and still QA ledgers

The detailed still and voice ledgers are now separate docs. Still-route testing has used 400 Magic Hour credits and has not approved a full pool. Voice QA has submitted 3,100 ElevenLabs characters across rejected drafts, the emotional reference render and segment diagnostics. Clean source clips are preserved; quick MP3 splice previews are discarded.

## E01 v4.3 final delivery checkpoint - 2026-10-25 16:59 IST

The still-first E01 rebuild reached a delivered final candidate v3: 94.254 seconds, 720x1280, 24fps, 15 dialogue lines in order, 14 selected visual rows. Final zero-credit corrections removed shot10 source banding and moved line14 onto a no-face hands/marks insert to avoid visible closed-mouth speech. Drive contains the updated final MP4, selected manifest, assembly plan, QA contacts and final-gate addendum.

Current ledger remains 17,935 Magic Hour credits overall and 10,644 post-acceptance. No new credits were spent after the final QA corrections. E01 is delivered and user feedback is pending. Broader pipeline closeout means preserving this code package, final manifests, QA ledgers and current Drive artifacts; it does not authorize a ten-episode batch or any additional spend.
