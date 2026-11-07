# First still batch QA

Status: route validated with one paid image after the user's 3:01:35 PM IST approval to try the quoted rebuild estimate.

## API result

- Endpoint: Magic Hour AI Image Editor
- Job: `cmvnmqcuo018xje01pq6egb0h`
- Model: `seedream-v4.5`
- Input references: 5 character/location reference images
- Output count: 1
- Output size: 576x1024
- Credits charged: 50
- Local output: `/tmp/e01-v3-still-batch-01/shot07-action-peak-candidate-01.png`

## Visual inspection

The frame shows Harry holding a slim wooden wand. No sword, rapier, blade, knife or metal cuffs are visible. The silver curse elements read as flexible magical ribbons, not handheld weapons. Both faces are recognizable against the references, the formal outfits are consistent enough for the next candidate batch, and the candlelit Yule Ball setting is preserved.

Caveat: this is one still, not proof of full-episode consistency. The next batch must compare multiple poses and transitions before any video generation.

## Route finding

- AI Image Editor supports multiple reference images. Current docs list up to 9 additional input images for `seedream-v4.5` and `nano-banana-2.1`.
- `nano-banana-2.1` rejected the requested 9:16 editor configuration, so it is not the current vertical-still route.
- `seedream-v4.5` accepted 9:16 with one output image and charged 50 credits.
- Image-to-video supports a start image and an end image for MiniMax H3. Mid-shot stills guide selection and QA, but they are not hard pins in the public Magic Hour image-to-video schema.
