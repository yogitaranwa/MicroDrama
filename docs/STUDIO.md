# Studio: from a short brief to a reviewed script

`python audiofirst.py studio draft|approve` is the front of the micro-drama generator. You give it an idea (and optionally a room and
character names); a connected LLM writes the story; the pipeline's own validators check it; you read a review pack and approve it.
**Drafting spends no credits.** Production (below) refuses to start without the approval file and spends only inside the approved cap.

```
brief.json ──► LLM draft ──► repair loop ──► compile (code does geometry) ──► validators ──► REVIEW.md + price ──► approve
   ──► produce: assets ─► per shot [start frame ─► YOU review it ─► video ─► speech check ─► last frame] ─► score ─► assembly ─► film.mp4
```

## Run it

```sh
# brief.json: {"idea": "...", "environment": "", "characters": 2, "seconds": 48, "tone": "...", "names": []}
python audiofirst.py studio draft --brief brief.json --model qwen2.5:7b-instruct-q4_K_M --out output/my-film
python audiofirst.py studio approve --out output/my-film --max-credits 4500
```

* `environment` empty: the LLM invents a small closed room that suits the story (the user then sees it in the review and can change it).
* The model must already be installed in Ollama (`ollama list`); the tool never downloads one. The LLM is a two-method interface
  (`chat(system, user)`), so an API model later is a new class, not a rewrite. `--replay saved.json` replays saved replies offline.
* Output folder: `REVIEW.md` (script, shot timings, first-frame chain, reference-image prompts, price), `story.json`, `pack.json`,
  `quote.json`, `draft-history.json`, `views/floor-plan.png`, `views/camera-<name>.png` (what each camera sees).

## Produce it (spends credits, inside the approved cap)

```sh
python audiofirst.py studio produce --out output/my-film              # runs until a start frame needs your eyes
python audiofirst.py studio accept  --out output/my-film --shot s01-wide --reviewer "Your Name"
python audiofirst.py studio produce --out output/my-film              # video, speech check, next frame ...
python audiofirst.py studio status  --out output/my-film
```

* `produce` is resumable and never pays twice; it stops (and says why) when a frame needs review, a provider job failed or is pending, or a dialogue shot failed its speech check.
* **A start frame is only used after a named reviewer accepts it** (`accept`), because the spend guard needs real evidence that someone looked at the pixels; the tool does not
  fake it. `reject` regenerates a bad frame (one image credit; the old file is kept).
* Each video is transcribed at once. A dialogue shot must say its line (word error under 0.35, at most one extra word). If it fails, the run stops: re-rendering costs credits, so you decide
  with `--allow-rerender SHOT` (one paid re-take per flag; the failed take is kept). A silent shot that gets invented speech does not stop the run; its audio is replaced with the room's own
  ambience in assembly.
* Frames chain: `continue` copies the previous last frame, `resume` and `build` use it as the first reference (see rules below).
* The provider is `kling-3.0` unless you pass `--video-model`; a failed or pending job is never resubmitted automatically (`error`/`submitted` ledger states block until reconciled).
* The assembler (colour match, ducked score, captions, hook and end card) was checked on synthetic clips; the credit-spending path was exercised with a fake provider, and by hand in the
  earlier Cold Cycle run, not yet by an automated live run of this exact command.

## What the LLM does and does not do

The LLM writes only story: two characters (look, wardrobe, voice), a room (features on named walls, a centre piece), and the shots
(wide, entrance, dialogue, insert) with lines of at most 9 words and what each speaker is busy with. It never writes coordinates or video
prompts, because small models are good at story and bad at geometry. Code then builds the floor plan, fixed camera set-ups, marks,
framing text and prompts.

* The pack is checked (speaker names, line length, no ellipses, no idle speakers, valid features, shot count); the LLM is shown each problem
  and asked to fix its own answer, up to `--repairs` times.
* The compiled story must pass `validate_directed` (timed beats, motivated action, arrival reasons, blocking continuity, 2500-character prompts).
* Approval is bound to the sha256 of the exact script and a credit cap at least as large as the quote; editing the script invalidates it.

## Pipeline rules this stage relies on (all in `directed.py`)

* **Chained first frames** (`rules.chain`): `first_frame_plan` says, per shot, `continue` (same angle and people as the previous shot: its real last frame
  is the first frame, no image job), `resume` (an earlier shot used this angle: its last frame is the first frame reference, so people return to
  where the story left them) or `build` (a new angle: built from the previous shot's real last frame, the plate, portraits and layout guide).
* **Motivated action** (`rules.activity`): everyone on screen has a task (`activity`), and anyone who enters or moves to a new place has an
  `arrival` with from, to, why and the first thing they do there. "Standing" and "waiting" are rejected.

## Limits of this first build

* Exactly two on-screen characters and one closed room; 4-second shots.
* With a 7B local model (tested: qwen2.5:7b-instruct-q4_K_M, about 6 minutes, one repair) the story is valid but generic and sometimes odd
  ("typing on the desk"); quality scales with the model. The validators check structure, not whether the story is good.
* Nothing here judges voices, lip sync or acting; only a person watching the finished film can.
