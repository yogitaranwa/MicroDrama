# h3-film

One request in, one finished video out.

h3-film turns a request, typed in any language, into a finished mp4. The request can come with pictures, a logo, a song, a voice recording, video clips or links. A first Claude session (the producer) works out what the request means, studies real examples and writes a brief. A second Claude session (the planner) writes the film: the script, the soundtrack, the still pictures and one prompt per clip. MiniMax H3 draws the clips on Modal GPUs, to the finished soundtrack. Code cuts the clips together and draws captions and lyrics on top. It makes explainers, documentaries, software launch films, lyric videos, edits of the user's own footage, map films, logo animations, ads and short-form videos, in 77 house styles or in a look it studies from a linked video.

## Pages

- **Quick output gallery:** https://claude.ai/artifact/25Neomyh8NnVyMYcPzDa33
- **Internal library** (styles, examples, voices, settings): https://claude.ai/artifact/XgUGhxuSZSPdpwDET9vcYF
- **Full test batches**, with cost and score per film, most recent first:
  - [Tonight's Batch, 10-11](https://claude.ai/artifact/CnoJEe6hqJonBHqkkVRGdJ)
  - [Current Film Costs, 10-10](https://claude.ai/artifact/3zYh3KzZnVYkQeBuQQF34e)
  - [Random Inputs Round 2, 10-10](https://claude.ai/artifact/G8ZhLvZf1mZdFbKZKs8He7)
  - [Random Inputs Review, 10-10](https://claude.ai/artifact/CFcZ4ZQMtwYYE4oSnsLWpa)
  - [Style Scorecard, 10-07](https://claude.ai/artifact/Y2HZ3WXFqJ28H6YX7CbFou)

## Overview

**Repo:**
- [private-project-source] (private) is the repo to build from. README.md is the full implementation guide; AGENTS.md has the rules for working in the repo. batches/ holds every test film shown on the pages linked below, with its video, its record (request, brief, plan, prompts, settings) and its cost, time and score (batches/index.csv).

**GPU:**
- RTX PRO 6000 Blackwell (Blackwell is needed for H3's nvfp4 text encoder). About 37 GB of weights.

**Model:**
- MiniMax H3, Reference to Video (draws the clips)
- Claude Sonnet 5.5 (the agent: producer and planner), with our film tools (an MCP server), file read and write, web search and fetch, and a shell. The repo runs it in Claude Code.
- Nano Banana 2.1 (stills), ElevenLabs (music, sound effects, speech to text, voices for languages Magic Hour doesn’t support), Magic Hour voices

**Inputs:**
- Prompt (any language; links in it are studied first)
- Uploads, optional: videos, images (e.g. character, place, product, logo), audio (e.g. song, voice recording)
- Aspect ratio: 16:9, 9:16, 1:1, 4:5, 3:4, 4:3, 21:9
- Duration: 5-60 s, optional (the agent picks if left blank)
- Resolution: 480p, 720p or 1080p

**Outputs:**
- One mp4 with music, voices and sound effects, at the requested length, aspect and resolution

**Generation time:**
- About 21 s per second of film on average (range 8-38 s): planning 13 s, rendering 8 s with every clip of a film on its own GPU. By kind of film: drawn films 16 s, footage edits and swaps 19 s, launch films 31 s, lyric videos 32 s, map films 17 s. From the latest batch (22 films, 15-60 s long, 10-12; batches/index.csv). Rendering grows with resolution, roughly 2.5x at 720p and 3.5x at 1080p.

**Resolution:**
- Up to 1080p, in every aspect ratio above. H3's sizes for 16:9: 832x480, 1248x704, 1408x800. The repo writes the film at H3's size; scale 720p and 1080p up to 1280x720 and 1920x1080 at the end.

**Cost:**
- About $0.05 per second of film at 480p on average (range $0.02-0.085): Claude $0.024, pictures and sound $0.005, rendering $0.022 (27 GPU-seconds on an RTX PRO 6000 at $3.03 an hour). By kind of film: drawn films $0.043, footage edits and swaps $0.050, launch films $0.074, lyric videos $0.053, map films $0.041. Rendering grows with resolution.

**Notes:**
- H3 needs two additions, and every clip uses both: the clip's own soundtrack held fixed (audio inpainting: H3 draws the picture to the finished sound, which gives the best lip and beat sync), and frames pinned at set times (MiniMaxH3AddGuide). Our ComfyUI graph has both: research/h3/runpod/r2v_v1.json, built by comfy_r2v.py.
- Keep prompt enhancement OFF (the opposite of the H3 Colab): it summarises the agent's prompts and drops the shot timings.
- Keep the render settings in the repo (25 steps, T8 cache). The official 50 steps at full precision were not better and 3.5x slower.
- Run the agent in a container: it reads web pages and runs shell commands, so only the film tools should hold API keys.
- Real footage and songs come from YouTube through yt-dlp, which YouTube blocks on servers: give yt-dlp a signed-in account's cookies and keep it updated, or use licensed media. Fan edits, sports edits, recaps, memes and lyric videos depend on it.
- The agent must see every tool description in full (up to 12,288 characters). In Claude Code (2.1.285, the version every test film ran on), set CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH=12288 (it cuts them at 2,048 otherwise).
- Licensing: the background-removal model (BRIA RMBG-2.0) is non-commercial; style sample frames and logo packs come from other companies. Review before shipping.
- The quality of the internal library (styles, examples, voices, settings) is a massive quality lever. Consider what examples/styles the agent and H3 are given to copy. The current library was put together quickly: https://claude.ai/artifact/XgUGhxuSZSPdpwDET9vcYF
- For Codex: start with the README's "How to build this into Magic Hour" section (also in AGENTS.md): what must stay exactly as it is, what is ours to choose and what we recommend, the order to build in, and how to check quality against the test films in batches/.

## How to build this into Magic Hour

This repo is a working system: one request in, one finished film out, made by two Claude Code sessions (the producer and the planner; a film with map shots adds two Claude Agent SDK sessions) and MiniMax H3 on rented GPUs. Building it into Magic Hour means running the same steps behind Magic Hour's own API, on its own servers and GPUs. Some parts are proven and must stay exactly as they are; the rest is Magic Hour's choice.

### Keep exactly as it is

- **The agent's instructions.** The films look the way they do because of this text, and editing it changes the films:
  - the producer's prompt (`agent/h3film/auto.mjs`, with the video studies `kit.mjs` writes) and the style list it picks from, with each style's score and planner mode (`agent/web/app/styles/menu.ts` and `presets.ts`, `agent/scorecard/ratings.json`, `agent/runs/_styles-log/best-takes.json`);
  - the planner's prompt as `agent/h3-film-agy.sh` puts it together: the skill files in `skills/h3-film/` (SKILL-gemini.md, PAINTED.md, MINIMAL.md, FOOTAGE.md and, for swaps, FOOTAGE-swap.md, REFERENCES.md, `usecases/`; for launch films also `references/`, `agent/h3film/library/` and `agent/h3film/exemplars/`), the style cards with their reference frames and example films (`agent/web/app/styles/`) and the six example runs in `agent/runs/`;
  - every tool description in `research/h3/` (`mcp.mjs`, `tools-*.mjs`), and the planner's hooks and what they run (`agent/h3film/planner-hooks.json`, `planner-check.mjs`, `planner-stop.mjs`, `build-edit.mjs`);
  - the map stages' prompts and example films (`agent/v2/DOCTRINE.md`, `agent/v2/stages/`, `agent/v2/direction/`);
  - the names from earlier setups that this text refers to: `agent/h3-film-agy.sh` starts Claude, `SKILL-gemini.md` is the Claude planner's skill, `research/h3/runpod/` builds the Modal jobs.
- **The two code paths** (1.3): the swap question in `agent/h3film/auto.mjs` and everything that reads `H3_SWAP` (`agent/h3-film-agy.sh` gives a swap `skills/h3-film/FOOTAGE-swap.md`, `research/h3/soundtrack.mjs` keeps the swap films' seam and bed rules). A swap runs exactly the code that made the approved swap films; every other film runs exactly the code that made the 10-12 batch. Work for swaps stays on the swap path (AGENTS.md).
- **The H3 render setup.** Magic Hour's production graph `research/h3/runpod/r2v_v1.json` (ComfyUI v0.36.0: the pruned int8 model, the nvfp4 text encoder, 25 steps with the T8 cache) and the two additions `comfy_r2v.py` wires into each clip's job: the clip's own slice of the soundtrack held fixed (audio inpainting) and pictures pinned at set frames (MiniMaxH3AddGuide). Prompts go in word for word, with no prompt enhancement. Keep also how `agent/h3film/render-all.mjs` prepares each clip: its render length, the size of its reference videos, its pins (5.2). As tested, neither Magic Hour's public H3 API nor fal offers the two additions alongside references (5.9).
- **The sound rules** in `research/h3/soundtrack.mjs` (voices, loudness, the mix) with the voice lists in `research/h3/voices/`, **the join** in `agent/h3film/join.mjs` (the soundtrack played once under the film, captions and lyrics drawn by code), and **the files passed between steps** (`brief.txt`, `render.json`, `soundtrack.json` and the rest; 1.5).
- **The models and their effort**: Claude Sonnet 5.5 for the producer (medium), the planner (high; medium for launch films, lyric videos and films modelled on a video) and the map stages (medium), with Claude Code 2.1.285's own helper model (Claude Haiku 4.5), which reads fetched web pages; Nano Banana 2.1 for pictures and Nano Banana 2 for the map cut-outs (both on fal); ElevenLabs `scribe_v2` (speech to text), `music_v2_5` (music), sound effects, forced alignment (map shots) and `eleven_v4` (voices in the languages Magic Hour's voices are not used for); Magic Hour's voices; MiniMax H3, reference to video.

### Magic Hour's choice, with our recommendation

- **How the agent runs.** The repo runs the producer and the planner as Claude Code sessions (`claude -p`), and the map stages through the Claude Agent SDK, which runs the same kind of session from code. Every test film planned by `claude-sonnet-5-5` was made this way, on Claude Code 2.1.285: keep exactly that version, as the server image does (7.7). Claude Code runs headless on Linux. The producer has web search, web fetch, Read and a shell (it runs `fetch.mjs` and `kit.mjs`) and answers in a fixed JSON schema. The planner has the film tools as an MCP server (`research/h3/mcp.mjs`), file tools, web search and web fetch; only a launch film's planner also keeps a shell. A loop of your own on the Claude API can come later, but it then has to give the sessions what Claude Code gives them today: those tools; every tool description in full (up to 12,288 characters); tool calls of up to 30 minutes; `storyboard` and `make_soundtrack` calls side by side and other film-tool calls one at a time; the planner's two hooks (a check after each file write, and a stop as soon as the film is whole); pictures in the first message; fetched pages read by Claude Code's helper model; and the 5-minute prompt cache.
- **GPUs.** The same graph on Modal (`research/h3/modal_h3.py`: RTX PRO 6000 first, then B200) or on your own Blackwell GPUs (the nvfp4 text encoder needs Blackwell). Moving off Modal changes one call in `comfy_r2v.py` (5.9). render-all sends all clips of a film at once (a clip that continues a shot from the clip before waits for it); Modal's account cap (10 GPUs on the Starter plan) makes the rest wait.
- **Jobs and storage.** One film is one job and one run folder (`agent/runs/h3film-<name>/`; the producer's brief and log go to `agent/runs/_auto/`). Films also write shared caches and new style cards into the repo (7.6), so give each worker its own writable checkout. A film whose planning fails is not planned again: nothing renders and `./film` exits 1. Rendering is retried: `auto.mjs` runs render-all up to three times, and each run reuses every clip already rendered from the same inputs.
- **Real footage and songs.** yt-dlp with a signed-in account (the code passes no cookie option: put `--cookies <file>` or `--cookies-from-browser <browser>` in `~/.config/yt-dlp/config`, 7.2), or licensed media.
- **Sandbox.** Nothing is sandboxed today: the producer, launch planners and map stages run shell commands with permission prompts off, and every session inherits every key in `.env.local`, which every planner can also read. Run the sessions where they cannot reach the keys. Today the code that needs keys runs inside their reach: the tool server is started by the planner's session, and the producer runs `kit.mjs` (ElevenLabs speech to text) from its shell (12).

### Order of work

1. Run the repo as it is (7.2; on Linux, the server image in 7.7 has made a real film) and remake three test films: one drawn film, one footage edit and one launch film. Rows x24 (drawn), x01 (footage edit) and x27 (launch film) of `agent/h3film/random-inputs-v3.tsv` need no uploads: `mkdir -p agent/runs/_auto; TSV=agent/h3film/random-inputs-v3.tsv RUNPFX=<new prefix> agent/h3film/run-v3.sh x24 x01 x27` (8.3). Compare them with the same rows' takes in `batches/films/` (8.5 names the scored ones; the `r1-` takes were made from this repo on 10-12).
2. Put the same scripts, unchanged inside, behind your API: one request, one job, one mp4. A request is `./film "<request>" [uploads…] [--aspect <ratio>] [--duration <seconds>] --name <job>` (`--ref` for references from Magic Hour's library, `agent/h3film/MH-REFERENCES.md`); for 720p or 1080p set `GPU_ROWS` to 704 or 800 and scale the film up at the end (5.7). The film is `agent/runs/h3film-<name>/final-gpu.mp4`; no film means exit code 1.
3. Replace the infrastructure one piece at a time (GPUs, storage, sandbox, media fetching), proving each with the free checks in 8.1 (for GPUs, the test in 5.9) and then remaking the same three films.
4. Only then port or refactor (for example, Claude Code to your own API loop), checking the films after each step.

### Checking that nothing got worse

Check every change by remaking test requests and watching the results next to the same requests' films in `batches/`; nothing judges them automatically (8.7). Each film there has its video, its record (request, brief, plan, clip prompts, render settings, soundtrack timings) and its score (if rated), cost and time (`batches/index.csv`); the films planned by `claude-sonnet-5-5` (the current pipeline) that scored 8 to 9.5 are the bar. The same request gives a different take every time (the producer, the planner, the pictures and the H3 seed all change), so judge a change on several films, never on one.

A change meant to leave the films alone can be proven for free: record what the producer and the planner receive on the old code and on the new, and compare them byte for byte (`tools/same-input/`). If both get exactly the same input, the films cannot change. Make films only where the input changes: several takes, judged blind next to the bar.

## Contents

This README is the full guide to the system: what each part does, the files and fields passed between parts, where every prompt and rule lives, every outside service and its settings, the decisions behind the current settings, how to run and test it, and what is known to be weak. It describes the code as it is in this repo. The settings in the code are the ones that made the best recent films (rated 8 to 9.5). `AGENTS.md` holds the rules for anyone changing the code.

This repo was cut on 10-12 (dates are 2026) from the research repo where the pipeline was built, called the lab below. Everything a film needs is here, at the same paths; nothing in this guide needs the lab.

1. [How it works, end to end](#1-how-it-works-end-to-end): the steps, what runs where, how a request becomes a kind of film, the run folder, the files passed between steps, conventions, failures, the folder layout
2. [The producer](#2-the-producer): request in, brief out
3. [The planner and its tools](#3-the-planner-and-its-tools): brief in, soundtrack, stills, clip prompts and `render.json` out
4. [Sound, captions and the join](#4-sound-captions-and-the-join)
5. [Rendering](#5-rendering): `render.json` in, one clip per entry out, on MiniMax H3
6. [Maps and shots drawn in code](#6-maps-and-shots-drawn-in-code)
7. [Setup and running](#7-setup-and-running): install, settings, making a film, the server image
8. [Testing](#8-testing): free checks, the test requests and their films, how films were scored, costs and times
9. [Decisions that must not be undone, and what was tried and rejected](#9-decisions-that-must-not-be-undone-and-what-was-tried-and-rejected)
10. [Quality levers](#10-quality-levers)
11. [Known problems](#11-known-problems)
12. [Licensing and security](#12-licensing-and-security)

Start with [How to build this into Magic Hour](#how-to-build-this-into-magic-hour) above.

Other documents in this repo:

- `AGENTS.md`: rules for coding agents and engineers working in this repo (`CLAUDE.md` loads it).
- `docs/ticket.md`: the ticket for building this at Magic Hour, as sent (the Overview above).
- `docs/lessons.md`: the lessons learned while building the pipeline, each with its reason (what H3 does with prompts, stills and references; sound; footage edits; swaps; maps; testing; what was rejected).
- `docs/lab/`: the build history as written at the time: the day-by-day notes, every commit message, and the guides behind the style builder, the style cards and menu, the video studies, the map engine and the first H3 research (`docs/lab/README.md` lists them).
- `docs/history.md`: how the pipeline got here, newest first, from 2026-09-12 to 2026-10-12. Its run names and commits refer to the repo this one was cut from; nothing here needs them.
- `batches/README.md`: the test films and their records (section 8.4).
- `tools/pages/README.md`: the builders of the pages linked above.
- `agent/h3film/RULES.md` and `research/h3/prompts/orchids-reveal/GUIDE.md`: H3 prompt rules for launch films, each with the take that set it. `skills/h3-film/MERGE-AUDIT.md`: those lessons checked against the painted path.
- `agent/v2/MAPS-IN-H3.md`: background on the map engine.
- `agent/h3film/MH-REFERENCES.md`: how Magic Hour's saved reference items map onto `--ref`.

To make a film right away, do the setup in 7.2 and run the command in 7.1.

## 1. How it works, end to end

### 1.1 The steps of one film

```
./film "<request>" [files…] [options]   zsh: loads .env.local, unsets every CLAUDE* variable, sets H3_BUDGET_USD=20 if unset
 └─ node agent/h3film/auto.mjs  (same arguments)
     1. PRODUCER    kit.mjs first studies every link in the request and every uploaded video (frame sheets, cuts, words);
                    then one Claude Code session (claude -p), shown those sheets, answers one JSON object;
                    code turns the answer into the brief (agent/runs/_auto/<name>.txt)
                    and seeds the run folder agent/runs/h3film-<name>/ (attached/, refs/, reference/)
     2. PLANNER     agent/h3film/launch-locked.sh <run> -- agent/h3-film-agy.sh <name> <brief> 0
                    one Claude Code session with the tool server research/h3/mcp.mjs and two hooks; writes PLAN.md,
                    soundtrack/, the stills, prompts/clipN.txt, render.json (or EDIT.json, built into render.json), NOTES.md
       2b. MAP SHOTS  only if the planner called map_shots: agent/h3film/maps.mjs runs in the background;
                      the launcher returns only after maps/done.json or maps/failed.json exists
     3. LYRIC TIMES only if the run has lyrics.json, soundtrack/song.json and a clip prompt with [Ln] ids:
                    python3 agent/h3film/lyric-retime.py <run> 0
     4. RENDER      node agent/h3film/render-all.mjs <run>, run up to 3 times until final-gpu.mp4 exists;
                    each H3 clip: .venv/bin/python research/h3/runpod/comfy_r2v.py → one Modal call (app h3-render, class H3)
     5. JOIN        joinFilm() in agent/h3film/join.mjs, called by render-all → agent/runs/h3film-<name>/final-gpu.mp4
```

| Step | Runs on | Decides | Median time | Median cost |
|---|---|---|---|---|
| 1. Producer | Claude Sonnet 5.5, medium effort | what the film is: its kind, its style, the real material it needs, the brief | 0.8 min | $0.14 |
| 2. Planner | Claude Sonnet 5.5, medium or high effort | the script, the soundtrack, the stills, every clip prompt | 3.3 min | $0.43 |
| Tools | Nano Banana 2.1, ElevenLabs, Magic Hour voices, HyperFrames | make what the planner asks for | inside planning | $0.16 (pictures and sound) |
| 4. Render | MiniMax H3 on Modal GPUs | draws each clip | 5.7 min, with the join | $0.66 |
| 5. Join | ffmpeg and Pillow | cuts, sound, captions | | |

Medians over the newest take of each of the 35 test requests on the batch page (10-10/11, 480p tier); a whole film 11.1 min and $1.46. Section 8.8 has the sources, the latest batch's figures and the cost basis.

Each step is its own process. Steps pass work only through files in the run folder and a few environment variables, so any later step can be run again on a finished run folder (render-all alone, for example). Run by hand, a step needs the variables `auto.mjs` gave it, which the run folder does not hold. For render-all these are `GPU_ROWS`, set exactly as `auto.mjs` set it: `GPU_ROWS=` (set and empty) for the 480p tier, `704` for the `2-5d-hybrid` card. Its raw value is part of every clip's reuse key, so an unset `GPU_ROWS` renders every clip again. It also needs `H3_DURATION` (the brief's `Length:` line, when there is one) and `H3_BUDGET_USD=20` (its own default, 5, refuses longer films). `--plan` stops before step 3, so a lyric film planned that way needs `lyric-retime.py` before render-all.

What waits for what:

- The planner starts only after the brief is written.
- A planner session ends in one of three ways: its stop hook sees a whole film and ends it (3.6); the model stops on its own; or a tool writes `FAILED.json` and the launcher kills the session (it checks every 3 s).
- Map shots start in the background the moment the planner calls `map_shots`; the planner keeps working. The launcher does not return until the map shots finish or fail.
- Rendering starts only after the launcher returns. All H3 clips of a film render at the same time, except a clip that continues a shot from the clip before it (5.2 step 8).
- The join runs inside render-all once every clip exists.
- render-all is tried up to 3 times. A clip already rendered from the same inputs is reused, so a retry renders only what is missing.

### 1.2 What runs where, and where the keys are

| Piece | Runs on | Calls out to |
|---|---|---|
| `./film`, `agent/h3film/auto.mjs`, `kit.mjs`, `fetch.mjs` | the worker machine | yt-dlp (YouTube and any link it opens), LRCLIB (synced lyrics), ElevenLabs speech to text, TikTok and YouTube Shorts pages and Apple's iTunes lookup (a video's credited sound), the image URLs the producer gives for characters and real people (`auto.mjs` downloads them) |
| Producer session (`agent/h3film/claude.mjs`) | the `claude` CLI on the worker, working folder `<os temp>/h3-claude-ask` | Anthropic; built-in WebSearch, WebFetch, Bash (it runs `fetch.mjs` and `kit.mjs`), Read |
| Planner session | the `claude` CLI on the worker, working folder `~/h3-claude/h3film-<name>` | Anthropic; the tool server over stdio; built-in Read, Write, Edit, Glob, WebSearch, WebFetch (launch films keep every built-in tool) |
| Tool server `research/h3/mcp.mjs` (+ `tools-film.mjs`, `tools-footage.mjs`, `tools-codeshot.mjs`, `tools-maps.mjs`, `soundtrack.mjs`) | node, started by the planner session | fal (Nano Banana 2.1), ElevenLabs (music, effects, voices, speech to text), Magic Hour API (voices), image URLs (`reference_image`), yt-dlp (`web_clip`, and `user_video` given a link), local Chrome (Playwright screenshots, HyperFrames stills and code clips), rembg (local Python) |
| Map shots `agent/h3film/maps.mjs` + `agent/v2/` | a detached node process on the worker | Claude Agent SDK sessions (Anthropic), ElevenLabs forced alignment, fal (cast cut-outs), local HyperFrames renders |
| `render-all.mjs`, `comfy_r2v.py` | the worker (ffmpeg, the Python venv) | Modal (one call per H3 clip); fal (the swapped first frame of a live-action swap clip); ElevenLabs speech to text (speech captions) |
| MiniMax H3 | Modal: ComfyUI v0.36.0 in `research/h3/modal_h3.py`, GPUs RTX PRO 6000 then B200 | the Modal volume `h3-weights` (the model weights) |
| `join.mjs` | the worker (ffmpeg, Pillow) | nothing |

Keys: the tool server, render-all, `maps.mjs`, `fetch.mjs` and `auto.mjs` each read `.env.local` themselves, and no key is written into the planner's prompt or its `mcp.json`. render-all reads it only after its clips have rendered (for speech captions). Run by hand, it needs the keys in its environment before that (`set -a; . ./.env.local; set +a`) when the Modal token is kept in `.env.local`, and for a swap clip's first frame. But `./film`, `auto.mjs` and the launcher load `.env.local` into their own environment, so both Claude sessions inherit every key. A session with a shell (the producer, launch planners, the map stages) could print them, and every planner's Read tool can reach the repo folder. In a rebuild, give the keys only to the tools and run the sessions in a sandbox (section 12).

Neither film session ever loads this repo's `CLAUDE.md` or `AGENTS.md`: both run from folders outside the repo, `--add-dir` loads no memory files by default, `./film` unsets every `CLAUDE*` variable, and the map stages start with no setting sources. Keep it that way: instructions for coding agents must never reach a film session.

Every test film planned by Claude ran on Claude Code 2.1.285; keep exactly that version (7.2, 7.7).

### 1.3 Kinds of film, and how each is routed

The producer picks a menu section and a style card. Code turns those two picks, plus what was attached, into the planner's instructions, effort, example films and render size. Three kinds of film, as the code names them:

- **Launch film** (`LAUNCH=1`, `H3_PAINTED=0`): a software product launch film built from motion components cut from real launch films. It follows the launch path of `skills/h3-film/SKILL-gemini.md`.
- **Painted film** (`H3_PAINTED=1`): every other film, edits of the user's footage included. H3 draws each shot from stills and words. It follows `skills/h3-film/PAINTED.md`.
- **Minimal** (`MINIMAL=1`): only the `bold-flat-poster` card, planned from `skills/h3-film/MINIMAL.md` and the card. The launcher still runs it as painted (`H3_PAINTED=1`, map shots offered).

On top of the kind, a brief can add footage (`FOOTAGE.md`), the user's references (`REFERENCES.md`), map shots (`map_shots`) and lyric ids.

**Section to use-case file.** The section is the producer's `use_case` when the card is in it, else the first menu section that holds the card, else the producer's pick (a studied look is in no section).

| Section | Use-case file |
|---|---|
| Explainer, Documentary, Map video, Tutorial, Event promo, Logo animation, Lyric video | `skills/h3-film/usecases/{explainer, documentary, map-video, tutorial, event-promo, logo-animation, lyric-video}.md` |
| A section named by a use-case file's header lines `section: <name>` and `brief: …`: Ambient loop, Baby Sensory, Space Epic, Comedy Short, Fan Edit, Fruit Drama, Creature What-if, Size Comparison, Sports Edit, Action short, Storytime, Viral short hi, Viral short v3 | that file (`*-uc.md`, `viral-short-*.md`) |
| Software launch / demo; Animated chart (no cards, never picked); "Ambient Loop" (a second ambient section, capital L, with no file) | none: the brief says `Use case: none.` |

Such a file's header may also give `aspect:`, the producer's default frame for that section. Its `router:`, `fields:` and `brief:` lines are left from older code and are not read. `anime-music-video-uc.md` names a section the menu does not have, so it is never used.

**Card to kind.** A card's planner mode comes from its best take in `agent/runs/_styles-log/best-takes.json` (`opus-launch`, `opus-minimal`, `opus-painted`, `gemini`), else from a card line `planner: launch` (no card has one), else painted.

- Launch: the card's mode is `opus-launch` (`dark-product`, `cinematic-mockup`, `acid-type`), or the section is Software launch / demo and there is a URL or an attached picture the producer marked as a screenshot. The card then sets only the look. A product with no URL and no screenshot (a candle ad filed under software) stays painted.
- Minimal: not launch, and the card's mode is `opus-minimal` (`bold-flat-poster` only).
- Painted: everything else. Every brief from `auto.mjs` names a card, so every film that is not a launch film runs with `H3_PAINTED=1`.

**Flags the launcher reads from the brief text** (`agent/h3-film-agy.sh`):

| Flag | Set when | Effect |
|---|---|---|
| `CARD` | the first `agent/web/app/styles/cards/<id>.md` in the brief | painted film unless `LAUNCH=1`; a brief naming a card that does not exist stops the launcher |
| `FOOTAGE` | any absolute path or URL ending in `.mp4 .mov .webm .m4v .mkv` | pastes `skills/h3-film/FOOTAGE.md` (`FOOTAGE-swap.md` when `H3_SWAP=1`); the tool server gets `H3_FOOTAGE=1` |
| `UC` | the `skills/h3-film/usecases/<id>.md` path in the brief. With none and no "Use case: none", the first of these words: lyric video, logo animation, map video, for an event, event promo, tutorial, documentary, explainer (only hand-written briefs need this) | pastes the use-case file (painted films only: launch and minimal films do not get it) |
| `REFS` | a line starting `References the user attached` | pastes `skills/h3-film/REFERENCES.md`; the tool server gets `H3_REFS=1` |
| `MAPS` | every painted film | registers `map_shots`; turns `CODE_SHOTS` off |
| lyric ids | each `.vtt` path in the brief (painted, not minimal) | `agent/h3film/lyric-ids.py` writes `lyrics-ids.vtt` and `lyrics.json` into the run; `lyrics-ids.vtt` is pasted, and the note adds the lyric-id rules |
| `CODE_SHOTS` | a card line `tools: … code-shots` (no card has one) | would register `map_clip` and `map_stills`, which crash the tool server (11.3) |

**Effort, example films, render size** (set by `auto.mjs`):

- Planner model `CMODEL`, default `claude-sonnet-5-5`.
- Planner effort `CEFFORT`: the environment's value when set. Otherwise medium for launch films, for the Lyric video section and for a film that follows a given video (the producer's `copy`), and high for everything else.
- Example films pasted into painted films (`EXAMPLES`: each run's `PLAN.md` and `prompts/clip*.txt`, kept in `agent/runs/`): Tutorial (not the `how-to` card): `h3film-t-breathe`, `h3film-breathe-now`, `h3film-style-hand-drawn`. Event promo and Logo animation: `h3film-t-logo`, `h3film-t-event`, `h3film-style-hand-drawn`, `h3film-style-stickman-cartoon`. Lyric video: `h3film-style-hand-drawn`, `h3film-style-stickman-cartoon`. Every other section: none. The launcher stops if a listed file is missing.
- Render rows `GPU_ROWS`: the environment's value when set, else 704 for the `2-5d-hybrid` card, else empty (the 480p tier). It goes to render-all, not to the planner.
- The launcher also gets `PLANNER=claude`, `LAUNCH`, `MINIMAL`, `SKILL` (`skills/h3-film/SKILL-gemini.md`), `RATIO` (`--aspect`, else the producer's frame) and `H3_DURATION`. `H3_DURATION` is set only with `--duration` or `DURATION=1`; `make_soundtrack` then refuses any other length, and render-all gets it too, so the join holds the film to that length.

**What each kind reads and writes:**

| Kind | The planner reads (pasted whole) | render.json |
|---|---|---|
| Launch | `SKILL-gemini.md` whole; `references/motion.md`, `exemplars/hero-edit-magic-hour-ugc-form.txt`, `references/translate.md`, `references/template.txt`; Magic Hour v13 clips 1-3 and the card's own example clips (`refs/<id>/example/clip*.txt`), or Orchids clips 1-4 when the card has none; the card. It then opens `agent/h3film/library/CASTABLE-index.md` and, per cast component, `library/shapes/<id>.md` and `skills/h3-film/references/components/<id>.md` | no `kind`; product, type and sample stills as images; motion clips from real launch films as videos; no pins |
| Painted | `SKILL-gemini.md`'s opening role lines only; `PAINTED.md`; the use-case file; the card; `refs/<id>/exemplar-prompt.txt` if any; every file in `refs/<id>/example/`; the lyric ids; the example films | `"kind": "painted"`; design stills and sample stills as images; the card's style clip as a video, if it has one; pins where a shot opens on a set picture |
| Minimal | one role line; `MINIMAL.md`; the card; its exemplar prompt | `"kind": "painted"` |
| + footage | adds `FOOTAGE.md`, a line naming the user's videos and, with the write hook on, the note that a montage is written as one `EDIT.json` | footage clips (played as filmed, or through H3), painted inserts |
| + the user's references | adds `REFERENCES.md` | |
| + map shots | the `map_shots` tool text | map clips as code clips under `maps/` |

Any film may also hold code clips from `code_clip` (6.12): an mp4 drawn in code that plays as it is.

A painted film gets only the skill's opening lines because the launch reading and `PAINTED.md` contradict each other: on 10-09 a painted planner followed a launch rule pasted above `PAINTED.md` and built a clip that fell into a black void.

**Two code paths, chosen before the producer** (10-12). One short question to Claude Sonnet 5.5 at low effort (`auto.mjs`) asks whether the request is a swap: a scene filmed with other people (a movie or show scene, a clip, a TikTok) made again with named real people in their places, kept live action or redrawn in another look. A swap runs exactly the code that made the approved swap films: the producer also fetches photos of the real people swapped in (2.10), the planner reads `skills/h3-film/FOOTAGE-swap.md` in place of `FOOTAGE.md` (MiniMax's swap layout, a swapped first frame, a remake in another look drawn from pinned stills), and the sound keeps those films' seam and bed rules (4.8, 4.9). Every other film runs exactly the code that made the 10-12 batch, including footage of the real people themselves, a cartoon character dropped into footage and a drawn film about real people. `H3_SWAP=1` or `0` skips the question.

Why: on 10-12 the films made after the batch were judged worse. In a blind round (three requests, two takes each on each code), project-owner found all six takes on the batch's code as good as the batch films, and about one in six on the later code, which mixed the swap work into every film. The question picked out exactly the three swaps among 73 past requests (the 70 run-sheet requests and three swap requests), on two runs; asked six more times each on 10-13, the three swaps were always swaps, and the two closest look-alikes (a basketball edit "like this but" with named players, a cartoon put into footage) never. Checked byte for byte (8.1, `tools/same-input/`): a normal film's producer and planner get exactly what the batch's got, a swap's exactly what the approved swaps' got, apart from the map tool's text in drawn films and swaps (the colour pick taken out, 6.3). The only other changes to the code those films ran: map films take their card's look again, as the approved Hannibal (v48) was made, and the map tool no longer asks the planner to pick the map's style and colours (6.3); the rest turn a failure into a film or a clearer error (a sound file with no sound, an unreadable one, a failed speech to text, a picture service's account error, exit code 1 with no film) or let it run on Linux (fonts, the map stages' sandbox switch, 7.7).

### 1.4 The run folder

`agent/runs/h3film-<name>/` holds everything one film used and made.

| Path | Written by | What it is |
|---|---|---|
| `brief.txt` | launcher (the brief `auto.mjs` wrote, every "16:9" replaced by the frame) | 1.5.1 |
| `attached/` | `auto.mjs` | the user's pictures and sound files, as `<Name>.<ext>` (the reference's @Name without the @; `<Name>-<i>.<ext>` when one reference has several files; WebP and GIF as PNG); a fetched song, or an uploaded video's sound used as the song |
| `refs/` | `auto.mjs`; `reference_image` | official character pictures and real people's photos (`<slug>.png` or `.jpg`); real pictures the planner fetched |
| `reference/` | `auto.mjs` | frames of the video to follow or the look video: `ref-NN.jpg`, `shots-NN.jpg`, `reference.txt` (2.12) |
| `prompt.md`, `mcp.json` | launcher | the planner's first message (1.5.2); the tool server's settings (3.5) |
| `lyrics-ids.vtt`, `lyrics.json` | `lyric-ids.py` | the song's lines as ids `[L1]…` with their times; id to words |
| `manifest.json`, `code.diff` | `manifest.py`, render-all | how the run was made (1.5.8); the uncommitted code it ran with |
| `t0`, `t1`, `t-maps`, `t2` | launcher | Unix times: session start, session end, map shots done, launcher done |
| `transcript.jsonl`, `stderr.txt` | the planner's `claude -p` | the whole session as stream-json; the CLI's errors |
| `planner-hooks.log`, `planner-stop.state.json` | hooks | each hook decision; the stop hook's state |
| `PLAN.md`, `NOTES.md` | planner | script and shot list; what was made and why |
| `prompts/clipN.txt` | planner, or `build-edit.mjs` | one prompt per H3 clip (1.5.4) |
| `EDIT.json`, `EDIT.built.json` | planner; `build-edit.mjs` | a montage's edit list (1.5.3); the record of its last clean build |
| `render.json` | planner or `build-edit.mjs`; the launcher writes `ratio` | the render list (1.5.5) |
| `soundtrack/` | `make_soundtrack` | 1.5.6 |
| `storyboard/NN-<name>.png` | `storyboard` | Nano Banana frames: designs, places, pinned pictures |
| `images/<name>.png` | `image` | Nano Banana stills and edits (product screens, state stills, cut-outs) |
| `stills/<name>.png` | `still` | type stills and end cards drawn in HTML (exact text) |
| `shots/` | `screenshot` | product site screenshots, `logo.png`, `logo-mark.svg`, `logo-word.svg`, the app icon |
| `footage/` | `user_video`, `build-edit.mjs`, render-all | segments `<stem>-<start>s-<length>s.mp4` (video only, at most 1080 rows, ending at the source's next scene cut), downloads `<stem>-src.mp4`, contact sheets, `edit-cuts.json`, framed crops |
| `code/<name>/` | `code_clip` | a code clip's page, its mp4 and a contact sheet |
| `maps/` | `map_shots`, `maps.mjs` | 1.5.7 and section 6 |
| `FAILED.json` | any tool, on a failure the film cannot go on without | `{tool, error, at}`; the launcher ends the session and nothing renders |
| `prompts-unretimed/` | `lyric-retime.py` | the prompts before lyric rows were moved to their sung times |
| `prompts-lyrics/`, `prompts-tagged/` | render-all | prompts with lyric words filled in; swap prompts with the H3 node's tags. These, not `prompts/`, go to H3 when they exist |
| `render/refs/` | render-all | launch motion clips cut to their proven span |
| `render-gpu/` | render-all | `<id>.mp4` (H3's clip), `<id>.json` (the clip as handed to `comfy_r2v.py`), `<id>.key` (the reuse key), `zoom/`, `swap/`, `chain/` (pictures the renderer pinned), `*.stale-*` (clips whose inputs changed) |
| `render-code/` | render-all | code and footage clips conformed to the film |
| `render-<id>.log` | render-all | each clip's log; its last line gives the GPU seconds |
| `speech-words.json` | render-all | the soundtrack's words, for speech captions |
| `spend.json` | render-all | `{spent, cap}`, the render cap's estimate (priced as on fal, not the real cost) |
| `final-gpu.mp4`, `final-gpu.mp4.captionN.png` | join | the film; each caption drawn as a picture |

Every picture a tool makes has a small copy beside it, `<name>.view.jpg` (at most 1216 px on its long side), which the planner looks at; prompts and render.json name the full file. With `NOVID=1` the prompts go to `render-novid/`, the clips to `render-gpu-novid/` and the film to `final-novid.mp4`.

Outside the run folder: `agent/runs/_auto/` holds `<name>.txt` (the brief), `<name>.log` (planner and render output), `<name>.out` (runs started by `run-v3.sh`), `catalogue.json` (the cached style list), `claude-calls.jsonl` (one line per producer call), `files/` (fetched videos and songs, `.lrc` lyrics, `.vtt` timings, copies of files whose paths have odd characters, `.youtube-blocked`) and `stt-*.json` (transcripts). Video studies are in `agent/runs/_style-builds/kits/`, Nano Banana pictures in `agent/artcache/`. A film can also write into the repo itself: a studied look adds `agent/web/app/styles/cards/<id>.md` and `refs/<id>/pool/`, and a launch film rewrites `agent/h3film/library/CASTABLE-index.md`. The planner works in `~/h3-claude/h3film-<name>` (an empty folder) and the producer in `<os temp>/h3-claude-ask`; neither is cleaned up.

### 1.5 The files passed between steps

#### 1.5.1 `brief.txt` (producer → planner)

Plain English, in this order:

```
<the producer's brief>

Style: the <Name> style (card: agent/web/app/styles/cards/<id>.md). Use case: skills/h3-film/usecases/<file>.md. <the section's hard rules> The user attached <paths>: look at each before planning. The film's video footage: <absolute paths>: <footage_use, or "use it in the film">. <official pictures line> <on the swap path: the real people's photos line> Any narration and on-screen words in <Language>. <aspect>.
References the user attached (skills/h3-film/REFERENCES.md says how to use each kind):
- @<Name> (<kind>): <files>. <its role>
Length: <N> s exactly, set for this run: make_soundtrack's duration is <N>, and the film is the soundtrack's length.
```

- The producer's brief: the user's words verbatim in quotes first, then what they mean as researched, the point, where it takes place, who is on screen and who speaks, the real media by path, and for a factual film 4 to 6 certain facts (with `--duration N`, about max(2, round(N/7))). Never the look, the edit's treatment, jokes or invented claims (2.6).
- `Use case: none.` when the section has no file.
- Parts that do not apply are left out. Every path of the user's pictures and sound files is replaced by its `attached/` copy, and every uploaded video that is not footage by words (2.11), because the launcher takes every video path in a brief as footage.
- Paths are absolute. A file whose path has characters other than `A-Za-z0-9_./-` is copied to `agent/runs/_auto/files/` first, because the launcher's patterns match only plain paths.
- The language sentence appears only when the language is not English. The aspect is the last word of the Style line.

What later steps read out of this text (keep these strings, or replace them with fields in a rebuild):

| Reader | What it looks for |
|---|---|
| `agent/h3-film-agy.sh` | the card path; the use-case path or "Use case: none"; video paths (footage); `.vtt` paths; a line starting `References the user attached`; every "16:9" (replaced by the frame) |
| `research/h3/tools-maps.mjs` | the whole brief, passed to the map stages |

An example of the code's part (a first-person movie recap Short, 60 s, 9:16; paths shortened):

```
Style: the Miles Morales First-Person Recap style (card: agent/web/app/styles/cards/miles-morales-first-person-2.md). Use case: skills/h3-film/usecases/fan-edit-uc.md. The film's video footage: /…/agent/runs/_auto/files/fetched-3v9Pfg4Ocbg.mp4, /…/fetched-5XnGKA75dtI.mp4: use it in the film. 9:16.
Length: 60 s exactly, set for this run: make_soundtrack's duration is 60, and the film is the soundtrack's length.
```

#### 1.5.2 `prompt.md` (launcher → planner)

The planner's whole first user message, on stdin:

```
THIS FILM'S BRIEF (repeated at the end): <brief>

<frame note, when the frame is not 16:9: how to compose for it, whatever any file below says>

<recovery paragraph: which pasted files and PLAN.md to reopen after a context compaction>

<skill: SKILL-gemini.md whole (launch) | its lines from the "# " heading to the first "## " heading (painted) | one sentence (minimal)>
===== END OF SKILL =====
<run lines: no Skill tool and no Bash; relative paths are relative to the repo; the run folder ("write everything here");
 the render budget; for painted films the map-shot rule>
===== FILE <absolute path> =====
<each pasted file, whole>
===== END OF FILES =====
<note for this kind of film (3.4); the lyric-id rules when lyrics.json exists>
===== FILE …/skills/h3-film/FOOTAGE.md =====          (only with footage)
…
===== END OF FOOTAGE.md =====
This brief attaches the user's own video: <paths>. FOOTAGE.md above decides how this film uses it. <the EDIT.json note>

BRIEF:
<brief>
===== END OF PROMPT =====
```

Then the line "(Your working folder is not the repo: a relative path in the files above is relative to <repo>.)". When `reference/` holds frame sheets (a film that follows a video, or takes its look from a linked or uploaded one), `reference/reference.txt` follows, and the sheets ride in the same message as pictures. With a frame other than 16:9, every line that states a film's aspect in the pasted files (the template's "Software launch film, 16:9,", "SHOTS (16:9,", `"ratio": "16:9"`, the use cases' defaults) is rewritten to the frame. With the write hook on, the skill's "call check_prompt after each prompt" becomes "each prompt is checked automatically as you write it". The launcher stops if `prompt.md` is over 185,000 bytes. Real sizes in this repo's 10-12 runs: painted films 40 to 107 KB, launch films 123 to 148 KB.

#### 1.5.3 `EDIT.json` (planner → `build-edit.mjs`), montage edits only

A montage (every clip one shot of the user's footage) is written as one edit list. `agent/h3film/build-edit.mjs` writes the clip prompts and `render.json` from it, word for word, on every write (the write hook runs it). Before this, 65-85% of each montage prompt was one template copied 14 to 38 times; the five edits of 10-10 rebuilt byte-identical from their edit lists (87 of 87 clips), and planning an anime music video cost 33% less.

```json
{
  "ratio": "9:16",
  "template": "<the clip prompt once, with {name} blanks where shots differ>",
  "fit": "whole",
  "captions": [ … as in render.json … ],
  "shots": [
    { "segment": "footage/c01-23.10s-1.55s.mp4", "span": 1.25, "clean": true },
    { "segment": { "from": "<source video>", "start": 10.7, "as_edited": false }, "span": 1.04,
      "zoom": { "to": 1.3 }, "frame": { "x": 0.5, "y": 0.4 }, "images": [ "<type still>" ],
      "adds": "one white flash", "rows": "0.0-0.15s — a white flash on the cut.\n0.15-1.04s — Video 1 continues at normal speed." },
    { "span": 1.5, "seconds": 1.8, "prompt": "<a whole prompt of its own>", "pins": [ { "t": 0, "image": "<still>" } ] }
  ]
}
```

- Required: `ratio`; `shots`, each with `span`; `template` unless every H3 shot has its own `prompt`. The soundtrack must exist first.
- One shot per clip, in film order (`clip1`, `clip2`, …). `seconds` defaults to `span + 0.3` for a shot with a segment; a shot with no segment gives its own `seconds` (and usually `prompt` and `pins`: a painted insert).
- Paths may be relative to the run folder; build-edit writes them absolute.
- `segment`: a file `user_video` cut, or `{from, start, as_edited?}`, which build-edit cuts itself at the clip's length with `user_video`'s own `cutSegment()` (cached in `footage/edit-cuts.json`). `as_edited: true` keeps the source's own flash frames and zoom cuts instead of ending at the next scene cut. A source that cuts to another shot inside the span is an error; a segment up to 0.1 s short of its span builds with a note.
- `clean: true`: plays exactly as filmed, no H3; no `images`, `zoom` or `pins`. `fit` (for the whole edit or one shot) reaches only clean shots; `frame` reaches both kinds.
- Blanks: `{seconds}`, `{span}` and `{ratio}` fill themselves; every other `{name}` takes the shot's field of that name. A blank with no value is an error. The template is filled in one pass, so a blank inside a shot's field (a `{span}` inside `rows`) stays as written (11.3).
- Each H3 shot's sound: `soundtrack/part_N.mp3` when there is exactly one part per shot, else `soundtrack/shot_N.mp3`, cut from `soundtrack.mp3` at the shot's start in the film for its render length.
- Output: `prompts/clipN.txt` for every shot that is not clean, `render.json` (`kind: "painted"`, `ratio`, `music`, `captions`, `clips`), and `EDIT.built.json` (`{edit: <the exact EDIT.json text>, files: [...]}`), which the stop hook checks. Problems come back as a list, and no prompt or render.json is written.
- `node agent/h3film/build-edit.mjs <run>` rebuilds by hand; it is deterministic.

#### 1.5.4 `prompts/clipN.txt` (planner → H3)

One plain-text prompt per H3 clip, sent to H3 word for word (no rewriter). Its reference lines name the clip's files by position: `Image N is …` for the Nth path in render.json `images` (1-based), `Video N is …` for `videos`, `Audio 1 is the finished soundtrack: keep it verbatim…` for `audio`. Rows are `<a>-<b>s — <what fills the frame>` in the clip's own seconds, coarse (one decimal); `check-prompt.mjs` and `lyric-retime.py` parse rows of exactly this shape. The rest depends on the kind of clip:

- Painted (`PAINTED.md`): an opening style sentence, the reference lines, the TEXT, MOTION and SETTING lines, `SHOTS (<ratio>, <seconds> s, …)` and its rows, and a `COPY LIST` of exact strings.
- Launch (`skills/h3-film/references/template.txt`): the job line `Software launch film, <ratio>, <seconds> seconds, …`, the reference lines, `THE ROOM` (some cards: `THE SETTING`), `BEAT SHEET` and its rows, `TYPE`, `COPY LIST`, `LINES`, `CONSISTENCY`, `CAMERA & MOTION`, `RENDER`.
- Footage clips follow `FOOTAGE.md`: a style sentence about only what is added on top, then the job line for `Video 1`. Live-action swap clips use MiniMax's own reference layout instead.

Lyric films write ids (`[L3]`, `[L3:1-4]`), never the words. At most 20,000 characters (Magic Hour's cap; the write hook reports a launch prompt's length). The layouts and rules are in 3.10.

#### 1.5.5 `render.json` (planner → render-all)

Written by the planner in one Write after the prompts, or by `build-edit.mjs`. Every path is absolute.

```json
{
  "kind": "painted",
  "ratio": "9:16",
  "music": "<run>/soundtrack/soundtrack.mp3",
  "captions": [ { "speech": true, "place": "middle", "words": 2 } ],
  "clips": [
    { "id": "clip1", "prompt": "<run>/prompts/clip1.txt", "seconds": 8, "span": 7.5,
      "images": ["<run>/storyboard/01-monkey.png", "<run>/storyboard/02-salaryman.png"], "videos": [],
      "audio": "<run>/soundtrack/part_1.mp3", "expansion": "disabled",
      "pins": [ { "t": 0, "image": "<run>/storyboard/03-street-master.png" }, { "t": 2.9, "image": "<run>/storyboard/04-street-door.png" } ] },
    { "id": "clip2", "footage": "<run>/footage/lr-hook-0.00s-1.54s.mp4", "seconds": 1.54, "span": 1.24 },
    { "id": "clip3", "code": "<run>/maps/clip3.mp4", "seconds": 6.73, "span": 6.23 }
  ]
}
```

Top level:

| Field | Meaning | Read by |
|---|---|---|
| `kind` | `"painted"` for every film but launch films (launch planners leave it out) | render-all and the stop hook: a film that is not painted and has no footage gets the launch row check (3.6) |
| `ratio` | the film's frame (default 16:9); the launcher overwrites it with the run's frame when that is not 16:9 | render size, zoom and frame crops, the swapped frame's shape |
| `music` | absolute path of `soundtrack/soundtrack.mp3` | the join (the film's only sound); speech captions |
| `captions` | optional list (4.12) | render-all, join |
| `chain` | legacy, no current instruction writes it: clips render one after another, each given the previous clip's last 3 s | render-all |
| `clips` | in film order; together they tile the soundtrack from 0 | render-all |

Each clip is one of three things:

- an H3 clip: it has `prompt`;
- a footage clip played as filmed: `{id, footage, seconds, span}` plus optional `fit`, `frame`, `zoom`; no prompt, images, videos or audio;
- a code or map clip: `{id, code, seconds, span}`; no prompt, images, videos or audio.

Clip fields:

| Field | Meaning |
|---|---|
| `id` | `clipN`; names every file render-all makes for the clip |
| `prompt` | absolute path of `prompts/<id>.txt` |
| `span` | the seconds of the film this clip fills, equal to its soundtrack part's length. The join keeps exactly these frames |
| `seconds` | the render length. Planners write `ceil(span + 0.3)`, at least 5 (`PAINTED.md`, `SKILL-gemini.md`; 2 to 15 for a footage clip, `FOOTAGE.md`); `build-edit.mjs` writes `span + 0.3`. render-all then asks for at most `span + 0.3`, exactly that for a one-shot footage clip, and H3's smallest length for a zoom shot (5.2 step 3); H3 rounds up to its frame steps (1.6) |
| `images` | absolute paths in Image order (`Image 1` first); at most 9 (the node's `ref_image_0` to `_8`) |
| `videos` | absolute paths in Video order; at most 3 (`ref_video_0` to `_2`), 15 s in all by the skills' rule (fal's limit; nothing checks it on Modal). A path containing `/footage/` is the user's footage |
| `audio` | absolute path of `soundtrack/part_N.mp3` (a montage shot: `part_N.mp3` or `shot_N.mp3`, 1.5.3), this clip's slice of the finished soundtrack (Audio 1) |
| `pins` | `[{"t": <clip seconds>, "image": <path>}]` or `[{"t", "video": <path>, "at": <seconds in it>}]`: the picture fixed at that moment. A pinned still is not also listed in `images`, and no row calls it "Image N" |
| `zoom` | footage shots: `{"to": 1.6}` pushes in from the frame as filmed; `{"from": 1.5, "to": 1}` pulls back; `{"from": 1.4, "to": 1.4}` holds a tighter framing. On a footage shot that also attaches pictures (a swap or restyle), `{"to": 2}` holds 2x for the whole shot and `{"from": 1, "to": 2}` pushes in (5.2 step 4c) |
| `frame` | footage shots wider or taller than the film: `{"x", "y"}`, the centre of the film's frame on the shot, as shares of its width and height (default 0.5) |
| `fit` | `"whole"`: a footage clip keeps its whole picture on black instead of filling the frame (code clips are always fitted) |
| `footage` | absolute path of a clean segment |
| `code` | absolute path of a code clip's or map clip's mp4 |
| `swap` | `true`: a live-action swap clip (5.2 step 4d); only `FOOTAGE-swap.md` asks for it. A prompt in MiniMax's swap layout without the flag is an ordinary clip |
| `seed` | a fixed render seed, for A/B tests only |
| `expansion` | `"disabled"`, kept from the fal days; on Modal it only enters the reuse key (no rewriter runs) |
| `first`, `last` | frame mode: refused on Modal ("pin those frames instead") |

Rules no code checks, which the film depends on:

- The clips tile the soundtrack: the sum of `span` is the soundtrack's length, and each H3 clip's `span` equals its part's length as `make_soundtrack` returned it (a merged map entry covers several parts). The join cuts the picture by spans and plays the soundtrack straight through, so a mismatch puts every later cut out of sync. From 09-28 to 10-10 launch planners gave `make_soundtrack` their render seconds instead of their spans: the picture ran up to 1.2 s ahead at each cut and 2.4-3.9 s by the end, and the closing line was cut off.
- `images`, `videos` and `audio` hold exactly what the prompt's Image, Video and Audio lines name, in that order.

#### 1.5.6 `soundtrack/` (make_soundtrack → planner, render-all, join)

The planner builds the whole soundtrack in one call, before any prompt, and every row follows the times it returns.

| File | What it is |
|---|---|
| `soundtrack.mp3` | the finished mix, `duration` s (a whole number, 4 to 120), 192 kbps, programme loudness -16 LUFS |
| `part_N.mp3` | clip N's slice: from the sum of the earlier parts, for this part's length |
| `vo-N.mp3` | line N's read (N counts from 1 in call order), or one cut of real audio covering a run of lines from one recording |
| `fx-N.mp3` | sound effect N |
| `music.mp3` (+ `music.mp3.music.json`), `bed.wav` | generated music and its beat analysis; the music bed after level, ducking and fade |
| `song.json` | `{song, songStart, duration}` when a song or the user's music plays; lyric timing and lyric captions map song times to film times with it |
| `soundtrack.json` | the tool's whole answer; written only for painted films (`MAPS=1`) |
| `shot_N.mp3` | a montage shot's slice, cut by `build-edit.mjs` |

The answer (the content of `soundtrack.json`):

```json
{
  "file": "<run>/soundtrack/soundtrack.mp3", "duration": 30, "music": "generated", "bpm": null,
  "beat_grid": { "bpm": 0, "beats": [], "downbeats": [], "energy": [{ "label": "high", "start": 0, "end": 4 }] },
  "beat_grid_note": "…", "music_start": 12.3, "songStart": 0, "note": "…",
  "lines": [ { "text": "…", "speaker": "Ishibashi", "at": 0.3, "end": 2.59, "requested_at": 0.3, "clip": 1, "clip_at": 0.3, "clip_end": 2.59 } ],
  "effects": [ { "sound": "a gas flame flaring up…", "at": 5.8, "end": 6.8 } ],
  "parts": [ { "file": "<run>/soundtrack/part_1.mp3", "start": 0, "duration": 7.5 } ],
  "seams": "FINAL. Clip spans: 7.5 / 6 / 8.39 / 8.11 s …"
}
```

| Field | When | Meaning |
|---|---|---|
| `file`, `duration`, `parts` | always | the mix; the film's length; one `{file, start, duration}` per clip |
| `music` | always | `"generated"`, a library name, the user's file path, `"song"`, or absent (voices only) |
| `bpm` | beds | the tempo from a library or user file's beat file; `null` for generated music (its tempo is in `beat_grid.bpm`) |
| `music_start` / `songStart` | the user's music as the bed / song mode | where the film starts in that file |
| `beat_grid`, `beat_grid_note` | when music plays and its analysis worked | `{bpm, beats, downbeats, energy}` in film seconds |
| `lines` | always | each line as placed: `text`, one of `voice` / `speaker` / `from`, `at`, `end`, `requested_at`; on painted films also `clip` (1-based), `clip_at` and `clip_end` (the line in its clip's own seconds, so rows need no subtraction) |
| `effects` | with effects | `{sound, at, end}` each |
| `seams` | painted, more than one clip, any lines | "FINAL. Clip spans: …": the spans to use (`seconds` = ceil(span + 0.3)), rows from `clip_at`/`clip_end`, do not call again |
| `note` | sometimes | lyric window moved, late lyric lines, seams off the beat, a silent file |

A song call returns `{file, duration, music: "song", songStart, note?, beat_grid?, lines: [], parts}`.

#### 1.5.7 `maps/` (map_shots → launcher, render-all)

`request.json`, `soundtrack.json` (the read the map is timed to), `pid`, `maps.log`, `skeleton.json`, `direction/` (aligned words in `vo/`, `beats.json`, `beats.forked-from.json`, `choreo/`, `kit_film/`), `film/` (the map pages), `logs/` (stage sessions), `.direction-done`, `.choreo-done`, `clipN.mp4`, `clipN-sheet.jpg`, and finally `done.json` (`clips`, `sections`, `minutes`, `model`, `stages`, `stages_usd`) or `failed.json` (`{error}`). The launcher waits for one of the last two; render-all refuses the film on `failed.json` and needs every `code` mp4. Section 6 has the details.

#### 1.5.8 `manifest.json` (launcher, render-all)

- First block, written at launch by `agent/h3film/manifest.py launch`: `run`, `started`, `repo`, `git` (`sha`, `dirty`, `diff_sha1`, `untracked`), `agy` (left from the Antigravity planner; its values mean nothing now), `flags` (only these, when set: `MODEL PLANNER CEFFORT LAUNCH MINIMAL EXAMPLES SKILL SEAL INLINE PINLINE RESUME RATIO FRESH ROUND H3_ACCURACY H3_BUDGET_USD H3_CALL_LIMIT_S VOICE_PROVIDER NANO_BANANA_MODEL ELEVENLABS_TTS_MODEL ELEVENLABS_MUSIC_MODEL AGY_CLI_DISABLE_AUTO_UPDATE`; never keys), `route` (`card`, `card_sha1`, `use_case`, `painted`), `models` (`planner`, `image`, `voice`, `tts_elevenlabs`, `music`, `video: minimax-h3`), `prompt` (`bytes`, `sha1`, the pasted files and their sizes).
- `session`, after the planner: `ended`, `agy_exit` (the planner's exit code), `conversation_id`, `planning_min`, `model_turns`, `tool_calls`, `still_working_repeats` (how many "STILL WORKING" answers), `tools` (calls per tool), `status`, `usage`, `num_turns`, `cost_usd` (as the session's result line reports it), `prompt_received_whole` (always null for Claude), `failed`, `render_json`.
- `render`, after the render: `at`, `backend: "modal"`, `rows`, `novid`, `final`, `size`, and per clip `id`, `file`, `code`, `footage`, `prompt`, `prompt_chars`, `images` and `videos` (counts), `audio` (true or false), `seconds`, `span`, `key`, `seed` (read back from the clip's embedded graph).
- Not recorded: `H3_DURATION`, `GPU_ROWS` (only `render.rows`), the producer's call (in `agent/runs/_auto/claude-calls.jsonl`), the map stages' cost (in `maps/done.json`).

#### 1.5.9 `final-gpu.mp4`

H.264 (CRF 18, yuv420p) with AAC sound. Size: H3's render size for the film's frame and tier (1.6). A film with map shots takes the map clips' size instead: 1080x1920 for 9:16, else 1920x1080, so a film in another frame is stretched to 16:9 (section 11). Frame rate: 24. A film with no H3 clip keeps its first clip's own rate (23.976 for the footage in the tests). Length: the sum of the spans, or the set length within +0.45 s. Captions and lyrics are burned in. The repo does not scale the film up to 720p or 1080p.

### 1.6 Conventions every step relies on

**Paths carry meaning:**

| Path contains | Means | Used by |
|---|---|---|
| `/footage/` | the user's footage: sent filling the frame (fitted when the clip also has stills), at the render's size, or at most 360 rows (480 at 720p and up) when the clip has no stills; its own frames pinned, framed and zoomed | render-all, `comfy_r2v.py` |
| `<run>/attached/` | the user's own files (a real photo for a swap; the user's music bed) | render-all, `soundtrack.mjs`, the tools |
| `<run>/maps/` | a map clip (the film takes its size) | render-all, the stop hook |
| `<run>/reference/` | frames of the video to follow: never attached to a clip | the stop hook |
| `agent/h3film/library/proven/` | a launch motion clip with a proven cut | render-all |

**Numbering.** `Image N`, `Video N`, `Audio 1` in a prompt are positions in render.json `images`, `videos`, `audio` (1-based). The H3 node itself labels references in request order (pictures, then videos, then sound) as `<Picture N>`, `<Video N>`, `<Audio N>`; render-all converts only swap clips' prompts to those tags.

**Time.**

- Film seconds: soundtrack times, `captions`, `make_soundtrack` `at`, part starts.
- Clip seconds: rows, pins (`t`), `clip_at` and `clip_end`.
- The film's grid: 24 frames a second (a film with no H3 clip: its first clip's own rate); a clip keeps `round(end × 24) − round(start × 24)` frames, where start and end are running sums of the spans.
- H3's frame steps: a render has 17k+5 frames (at least 5), the smallest such count at or above `round(seconds × 24)`.
- render-all asks for at most 0.3 s past a clip's span (5.2 step 3), and H3 renders up to its next frame step. The last event of a clip should end at least 0.7 s before its span ends, or H3 drops it.
- A clip is at most 15 s; the soundtrack 4 to 120 s.

**Render sizes.** The tier sets the rows: 480 (default), 704 (`GPU_ROWS=704`, the 720p tier) or 800 (`GPU_ROWS=800`, the 1080p tier). 16:9 is 832x480, 1248x704 or 1408x800; 9:16 turns them. Any other frame keeps the 16:9 tier's pixel count with each side rounded to 32: at 480 rows 1:1 640x640, 4:5 576x704, 3:4 544x736, 4:3 736x544, 21:9 960x416 (table in 5.7). Pictures are drawn larger than the render. Type stills and end cards (the `still` tool) are 4032x2268 at 16:9, the same pixel count in other frames. Nano Banana pictures come back at 1K (the `image` tool can ask for 2K). The H3 node encodes reference pictures at the render's size (`ref_image_size: match`), and `comfy_r2v.py` scales and crops each pin to it.

### 1.7 Locks, time-outs and failures

| What | Value |
|---|---|
| Film launches per machine | one at a time (`/tmp/h3-launch.lock`, held until the run's `prompt.md` exists plus 12 s; a lock over 60 s old whose owner is gone is taken over) |
| Scene detection in video studies (`kit.mjs`) per machine | one at a time (`/tmp/h3-kit-cuts.lock`) |
| Producer call | killed after 30 min |
| A tool call | answers "STILL WORKING: call again with the same arguments" after 1,750 s (`H3_CALL_LIMIT_S`); the repeat waits on the same job. Claude Code's MCP time-out is set to 30 min |
| Planner session | no time limit |
| Planner prompt | at most 185,000 bytes |
| Modal | 3,600 s per call; idle GPUs stop after 30 s; up to 40 containers in code, 10 on Modal's Starter plan |
| Render tries | 3 (only missing clips render again) |
| Map shots | the launcher waits as long as `maps.mjs` lives |

How a failure surfaces:

- Before planning, `auto.mjs` stops with exit 1 when YouTube blocks a download during the research, or when no style fits and the producer studied none. A request the producer refuses, and a lyric video with no song, print why and exit 0 with no film (section 2).
- A tool failure the film cannot do without (a voice, the music, a still: any provider error that is not a content refusal, such as 401, 402, 404, a 403 naming a lock, top-up, balance, credit, billing or exhaustion, or an error that outlasts its retries) writes `FAILED.json` and answers "RUN STOPPED … end the session now". The launcher ends the session and exits 1, and render-all refuses. `auto.mjs` prints `no render.json` (or `RENDER FAILED` when render.json was already written) and exits 1. A film made without its voice or a still is worse than no film.
- A refused picture (a client error that is not an account error, or no image back) is tried again at once, up to 4 tries. The tool then answers with fal's own reason and a hint (use the character's official picture from `reference_image`; keep names out of picture prompts), and the planner changes its request. It does not stop the film.
- A planner that ends without `render.json`: `no render.json`, exit 1.
- Map shots that fail: `maps/failed.json`; nothing renders, and there is no fallback to H3-painted maps.
- A clip render that fails: render-all stops; `auto.mjs` tries twice more, and finished clips are reused.

### 1.8 Where everything is

The tree is the lab's own, cut down to what makes a film. Nothing moved, so every path written into prompts and example files still works.

| Path | What it holds |
|---|---|
| `film`, `package.json`, `requirements.txt`, `.env.example` | the one command, the setup script, the Python packages, every setting |
| `agent/h3film/auto.mjs` | step 1, the producer, and the whole run from request to mp4 |
| `agent/h3film/claude.mjs`, `kit.mjs`, `fetch.mjs` | starts the producer's Claude session; studies a video (frame sheets, cuts, words, music); downloads footage, songs and lyrics |
| `agent/h3-film-agy.sh`, `agent/h3film/launch-locked.sh`, `with-pictures.mjs`, `manifest.py`, `reading-report.py`, `lyric-ids.py` | step 2, the planner launcher (it starts Claude; the name is left from the Gemini planner it once started), its lock, the first message with pictures, the run record, the reading report, lyric ids |
| `agent/h3film/planner-hooks.json`, `planner-check.mjs`, `planner-stop.mjs`, `check-prompt.mjs`, `build-edit.mjs`, `expand-prompts.mjs` | the planner's hooks: checks on launch clip prompts, montage edits built from EDIT.json, the stop when the film is whole (`expand-prompts.mjs` is dormant) |
| `agent/h3film/lyric-retime.py` | step 3, lyric rows moved to their sung times |
| `agent/h3film/render-all.mjs`, `boxed-check.py`, `planner-cost.py` | step 4, render.json to one H3 job per clip on Modal; the black-bar check; one run's cost |
| `agent/h3film/join.mjs`, `still.mjs` | step 5, the join with captions and lyrics; type stills and end cards in HTML |
| `assets/fonts/` | Inter Light, Regular and Bold (SIL Open Font License, `Inter-LICENSE.txt`): the caption and frame-sheet font where the macOS fonts are missing |
| `agent/h3film/library/`, `exemplars/`, `RULES.md` | launch components with tested prompt rows, whole example films, rules learned on H3 |
| `agent/h3film/maps.mjs`, `agent/v2/` | the map engine: the stages map films run (direction, choreography, the map build), the map template, its tools and data |
| `agent/h3film/*.tsv`, `run-v3.sh` | the test requests and the batch runner |
| `agent/web/app/styles/` | the style menu (`menu.ts`, `presets.ts`), the style cards (`cards/`), their sample frames and example films (`refs/`) |
| `agent/scorecard/ratings.json`, `agent/runs/_styles-log/best-takes.json` | project-owner's scores of the test films; the best take of 49 styles. The producer uses both to rank styles and stops without them |
| `agent/music/` | five library music beds with beat files. The tool server will not start without this folder |
| `agent/refs/` | logo packs of 17 products |
| `agent/runs/` | output, one folder per film; also the six example runs pasted into some films |
| `research/h3/mcp.mjs`, `tools-film.mjs`, `tools-footage.mjs`, `tools-codeshot.mjs`, `tools-maps.mjs`, `soundtrack.mjs`, `h3.mjs` | the tool server the planner calls (`h3.mjs` is the fal and MiniMax client of the unused `generate_video` tool) |
| `research/h3/voices/` | voice samples for the cloner, Magic Hour's preset list (`mh-presets.json`), the native Hindi and Japanese ElevenLabs voices (`native.json`) |
| `research/h3/codeshot/` | the libraries shots drawn in code use (d3, GSAP, three.js, world maps), copied into each shot |
| `research/h3/modal_h3.py`, `research/h3/runpod/` | H3 on Modal: the ComfyUI graph (`r2v_v1.json`) and the job builder (`comfy_r2v.py`). The folder's name is left from the RunPod pods it first served |
| `research/h3/prompts/orchids-reveal/GUIDE.md` | the H3 prompt guide that `references/translate.md`, pasted into launch films, points to |
| `research/tools/analyze_music.py` | beat and loudness analysis of a song |
| `ingest/<film>/run/`, `research/lab/run/` | motion clips cut from real launch films |
| `ingest/orchids/` | the template every default end card is drawn from |
| `skills/h3-film/` | the planner's instructions (3.8) |
| `batches/` | the test films and their records (8.4) |
| `tools/pages/`, `tools/build-batches.py` | builders of the pages linked above and of `batches/` |
| `skills/h3-film/build-refs.mjs`, `agent/h3film/library/build-castable.mjs`, `agent/h3film/library/proven/proof.mjs`, `agent/v2/tools/map_basemap.py`, `agent/v2/tools/map_prep.py` | upkeep scripts, run by hand, never by a film: the planner's reference indexes (`build-refs.mjs` also reads the lab's `framework/components/`, which is not in this repo); the launch component list and its rows; one component's test render on fal (paid); the satellite pictures; the map gazetteer |

## 2. The producer

The producer turns one request into one brief for the planner. It is one Claude session with code around it. The code studies the user's videos and links before the session, gives the session a fixed prompt and a JSON answer schema, then turns the answer into the brief, copies the user's files into the run folder and starts the planner. All the prompt text lives in `agent/h3film/auto.mjs` under the constants `ROLE`, `USER`, `RULES` (with `LINK`, `DRY`, `REFS` and the style list `LIST` folded in), `UPNOTE`, `SEEN`, the answer schema `PROD` and the section rules `HARD`. Line numbers drift; those names are the stable way to find things.

### 2.1 Files

| File | Job |
|---|---|
| `film` | the command users run (zsh, needs `/bin/zsh`) |
| `agent/h3film/auto.mjs` | the producer step and the whole run: producer, planner, render |
| `agent/h3film/claude.mjs` | starts one Claude Code session in print mode (`claude -p`) and returns its JSON answer |
| `agent/h3film/kit.mjs` | studies a video the model cannot watch: frame sheets, measured cuts, words heard, music, the sound a platform credits |
| `agent/h3film/fetch.mjs` | the four commands the session runs to get real media: `search`, `get`, `song`, `link` |
| `research/h3/tools-footage.mjs` | `ytSearch()` (YouTube search with no API key) and `transcript()` (speech to text, or a song's synced lyrics), used by the files above and by the planner's tools |
| `agent/h3film/launch-locked.sh` | starts one planner at a time |

It reads `agent/web/app/styles/menu.ts`, `presets.ts` and `cards/*.md` (the style list), `agent/scorecard/ratings.json` and `agent/runs/_styles-log/best-takes.json` (style scores; `auto.mjs` stops without them), and the header lines of `skills/h3-film/usecases/*.md`. It never reads a card's body or a use-case file's body: the planner does.

### 2.2 Running it

```
./film "<request as typed>" [files…] [--aspect 9:16] [--duration 30] [--name <run>] [--url example.com]
       [--style <card id>] [--ref [category:]@Name=file[,file…]]… [--dry] [--plan]
```

`film` stops if `.env.local` is missing, loads it, unsets every `CLAUDE*` variable inherited from the shell (a Claude Code session that starts a film would otherwise pass its own settings to the film's sessions; `auto.mjs` reads `CLAUDE_BIN` and the like back from `.env.local`), sets `H3_BUDGET_USD=20` unless set (render-all's own default of 5 refuses longer films), and runs `node agent/h3film/auto.mjs` with the same arguments. `auto.mjs` also loads `.env.local` itself (a value already in the environment wins), so it runs without `film`, but then nothing clears the `CLAUDE*` variables.

| Argument | What it does |
|---|---|
| first plain argument | the request, exactly as typed, any language. Every `http(s)://` link in it is studied before the session starts |
| later plain arguments | files. Each must exist (else exit 1). Their extension decides their kind (below) |
| `--aspect` | 16:9, 9:16, 1:1, 4:5, 3:4, 4:3 or 21:9 (anything else: exit 1). Without it the producer picks: the request's words (vertical, TikTok, Reels, Shorts: 9:16; square: 1:1), some sections' own default, else 16:9 |
| `--duration N` | the film's exact length in whole seconds. `make_soundtrack` then refuses any other length (it takes 4 to 120) and the join makes the file N to N + 0.45 s long. It also sets how many facts the brief asks for: about max(2, round(N/7)) instead of 4 to 6. Tested at 10 to 60 s. Without it the planner takes the length from the use case and the card |
| `--name` | the run folder `agent/runs/h3film-<name>/`. Default `auto-<card>-<first six words of the producer's title>`. An existing folder gets `-2`, `-3` …: a run folder is never reused |
| `--url` | the product's web address, for launch films. The producer can also take one from the request (its `url` field); `--url` wins |
| `--style <card id>` | forces the style; it must be a card on the menu (else exit 1). The producer then picks only among the sections that list that style, and is not asked to study a look |
| `--ref [category:]@Name=file[,file…]` | an upload as Magic Hour's reference library has it (2.5). Repeatable |
| `--dry` | the producer only; prints its pick and the brief, then stops (details below) |
| `--plan` | the producer and the planner, then stops before rendering |
| `--catalogue` (as the request) | prints every style with its section, score and planner mode, then exits. No model call; it may rebuild `agent/runs/_auto/catalogue.json` |

Files by extension (`kind()` in `auto.mjs`):

| Extension | Becomes |
|---|---|
| .mp3 .wav .m4a .aac .flac .ogg | a sound reference with no category, its @Name from its file name |
| .svg .png .jpg .jpeg .webp .gif | a picture reference with no category, its @Name from its file name. An SVG is only ever a logo |
| .mp4 .mov .webm .m4v | an uploaded video: studied like a link, then the producer decides what it is (2.11) |
| .vtt | timed lyrics, used only when the film is a lyric video |
| anything else | passed on as "The user attached <path>: look at each before planning." (HEIC counts here: Magic Hour's upload converts HEIC to JPEG, so do that before this step) |

Output: the pick (`brief` (first 600 characters), `footage`, `song`, `new look studied`, `use case`, `style`, `aspect … language`, `why`, `run`, `note`, `upload` lines), then `--- brief` and the whole brief, then `planning and rendering (≈30 min); log …`, and last one of `h3film-<name>: done, <run>/final-gpu.mp4`, `h3film-<name>: RENDER FAILED`, `h3film-<name>: no render.json`, or with `--plan` `h3film-<name>: planned (no render): node agent/h3film/render-all.mjs <run>`.

Exit codes: 1 when at the end the film (with `--plan`: `render.json`) does not exist, and on every early stop (bad arguments, a missing @Name, a YouTube bot-check block, a session with no answer, "no style fits and the producer studied none"). 0 when the film exists, on `--dry`, when the producer refuses the request (its one-sentence reason is printed), and when a lyric video has no song (it prints how to add one): those two make no film, but they are answers to the user, not crashes.

`--dry` still studies every link and uploaded video (a yt-dlp download of the first 150 s, ElevenLabs speech to text, music analysis), still transcribes uploaded sound files, and the session still searches the web; it is told "this is a dry run: search, but do not get or download anything" (an instruction, not enforced). It skips the character pictures and writes no run folder, but a studied look still writes its card, and a lyric video with no `.vtt` still gets one. The producer's Claude call cost about $0.09-0.12 on 10-10.

`--plan` skips two things a full run does before rendering: the lyric retiming (`python3 agent/h3film/lyric-retime.py <run> 0`, for a film whose prompts put sung lines on screen) and passing `H3_DURATION=<N>` to render-all. Do both when rendering a `--plan` run by hand (7.4).

### 2.3 What `auto.mjs` does, in order

1. Reads the arguments, checks `--aspect`, sorts the files by kind.
2. Builds the references (`--ref` items, plain pictures and sound files) and sets the uploaded videos aside.
3. If any `--ref` was given: every `@Name` in the request must name one, else exit 1 ("Missing references").
4. Loads the style list (cached) and the extra use-case files; applies `HIDE_STYLES`.
5. Prepares each reference file for the model: pictures as JPEG, an SVG as its markup, a sound file as the words heard in its first minute.
6. Studies every link in the request and every uploaded video with `kit.mjs` (the larger sheets), all at once.
7. Runs the producer session. If Anthropic's output filter refused the answer, runs it once more.
8. Stops (exit 1) if YouTube blocked a download during the session. Prints the refusal and stops if the producer refused.
9. If the producer picked no style: writes the look it studied as a new card (2.13).
10. Decides what each uploaded video is; adds the footage the session fetched; turns the song into a sound reference (2.11).
11. Applies the session's reading of each reference file (category, kind of sound, logo, screenshot).
12. Settles the section, the card path, the frame and the language; for a lyric video, the song and its timed lyrics.
13. Names the run.
14. Fetches the pictures of named characters and photos of real people (at most 8; 2.10).
15. Assembles the brief (1.5.1, 2.14).
16. Picks the planner's settings: launch, painted or minimal; example films; effort; render rows (1.3).
17. Prints everything. With `--dry`, stops here.
18. Copies the user's pictures and sound files into the run's `attached/`; writes the brief to `agent/runs/_auto/<name>.txt`.
19. For a video the film follows, or the user's own video whose look was studied: writes its shots into the run's `reference/` (2.12).
20. Starts the planner through `launch-locked.sh` and waits (2.12).
21. With `--plan`, stops. Otherwise retimes lyric rows if needed, runs `render-all.mjs` up to 3 times until `final-gpu.mp4` exists, prints the result, and exits 1 if there is no film.

### 2.4 The session

`auto.mjs` calls `claude(prompt, { images, schema: PROD, tools: ['WebSearch', 'WebFetch', 'Bash'], dirs, effort, lean, model })`. `claude.mjs` runs the Claude Code CLI in print mode as a child process and sends the prompt on stdin.

| Setting | Value | Why |
|---|---|---|
| model | `claude-sonnet-5-5` (`PRODUCER_MODEL`) | the same model as the planner. A Gemini producer stopped when Vertex refused every request (10-09); GPT-6.1 Sol was tested as producer and planner and turned down (10-10) |
| effort | `medium` (`PRODUCER_EFFORT`) | the producer has run at medium since it became one session (10-09); no other effort was compared |
| tools | WebSearch, WebFetch, Bash, Read (`--tools` and the same `--allowedTools`; Read is added because there are folders to read) | search, read pages, run the media commands, open pictures and sheets. Every other tool is off |
| folders | `--add-dir` the temporary picture folder and `agent/runs/_style-builds/kits` | Read reaches the user's pictures and every kit's sheets |
| working folder | `<os temp>/h3-claude-ask` | outside the repo, so no `CLAUDE.md` or `AGENTS.md` reaches the session |
| MCP servers | none: `--strict-mcp-config` (`PRODUCER_LEAN`, on unless `0`) | the account's claude.ai connectors and plugins put about 75k tokens of tool definitions into every request; without them a producer request fell from about 98k to 23k tokens and from $0.20-0.30 to $0.09-0.12 (10-10). Picks varied from run to run alike with and without them, except one row (a dinosaur bedtime story) that went to the 2d-cartoon style 5 times of 6 without them against 1 of 6 with them |
| answer | `--json-schema <PROD>`; the result's `structured_output` | the answer is one JSON object, every key required |
| pictures | when there are sheets: `--input-format stream-json --output-format stream-json --verbose`, one user message with the text first and every sheet as a base64 JPEG; else `--output-format json` | the model sees the sheets in its first message |
| sessions | `--no-session-persistence` (`CLAUDE_KEEP=1` keeps them) | |
| environment | `CLAUDE_CODE_PROMPT_CACHE_TTL=5m`, `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`, `CLAUDE_CODE_WEB_SEARCH_FAST_ARG=0` | the first two change billing only (on a subscription Claude Code writes the 1-hour cache at twice the input price; one call's turns are seconds apart; the title call reads the whole prompt to name a session nobody keeps). The fast web search profile returned spam for a format search where the full one returned the real videos and their sound credits (10-11). Claude Code reads fetched pages and runs searches with its small model (Haiku 4.5 on 2.1.285) |
| time limit | the process is killed after 30 minutes | |
| CLI | `CLAUDE_BIN`, else `claude` on PATH | |
| system prompt | none. `PRODUCER_STATIC_FIRST=1` sends `ROLE` and `RULES` as `--append-system-prompt-file` and the request last | off: it changes what the producer reads, to save about 3 cents a film at volume |

An answer with `is_error` or no `structured_output` fails with "claude <model> gave no answer: …". If that message mentions content filtering, the session runs once more with one added line: write no song lyrics or other copyrighted text word for word, refer to sung lines by their times (10-11: the output filter blocked a whole lyric video brief that quoted the song). Every call's cost is appended to `agent/runs/_auto/claude-calls.jsonl` (`at`, `run`, `caller`, `model`, `effort`, `lean`, `cost_usd`, `ms`, `api_ms`, `turns`, `usage`).

If yt-dlp met YouTube's bot check during the session (`agent/runs/_auto/files/.youtube-blocked` newer than the session's start), `auto.mjs` stops with exit 1, rather than letting a painted film stand in for real footage.

To rebuild the session outside Claude Code it needs: web search; page fetch, with pages summarised by a small model as Claude Code does; a way to run the media commands below and return their text; a way to open local pictures (the user's pictures, kit sheets) as image input; images in the first user message; structured output against the `PROD` schema; and prompt caching. The prompt names the media commands as shell command lines; if they become separate tools, change those lines in `RULES` and keep their outputs word for word. The session's shell needs only yt-dlp (with a JavaScript runtime such as deno), ffmpeg, ffprobe, the Python environment and `ELEVENLABS_API_KEY`; today it inherits every key (section 12).

### 2.5 What the session is given

The first user message, in this order: `ROLE`, `USER`, `RULES` (ending with the style list), the studied videos (`SEEN`), and after the text every frame sheet of those videos as an image. `USER`:

```
THE USER TYPED (any language): «<request>»
Their files: <path> (uploaded video 1, @Name); <path> (<kind>) … | only the references below | none. URL given: <url | none>. Frame given: <aspect | none>.
Their reference files (open every picture with the Read tool before deciding anything):
File 1 (@Name, <file name>, category given: <category> | a sound file | no category given): a picture, open <tmp>/1.jpg
File 2 (…), an SVG; its markup:
<up to 20,000 characters>
File 3 (…), a sound file: the words heard in its first minute: "<up to 1,500 characters>" | no words heard in its first minute
```

- Pictures are converted to JPEG, at most 1024 px, pasted on mid grey (128, 128, 128) so a white logo and a black logo both show, in a temporary folder the session may read. They are opened with Read, not attached.
- Sound files go in as the words heard in their first minute (ElevenLabs speech to text): the model cannot hear. No words heard means instrumental.

References (`--ref`): `[category:]@Name=file[,file…]`. Categories: character, object, location, brand (or "brand kit"), moodboard, audio, video; plurals and spaces are accepted. Pictures go with character, object, location, brand and moodboard; sound files with audio; videos with video. One reference may hold several files of one kind. An SVG is accepted only as a brand kit's logo, because the picture tools send PNG or JPEG. The @Name follows Magic Hour's `toReferenceToken` rule: letters, digits, `_` and `-` kept, leading non-letters dropped ("Ref" if nothing is left), a name used twice gets 2, 3. A plain picture or sound file is a reference with no category, named after its file; the session sorts it (its `refs` answer): character (a person or drawn character who could lead the film), object, location, brand (a logo, a brand's product shot, any screenshot of their app or site) or moodboard (pictures sharing one look and no one subject); for a sound file, song, instrumental, speech or mix (a voice over music); and whether each is a logo or a screenshot. A character they attached is the film's lead. `agent/h3film/MH-REFERENCES.md` maps these onto Magic Hour's saved items.

Linked and uploaded videos are studied before the session with the larger sheets (2.8). Every sheet is attached to the first message, and the kit's measured text follows under a header (`THEIR LINKED VIDEO` or `THEIR UPLOADED VIDEO <n> (<path>)`) that says which pictures belong to which video. If all sheets together pass 20 MB, each video sends one sheet in n (one request carries at most 32 MB, and pictures grow by a third as base64). A video that could not be downloaded is left out; its link stays in the request text. With uploads, a note follows: each uploaded video is the footage the film is made of, the video the film follows, the look the film takes, or several at once (a TikTok whose people they replace is both footage and the video to follow). Why the videos are studied first and attached rather than listed (10-10): told to open the sheets of a linked video, two of three producer tries opened only two of three sheets, and one missed the joke's payoff on the last sheet. Uploads are studied like links (10-11) because in Magic Hour's app every reference is an upload, never a link.

### 2.6 The prompt's rules

`ROLE`: "You are the producer of one short film made by an automatic pipeline: the video model MiniMax H3 paints its clips, and a film session plans them from the brief you write. You research what the user wants, gather the real media it needs, pick its style, and write that brief. Answer with the JSON object."

**RESEARCH.**

- A named format (a kind of video people make again and again: a "core" edit, a meme template, a Shorts movie recap, a sports breakdown) is defined by what every video of it repeats: the idea it exists for (who is set against whom, what the payoff is), the caption that stays on screen the whole time (its exact words), the sound on each punchline, reveal or cut (a known meme sound is the real one: its bare "<name> sound effect" video is fetched and given as a file), and its recurring graphic. The producer watches one or two real ones first (`fetch.mjs search`, then `kit.mjs`): the format itself without the request's twist, from channels that make it, the most viewed, never a video about it (a tutorial, a before-and-after or editing demo, a compilation), and gives the best as `copy`. It writes all of these into the brief by name, because the planner cannot see or hear the real ones. When the request names one side of the idea, it casts the other side the way the real ones do. Why (10-11): a podcast edit modelled on a "before vs after" editing demo came out plain.
- It searches the web for every named, slang or niche thing until it knows what it concretely is: how it looks, how it goes (the set; each role with the genders and ages one episode casts together, since an intro reel shows people from many rounds; what happens, in order) and how it sounds. Why (10-10): a producer read a dating show's intro as its cast.
- For a named show, format, meme or trend it reads the real source (Wikipedia, the official page, a real episode's description through `fetch.mjs link`), not search snippets. Why (10-09): a brief built from snippets reversed who pops whose balloon in a dating show.
- When the film shows a real thing people know by sight (a show, an event, a place, a game, a ritual), it runs `kit.mjs` on a real video of it (never a parody, reaction or explainer) and names that kit folder in the brief. The planner opens the same sheets; they never go into a clip. Why (10-09): with text research only, a game-show film invented its set and lines; once the producer watched a real episode, the next take had the real studio, the host's question and the twist ending.
- Links in the request are read first with `fetch.mjs link` (their own title, uploader and song beat any search result). What the user attached is theirs and wins: an attached song is the film's song even when a linked video uses another.
- No song lyrics or other copyrighted text word for word anywhere in the answer; sung lines are named by their times.

The media commands, as the prompt gives them (`<repo>` is the absolute repo path; downloads land in `agent/runs/_auto/files/`):

```
node <repo>/agent/h3film/fetch.mjs search "<query>" [--shorts]   (YouTube: id, seconds, views, title, channel)
node <repo>/agent/h3film/fetch.mjs get <videoId or link>         (downloads it; prints its path)
node <repo>/agent/h3film/fetch.mjs song "<title> <artist>"       (the song's official audio; prints its path)
node <repo>/agent/h3film/fetch.mjs link <url>
node <repo>/agent/h3film/kit.mjs <link or video file>   (frame sheets with times, cuts, cuts per beat, words heard, music)
```

**REAL FOOTAGE.**

- Fetch footage only when the film needs existing footage the user did not attach (an anime's scenes for an AMV, the actual meme clip, a real game or event). Their own linked or uploaded video is the footage when the request changes who or what is in it: the film is an edit of it.
- A format built on real footage (a sports breakdown, a movie or show recap) is made of that real footage, even with no single example to model it on, and is never painted (10-11: two such briefs said to paint it and the films lost what they were).
- Only what was really filmed: something that does not exist yet (a trailer for an unreleased film, a new episode) is painted new, and earlier films' clips are only references (10-11: a trailer for an unreleased film was cut from the earlier films' trailers).
- The person a request replaces with a character is the one the footage is about (the player, the dancer, the one talking), not a narrator or host unless named; everything else the format has stays, now about the character (a breakdown keeps its analyst's voice, captions, arrows and circles). Why (10-11): two of three such briefs made the character the analyst, and the next dropped the analysis.
- Footage found for someone who will be replaced shows that person big (a third or more of the picture's height in most frames), as the one the camera follows: slow-motion replays and close angles ("<who> slow motion", "<who> clips for edits", "<who> fancam"), never a broadcast reel of wide shots. H3 redraws only someone big in its frame (10-11: in broadcast highlights the tallest figure was under a third of the frame; in slow-motion replays of the same player he filled about nine tenths).
- Get the video that is the footage, never one about it. A meme is its template ("<the meme> template"), whose frames show the moment the request names; a famous clip is the clip people know, never a remake, a "vs original" video or a copy with another caption burned in. Check it with `kit.mjs`. `fetch.mjs get` takes any link (TikTok, X, Instagram). Prefer a clean picture; at most 10 minutes long. One video when one clip is the point; 4 to 6 for a compilation, each a different part.
- For a highlight edit of a real person, team or season: research their best and most famous moments and name them in the brief.

**THE SONG.** Only for an edit, an AMV, a lyric or music-driven video when no song was attached: the real song it should use (a linked or uploaded video's own song when they want that video remade, otherwise the track this kind of edit uses now), fetched with `fetch.mjs song`. For an uploaded video's song that cannot be named for certain, `song` is that video's path. A lyric or sing-along video always has one: for a traditional or public-domain song with no recording named, the most-viewed recording sung straight through (10-11: a nursery-rhyme brief gave none and the film stopped). Narrated and explainer films get none: the planner makes their music.

**THE STYLE.** `card` = one style from the list (2.13): `[proven N]` = its best unattended film was rated N/10 (8 or more), `[weak N]` under 8, `[untested]` none. When several fit, a proven one; the look matches the subject and its mood; a moodboard they attached means the nearest card. Without `--style`, `style_note` stays "" unless they name or describe a look, channel or kind of video none of the styles really is (or want the look of a linked or uploaded video): then `card` is "" and the producer studies that look itself, running `kit.mjs` on the video whose look they want, opening every sheet, and writing `style_note` (how the film looks, moves, cuts and sounds, how its people act and talk, how words sit and move; its first sentence naming the look; never naming or describing the example's characters, which would walk into the film; no rules) and `style_frames` (3 frame files from that kit, each a different shot). Photos of real-looking people or places with no video, for a film their words describe as filmed (a music video, a shoot, a camera, real light), make the film live action, photoreal like the photos, unless their words name a drawn, painted, animated or 3D look; "glossy", "cinematic" and "music video" describe photography. Such a film takes a card only if its look is live-action photography; otherwise the photos are the look studied (10-11: photos of real people for a "hyper-glossy Y2K music video" were drawn as glossy 3D). `use_case` = the section the card sits under; a painted film never takes a section whose films are cut from real footage (a fan edit, a sports edit), because that section's guide says there is no film without footage.

**SPEECH.** `speech`: characters (people on screen talk), narrator (one unseen voice) or none (a song's words, their footage's own sound, or a style with no voice).

**THE BRIEF.** The planner never sees the user's message, only the brief, the card and the use-case file. Written in plain English whatever their language, concrete, as notes to a director:

- the user's own words, verbatim, in quotes;
- what they mean, as researched: the format or thing named, how it really looks, goes and sounds, and the kit folder of the real one watched;
- the point (what a viewer new to this should understand or feel by the end), where it takes place (from the request and the research, never from the style), who is on screen, who speaks; never a list of events, shots or lines (the planner writes the whole film, words included); no length unless they asked;
- the real media: each footage file and the song by path, what it is, how the film uses it;
- for a factual film: 4 to 6 concrete, picturable facts the producer is certain of, their own facts first;
- nothing about the look or the edit's treatment (colours, grade, typography, where words sit, effects, transitions: the card has those). A format's own fixed caption, punchline sounds and recurring graphic are what the format is, so they stay. Nothing about how the film is funny: no jokes, puns or gags. Their footage is shown as filmed. No template wording, no invented claims about their business or people.

Why the point and not a list (10-09): when the producer read the card and the section guide, its brief became the card's shot list and the planner filmed that list; the producer no longer reads either. Why no jokes (10-10): a brief asking for gags specific to fruit got a pun script from a style that plays it straight; the planner follows the brief over the card.

The other fields: `footage_use` is "" unless the film is made of a video they uploaded; then one sentence starting EDIT (their footage with titles, labels or a restyle added), CLIPS (their clips between painted shots), B-ROLL (their footage under narration about it), MONTAGE (a highlight, hype, recap or sports edit cut on the music's beats; always for a card whose first line is `footage: edit`) or REFERENCE (only its look or content), then what they asked; `FOOTAGE.md` rule 1 reads that first word. `refuse` is "" unless the film cannot be made from what was given: never for a missing song, audio or image (the pipeline makes those), never because it is not a story, never when their footage is there; then one polite sentence saying what is missing. `aspect`: the frame given, else what the request implies, else 16:9 (each use case with an `aspect:` header adds "A <section> is <aspect> unless they ask for another shape."). `language`: the language they wrote in, in English. `brand`: for a logo animation, the brand's name as spelled. `url`: the address they gave. `title`: 3 to 6 words. `why`: one sentence.

### 2.7 The answer, field by field

Every key is required ("" or [] where it does not apply). `refs` is in the schema only when there are reference files; `duration` only with `DURATION=1`.

| Field | Type | What the producer writes | What the code does with it |
|---|---|---|---|
| `refuse` | string | "" or one polite sentence | non-empty: print it, exit 0, no film |
| `title` | string | 3 to 6 words | the run name `auto-<card>-<slug>`; a studied card's name and id |
| `use_case` | enum of the menu's section names (with `--style`, only the sections listing it) | the section the card sits under | the section, if it lists the card; else the first section that does; for a studied look, this value |
| `card` | enum: "" and every style id (with `--style`, only that id) | the style | the card. "" means a studied look |
| `watched` | string[] | the real videos it watched with `kit.mjs` | not read by code; it makes the model watch before writing |
| `copy` | string | the link or upload path of the one video the request is modelled on, or for a named format with no link the best real example watched; "" when none | its shots go to the planner (`reference/`) and the planner runs at medium effort; an upload named only here is not footage |
| `style_note`, `style_frames` | string, string[] | with `card` "": the studied look; 3 frame files from its kit | a new card (2.13); a frame from the user's own video makes that video the look |
| `aspect` | enum of the 7 frames | the frame | used unless `--aspect` |
| `language` | string | the request's language, in English | not English: "Any narration and on-screen words in <language>." |
| `footage_use` | string | "" or one sentence starting EDIT, CLIPS, B-ROLL, MONTAGE or REFERENCE | appended after the footage paths in the brief; set with an empty `footage`, it makes every upload footage |
| `footage` | string[] | downloaded paths and the uploads the film is made of | each existing video file becomes footage |
| `song` | string | a fetched song's path, or an uploaded video whose sound is the song | a sound reference in `attached/` (a video's sound extracted first), unless the user attached a sound file |
| `brand` | string | the brand's name, for a logo animation | the logo rule; `agent/refs/<brand>/logo-mark.svg` if no logo was attached |
| `url` | string | the address they gave | used when `--url` is not given |
| `brief` | string | the notes to the planner | the first part of the brief |
| `why` | string | one sentence | printed only |
| `characters` | {name, image_url}[]; on the swap path {name, image_url, real}[] | every named character of a real film, show, game or cartoon who appears on screen, never a real person: its official picture as it looks in this film or franchise. On the swap path (1.3) also every real person the request puts in someone's place (`real: true`; no other real person): a clear recent photo, one person, face big, front-on (Wikimedia Commons first). Each a direct image URL it checked | fetched by code before planning (2.10) |
| `speech` | enum: characters, narrator, none | who speaks | not read by code |
| `refs` | {n, category, audio, logo, screen}[] | its reading of each reference file | a picture with no category takes this category (else object); a sound file takes its kind; `screen` can put the film on the launch path |
| `duration` | number | with `DURATION=1`: the length the words ask for, 0 if none | the set length when `--duration` is not given |

### 2.8 Studying a video: `kit.mjs`

Two callers, two sizes: `auto.mjs` studies every link, every uploaded video, and after the session a `copy` link the producer found itself, with `kit({ url, local, title, channel, big: true })` (larger sheets, attached to the first message); the session runs `node agent/h3film/kit.mjs <link or file>` itself and gets smaller sheets it opens with Read.

- Folder: `agent/runs/_style-builds/kits/<key>`, where the key is the link's last 40 characters (other characters as `_`), or `<file name>-<size in bytes>` for a local file (two folders' `video.mp4` must not share a kit). Everything is cached; a kit is made once.
- A link's facts come from `yt-dlp -j`. Its video: yt-dlp, first 150 s only; larger kits up to 720p into `v720.mp4`, smaller up to 360p into `v.mp4`. A local file is used where it is.
- Frames: ffmpeg, first 150 s, 2 a second; larger 700 px tall into `f700/`, smaller 300 px tall into `f/`. The frame at t seconds is number 2t+1.
- Which frames go on sheets. Larger: only frames where the picture changes (the frame cut into a 4x4 grid; kept when any cell's mean brightness moved more than 12 of 255 since the last kept frame) and at least one every 1.5 s. Smaller: every frame.
- Sheets: larger `bigc-NN.jpg`, 4 frames in 2 columns, cells up to 700x700; smaller `sheet-NN.jpg`, 16 frames in 4 columns, cells up to 430x300. Each frame is labelled with its time and keeps its own shape (`KIT_FIT=0` restores fixed cells). Labels use Helvetica on macOS, else `assets/fonts/Inter-Regular.ttf`.
- Cuts: PySceneDetect 0.7.1. A cut counts only where ContentDetector (threshold 27) and HashDetector (threshold 0.3) both find one, in the first 150 s. One detection at a time per machine (`/tmp/h3-kit-cuts.lock`). Why (10-09): ffmpeg's scene score found 9 of 14 beat cuts between dark shots, and 18 cuts where a flashy edit had 9.
- Words: a mono 96 kbps mp3 of the first 150 s goes to `transcript()` (2.9), cached as `stt.json`.
- Music: `research/tools/analyze_music.py` with `ALLIN1=0` (madmom beats, librosa loudness sections low, mid, high): tempo, loudness sections, cuts per beat in each section.
- The sound a platform credits: a TikTok page (its sound's title and author, whether it is an original sound, the song TikTok matched, named through Apple's free iTunes lookup); a YouTube Short's page (its sound pill). Cached as `sound.txt`. Why (10-11): a format's sound is the one most of its videos share, and the producer cannot hear.
- Length: yt-dlp's for a link, ffprobe's for a file (10-10: a file's kit had said "? s long", and the brief called a 37.5-minute compilation "about 150 s").

The kit text the session reads:

```
VIDEO "<title>" (<channel>, <views>) <url>, <length> s long; you see its first <n> s [only: … not the other <m> s].
Its pictures: contact sheets of its frames wherever the picture changes (…) | its frames twice a second … Open every sheet with Read, in order: <sheet paths>
Single frames: <dir>/<f700 or f>/0001.jpg to …/<last>.jpg; the frame labelled t s is number 2t+1 (…).
Picture changes measured (cuts, seconds): <times> | none: one unbroken shot | not measured
Words heard (speech to text, seconds): <start-end "words"> … (at most 6,000 characters) | none | unknown: speech to text failed (…)
What its uploader says it is (title, track, description, tags): …
Its sound, as the platform credits it: <credit>
Its music measured: <bpm> bpm; loudness by section: …; cuts per beat by loudness: …
You cannot hear it: describe its sound (music genre and instruments, effects, the voice) from these lines; say it is inferred.
```

When sheets are attached, "Open every sheet with Read, in order: …" becomes "They are attached above, in order." A video that cannot be downloaded gives one line saying so.

`shotSheets(kit, folder)` makes what the planner sees of a video the film follows: one frame per shot (the middle of each stretch between measured cuts; a long shot one every 1.5 s), at most 32 spread evenly; each frame copied as `ref-NN.jpg` and laid out four to a sheet as `shots-NN.jpg`, labelled `ref-NN | shot S: a-b s`. Why: the brief alone lost what made the video that video (10-10); a 4-minute lyric video once gave 32 sheets, about 70k tokens the planner re-read on every request (10-11), hence the cap.

### 2.9 Getting real media: `fetch.mjs` and `transcript()`

`fetch.mjs` reads `.env.local` when it starts (it fails without it) and writes into `agent/runs/_auto/files/`.

- `search "<query>" [--shorts]`: `ytSearch()` returns yt-dlp's top 30 (`ytsearch30:<query>`; with `--shorts`, filtered to videos under 4 minutes) plus every Short on YouTube's own Shorts results page (about 25, read from the page's `ytInitialData`), without repeats: about 55 lines of `<id>  <seconds> s | a Short  <views> views  "<title>" by <channel>`. No API key. Why (10-10): the YouTube Data API's ~100 searches a day ran out mid-batch and the producer drew a cartoon of a meme it should have fetched; on 20 real lookups this list held the API's first result 18 to 20 times out of 20.
- `get <videoId or link>`: yt-dlp, the best mp4 up to 1080p with m4a sound, merged to `fetched-<id>.mp4`, 15-minute limit, cached. Any site yt-dlp opens (10-09: a meme went round as a TikTok edit, and with YouTube ids only the producer fetched the raw clip without the explosion). On failure it prints `could not download <arg>: <yt-dlp's error>`. When YouTube's bot check refuses ("not a bot"), it writes `agent/runs/_auto/files/.youtube-blocked`, which stops the film (2.4). Only `get` writes this mark; a download blocked inside `kit.mjs`, `song` or the planner's tools does not.
- `song "<title> <artist>"`: the released song with its synced lyrics, as `song-<slug>.mp3` and `song-<slug>.lrc`. (1) LRCLIB search (free, no key): entries with synced lyrics, not instrumental, whose artist and track share a word of 3 or more letters with the query; the release first, other cuts (video, lyric, live, remix, sped, slowed, edit, version, clip) last. (2) yt-dlp `ytsearch10:<query> official audio`: "- Topic" channel uploads first. (3) The first upload whose length is within 2 s of a synced entry is downloaded as mp3 with that entry's lyrics beside it. (4) With no such pair, the audio of the first "official audio" result, with no lyrics. Why (10-11): speech to text on a sung Japanese mix gave one misheard English line 80 times, and another song came as its 4:32 music video.
- `link <url>`: `yt-dlp -j`: title, uploader, length, its song (track and artist), views and 500 characters of description.

`transcript(file, cache)` in `research/h3/tools-footage.mjs`, used by `kit.mjs`, `auto.mjs` and the planner's tools:

- When `<file>.lrc` exists, the lines are the synced lyrics, in the song's own language and timing, shifted by the offset most matching lines agree on: a lyric line of 3 or more words and a heard line holding at least half of its words make a pair; at least 3 pairs must agree within 0.5 s; their median is the offset; an offset under 1 s is ignored. Each line ends at the next line's start (the last after 5 s), at most 8 s after its own start. Why (10-11): a lyrics entry synced to another cut of a song ran 17 s ahead of the singing.
- Otherwise ElevenLabs speech to text (`POST api.elevenlabs.io/v1/speech-to-text`, `model_id` `scribe_v2` or `ELEVENLABS_STT_MODEL`, the sound as a mono 96 kbps mp3). Words become lines at a sentence end, a pause over 0.6 s, or 14 words. The result is cached with the file's size; a cache with another size is made again (10-11: a cached transcript of a compilation fetched earlier under a song's name put a sing-along's lyrics 11.46 s late).

### 2.10 Pictures of characters and real people

The producer lists them in `characters`; code fetches them before the planner starts (the model never downloads them), at most 8 (names past the 8th are dropped). Each `image_url` is fetched with a plain User-Agent, following redirects, and kept only if the reply is `image/png`, `image/jpeg` or `image/webp` and at least 8,000 bytes. It is saved as `<run>/refs/<slug of the name>.png` or `.jpg` (WebP converted to PNG). Not fetched with `--dry`.

The brief then says, for characters: "The official pictures of its real characters, each that character's design, attached as it is to every clip that shows them and never redrawn (the prompts keep their names): <file> (<name>), …". On the swap path, for real people: "Photos of the real people it puts in someone's place: <file> (<name>), …; in footage kept as filmed (a live-action swap, FOOTAGE rule 3) each is attached as it is to every clip that shows them, in a drawn film each one's design is drawn from their photo." A picture that cannot be fetched is only logged ("character picture left out: <name> (…)"); the brief does not name it.

Why: two takes of a film about animated characters redrew them from words after the picture tools refused drawings of them, and a hint to fetch the pictures was never taken up (10-11). Two swap takes with no photo drew made-up men (10-12). Asking for a photo of every real person on screen, not only those swapped in, came after the approved films and is not in the code (1.3).

### 2.11 What each file becomes

Uploaded videos:

- Footage when the producer put it in `footage`, or it is neither `copy` nor the look, or `footage_use` is set and `footage` is empty. An upload is never dropped because the producer forgot to name it.
- The video the film follows when its path is `copy`; the look when no card was picked and a style frame comes from its kit. Such a video is not footage unless also in `footage`, and leaves the brief as words ("the video they uploaded for this film to follow, whose shots are in your first message" or "the video they uploaded for its look, which the style card was studied from"), because the launcher treats every video path in the brief as footage.
- Printed as `upload <path>: footage + the video the film follows + its look`.

Fetched footage: every `footage` path that exists and is a video is footage too.

The song: if `song` is a video, its sound is extracted with ffmpeg to `agent/runs/_auto/files/<name>-<size>-sound.mp3` (192 kbps). When the user attached no sound file, the song becomes a sound reference named after its file and marked as a song; a fetched release is called "the real song fetched for this film". A fetched song therefore also puts the "References the user attached" block in the brief.

Reference files take the producer's reading: a picture with no category takes its category (object if none of the five); a sound file takes its kind; an SVG is always a logo.

A lyric video: the song is the sound file marked song, else the first sound file; with none, the run prints how to add one and exits 0. The timed lyrics are the user's `.vtt`, else a `.vtt` written from `transcript()` (the synced lyrics when `fetch.mjs song` found them) into `agent/runs/_auto/files/<song>.vtt`. A song with sung words in any other film gets its lines written as a `.vtt` too.

A logo animation: the logo is a brand-kit picture marked as a logo (or a picture with no category the producer marked as one), else `agent/refs/<brand slug>/logo-mark.svg` if this repo has it (a few brands), else the brief says "No logo image is given: design the mark."

Paths with spaces or other signs are copied into `agent/runs/_auto/files/` first. The user's pictures and sound files are copied (not linked) to `<run>/attached/<Name>[-N].<ext>` (WebP and GIF as PNG), and the brief names those copies.

### 2.12 Handing over to the planner

The run folder before the planner starts:

- `attached/`: the user's pictures and sound files (and a fetched song), named by their @Name.
- `refs/`: the fetched character pictures and real people's photos.
- `reference/`: for a video the film follows (`copy`), or else the user's own linked or uploaded video whose look was studied: `shots-NN.jpg` (sent as pictures in the planner's first message), `ref-NN.jpg` (each frame as a file, for the storyboard tool's `shots`) and `reference.txt` (what the frames are, how closely to follow the video or that every still is drawn as another shot of it, and the kit's measured cuts, words, uploader text and music). A look studied from a video the producer found itself gets no `reference/`, only its card.

The command, from the repo root, output appended to `agent/runs/_auto/<name>.log`:

```
./agent/h3film/launch-locked.sh agent/runs/h3film-<name> -- ./agent/h3-film-agy.sh <name> agent/runs/_auto/<name>.txt 0
```

The `0` is the planner's own render budget: the planner renders nothing; `auto.mjs` renders afterwards. `launch-locked.sh` lets one launch start at a time per machine. It was written for an earlier planner whose tool server was registered globally; the Claude planner reads its own `mcp.json` per run, so today it only spaces launches out. A service running many films at once does not need it.

The environment `auto.mjs` gives the launcher, on top of its own (which carries every key, `H3_BUDGET_USD` and `H3_RUN_NAME`):

| Variable | Value |
|---|---|
| `PLANNER` | `claude` (anything else stops the launcher) |
| `CMODEL` | `claude-sonnet-5-5` unless set |
| `CEFFORT` | medium for launch, lyric and followed-video films, high otherwise, unless set (1.3) |
| `LAUNCH`, `MINIMAL` | `1` or empty (1.3) |
| `EXAMPLES` | the example films' files, space-separated, repo-relative |
| `SKILL` | `<repo>/skills/h3-film/SKILL-gemini.md`. Started by hand without it, the launcher uses the older `SKILL.md`, whose launch path renders clips itself on fal and spends money |
| `RATIO` | the film's frame |
| `H3_DURATION` | the set length in seconds, or empty |

### 2.13 The style list and studied looks

The style list (`catalogue()`, cached in `agent/runs/_auto/catalogue.json`, rebuilt when `auto.mjs`, `menu.ts`, `presets.ts`, `ratings.json`, `best-takes.json`, the cards folder or any card changes):

- Sections and their styles come from `agent/web/app/styles/menu.ts`. The menu id `kurzgesagt-flat` is the card `bold-geometric`. A style with no card file is skipped, and a section left with none is dropped (Animated chart). Today: 22 sections, 77 styles (85 on the menu; the 8 without a card are `clean-light-saas` and the 7 animated chart styles).
- Name: the card's first `# ` heading without a trailing parenthesis, else the name in `presets.ts`. `ref`: the `"ref"` in `presets.ts` (the real channel or film the look comes from). Look: the first quoted sentence after a "Style sentence", "Style line", "Job line" or "## Look" label in the card, cut at 320 characters.
- Score: the best `rating` in `ratings.json` among runs named `h3film-gem*` or `h3film-fgem*` (the card read from that run's `brief.txt`, else from the run's name), and in `best-takes.json` among entries with mode `gemini`. These are the style tests of 10-05 to 10-08; later films are not counted (11.2).
- Mode (the planner path): the card's mode in `best-takes.json`, else `opus-launch` with a card line `planner: launch`, else `painted`.
- Each line the model sees: `- <id> "<Name>" [proven N | weak N | untested] <ref> — <look>` under `## <Section>`; a style listed again under another section shows "(see above)". `HIDE_STYLES=a,b` leaves styles out (to test the studied-look path).

A look none of the styles is (`card` ""): with an empty `style_note`, exit 1. Otherwise code writes a card: id = the title as a slug, first 4 words (`studied-look` if empty), with `-2`, `-3` … when that card exists (10-10: a second take of one request had rewritten the first take's card); look pictures = the `style_frames` that exist, up to 4, copied to `agent/web/app/styles/refs/<id>/pool/look-N.jpg`; and the card file `agent/web/app/styles/cards/<id>.md`:

```
# <title> (a look the producer studied for this film, <date>)

## Style sentence
"<first sentence of style_note>"

## Look
<style_note>

## Look pictures
- agent/web/app/styles/refs/<id>/pool/look-1.jpg
Frames of the real thing: STYLE references for drawing this film's own stills (its people, places and type) in this look. Never attach one to a clip: whatever they show walks into the film.
```

The film then runs as a painted film on this card. The card is not added to `menu.ts`, so later films never see it. Since 10-09 the producer studies the look in the same session, and the planner runs exactly as for a menu style.

### 2.14 The brief: the code's part

The layout and the strings later steps parse are in 1.5.1. What goes into the code's lines:

The section's hard rules (`HARD` in `auto.mjs`):

- Lyric video: the user's song is the only soundtrack (`make_soundtrack song=<file>`, `song_start` = the window's start, `duration=30`, parts = the clip lengths, no lines, no music); the lyric sheet is the song's `.vtt`, pasted to the planner with each sung chunk as an id `[L1]`, `[L2]` …; pick the 30 s window that holds the first chorus; each line appears on screen as it is sung.
- Logo animation: animate the brand's own mark (shown with `still kind=lockup mark=<file>`), never redrawn or invented, or "design the mark" when there is none; the name spelled exactly; the film ends held on the finished logo; no narration, music only; about 10 seconds.
- Event promo: no narration, music only.
- Software launch / demo: the product's web address, or "No URL was given: draw the product's surfaces from this description and any attached images."; surfaces are the product in use, never its marketing site or pricing.

One reference line per attached item, by kind:

- character, object, location: in a live-action film or an edit of real footage the clips attach the photo itself (a redraw loses the likeness, 10-11); in a drawn film it is drawn once in the film's style as a subject still (a location: as the place itself, the ground of its scenes) and the clips attach that still, never the photo.
- moodboard: the look the user wants (the card is the nearest to it): style references for every still, never content, never attached to a clip.
- brand kit: logos and product shots. The logo is shown only by the still tool (`kind=lockup`, `mark=` or `wordmark=`); nothing draws it. The logo's commonest strong colour (saturation over 0.3, value over 0.25, from an SVG's colours or a picture's opaque pixels) is named as the film's accent. Each product shot becomes a product still (a screen: an image edit hero; a physical product: a subject still).
- the user's own voice recording (speech, or a voice over music): the film's narration, with every line of its words and their times. A mix is the whole soundtrack (`song=`), parts at the pauses; speech goes in as `make_soundtrack` lines from the file, with the style's music under them; whoever speaks on screen speaks with this voice (10-08: before this, the recording was dropped and our own voices read the film).
- a song: the soundtrack (in a montage of footage, `music=` under the footage's own calls; otherwise `song=` as the whole soundtrack from its strongest part). If words were heard, its sung lines go to the planner as a `.vtt` so words on screen become `[Ln]` ids the tools fill in (10-09: a planner copied an example's `[L1]` … `[L9]` with no lyrics behind them, and H3 painted "[L1]" as gibberish on a road).
- instrumental music: the music under the narration, or the whole soundtrack with no narration.
- a sound file the session could not place: left out, with a printed note.

### 2.15 Settings

| Variable | Default | Effect |
|---|---|---|
| `PRODUCER_MODEL`, `PRODUCER_EFFORT` | `claude-sonnet-5-5`, `medium` | the producer's model and effort |
| `PRODUCER_LEAN` | on | `0` gives the producer the account's claude.ai connector tools again |
| `PRODUCER_STATIC_FIRST` | off | `1` sends the fixed rules as a system prompt and the request last |
| `DURATION` | off | `1` also asks the producer for a length ("30 sec ad" = 30). The length is then `--duration`, else that, else none when the user's recording, finished soundtrack or an EDIT of their video sets it, else the use case's Length line. Off since 10-10 |
| `HIDE_STYLES` | none | comma-separated style ids the producer may not pick |
| `CLAUDE_BIN` | `claude` on PATH | the CLI for the producer and the map stages (the planner always runs the `claude` on PATH) |
| `CLAUDE_KEEP` | off | `1` keeps the producer's session on disk |
| `KIT_FIT` | on | `0`: frame sheets with fixed cells |
| `ELEVENLABS_STT_MODEL` | `scribe_v2` | speech to text |
| `CLAUDE_MODEL` | `claude-haiku-5-5` | the default model of `claude.mjs`; the producer and the swap question name their own, so nothing uses it |
| `H3_SWAP` | asked | `1`: the swap path; `0`: the batch path; unset: one question decides (1.3) |

### 2.16 Time and cost

The whole step, video studies and downloads included: median 0.8 min (0.2 to 4.7) over the 35 newest test films. The session alone (73 producer calls in this repo's 10-12 runs, from `claude-calls.jsonl`): median $0.145 ($0.056 to $0.355), 0.46 min (0.15 to 4.0), 5 turns (at most 11). These are Claude Code's own figures at list price with the 5-minute cache; some of those runs set Claude Code's helper model to Haiku 5.5 (since taken out), which CLI 2.1.285 prices as Opus, so they read somewhat high. ElevenLabs speech to text and downloads are not in them.

## 3. The planner and its tools

### 3.1 What the planner does

The planner is one Claude Sonnet 5.5 session per film. It gets the brief and a long first message built from instruction files (1.5.2). It has file tools, web search and fetch, and the film tools served by `research/h3/mcp.mjs`. It writes into the run folder `PLAN.md`, the finished soundtrack (one `make_soundtrack` call), the stills, one H3 prompt per clip, `render.json` (or, for a montage, `EDIT.json`, which code turns into the prompts and `render.json`) and `NOTES.md`. Then it stops. It never renders: render-all renders every clip after the session ends, and the join cuts the film.

### 3.2 The launcher, step by step (`agent/h3-film-agy.sh`)

Arguments: the run name, the brief file, and a render budget in dollars (default 5). `auto.mjs` always passes 0, so the planner cannot render. The script is zsh and sources `.env.local` with `set -a`, so every key is exported to everything it starts, the planner's `claude` process included. `PLANNER` must be `claude`.

1. Loads `.env.local`. Makes `agent/runs/h3film-<name>/`, exports `H3_OUT` (the run folder) and `H3_BUDGET_USD`, copies the brief to `<run>/brief.txt`. With a frame other than 16:9, every "16:9" in that copy becomes the frame (`perl -pi`).
2. Derives `CARD`, `PAINTED`, `FOOTAGE`, `UC`, `MAPS`, `REFS` from the brief (1.3). A brief naming a card that is not on disk stops the run: before this check such films ran without their card.
3. A launch film with a card (unless `LAUNCH_INDEX=0`): writes `agent/h3film/library/CASTABLE-index.md` fresh, `CASTABLE.md` without its 38 `NEEDS:` lines plus one line saying where they are. This file is written into the repo on every launch film.
4. Picks the files to paste (3.4); every listed file must exist or the run stops (a missing file used to vanish from the prompt silently). Runs `lyric-ids.py` for each `.vtt` in the brief.
5. Assembles `<run>/prompt.md` (1.5.2), applies the frame replacements, and, when the write hook is on, swaps the skill's "call `check_prompt` after each prompt" sentence for "Each prompt is checked automatically as you write it (the result comes back with the write): write all prompts in one batch and fix every row it lists".
6. Stops if `prompt.md` is over 185,000 bytes. The limit came from an earlier planner runtime that cut longer prompts without a word; every tested film was planned under it.
7. Writes `<run>/mcp.json` (3.5).
8. Runs `python3 agent/h3film/manifest.py launch`, which starts `manifest.json` (1.5.8), and writes `code.diff` when the repo has uncommitted changes. Deletes any old `FAILED.json`. Writes `t0`.
9. Starts the session (3.3) in the background and polls every 3 s; if `<run>/FAILED.json` appears, it kills the session at once. On macOS, `caffeinate` keeps the machine awake meanwhile.
10. After the session: 3.7.

### 3.3 The session

Run from `$HOME/h3-claude/h3film-<name>`, an empty folder outside the repo:

```
<prompt.md + "(Your working folder is not the repo…)" + reference/reference.txt> \
 | node agent/h3film/with-pictures.mjs reference/shots-*.jpg            (only if reference/ has sheets)
 | env CLAUDE_CODE_PROMPT_CACHE_TTL=5m CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1 CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH=12288 \
       REPO=<repo> MCP_TOOL_TIMEOUT=1800000 \
   claude -p --model claude-sonnet-5-5 --effort <high|medium> \
     [--tools Read,Write,Edit,Glob,WebSearch,WebFetch] --disable-slash-commands \
     --settings agent/h3film/planner-hooks.json --add-dir <repo> --add-dir <repo> \
     --mcp-config <run>/mcp.json --strict-mcp-config --dangerously-skip-permissions \
     [--input-format stream-json] --output-format stream-json --verbose
 > <run>/transcript.jsonl 2>> <run>/stderr.txt
```

There is no system prompt flag: Claude Code's own default system prompt sits in front of the film prompt in every tested film (what it contributes was not measured; a rebuild on the raw API would not have it).

Model and effort:

| Film | Effort | Why |
|---|---|---|
| Launch film | medium | blind picks on 10-10: medium launch takes were liked in 2 of 3 rows, high ones in 0 of 3; about half of a launch planner's cost was thinking |
| Lyric video section | medium | set on 10-11 with the effort-by-kind change; no separate test is recorded (11.5) |
| A film modelled on a given video (the producer's `copy`), unless `CEFFORT` is set | medium | cost (10-10): the attached frames carry what the extra thinking was spent on; one such take cost $1.36 at high against $0.80 for a take without them |
| Everything else, footage edits included | high | medium cut AI cost 23-47% on six films but came out worse on 4 of them, and last on both edit rows (10-10) |

Sonnet 5.5 is the planner because a blind test on 10-09 found it about as good as the Gemini 3.8 Flash planner it replaced, twice as fast, with no Google Cloud dependency. GPT-6.1 Sol was tested on 10-10 and turned down: slower on every painted row (8-18 min against 3-5) and not reliably cheaper.

Built-in tools:

| Film | Flags | What the planner sees |
|---|---|---|
| Painted | `--tools Read,Write,Edit,Glob,WebSearch,WebFetch --disable-slash-commands` | those six, no skills, no slash commands; the h3 tools are sent whole from the first request |
| Launch | `--disable-slash-commands` | every Claude Code built-in tool, Bash and ToolSearch included (24 in the 10-12 runs); the h3 tools load through ToolSearch |

Why: on 10-09 Claude Code's 28 built-in tools and 89 skills rode along on every painted request, and one painted planner wrote all its clips through Bash. On 10-10 the skill list was dropped from launch sessions too: none of 9 launch planners had called a skill. Launch sessions keep Bash although the prompt says "There is NO Skill tool and NO Bash in this session".

Claude Code settings that must hold (or their equivalents in another harness):

- `CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH=12288`. Claude Code cuts each MCP tool description at 2,048 characters otherwise. That cut hid `user_video`'s montage instructions and the `image` tool's product-still rules from every planner until 10-11; at 8,192 `user_video` lost its caption modes. The longest description today is `user_video` with its EDIT.json note, 9,460 characters (3.9). Keep every description under 12,288. Claude Code 2.1.285 honours the setting (its footage runs wrote EDIT.json fields that appear only after character 6,367 of that description).
- `CLAUDE_CODE_PROMPT_CACHE_TTL=5m` and no title call: billing only. Of 129 gaps between calls in 23 planners, one was over 5 minutes.
- `MCP_TOOL_TIMEOUT=1800000` with the tool server's `H3_CALL_LIMIT_S=1750`: a call still running after 1,750 s answers "STILL WORKING … Call <tool> again now with exactly the same arguments", and the repeat waits on the same job. Built for an earlier runtime's 3-minute cap; kept because every film was tested with it.
- Claude Code runs a turn's MCP calls one after another unless a tool is marked `readOnlyHint`. `mcp.mjs` marks `storyboard` and `make_soundtrack` read-only so their calls run side by side (10-11: batches of 9 storyboard calls took 8-25 min one by one, past the 5-minute cache: $2.44 of re-written context over 8 films). `image` stays one at a time on purpose: its edits chain.

A rebuild outside Claude Code needs the same things: full tool descriptions; parallel calls for `storyboard` and `make_soundtrack`; tool results that carry images the model sees; a file-read tool that shows images (planners look at sample sheets and `.view.jpg` stills with Read); web search and fetch; the two hooks (3.6); and a stop when the hook says the film is whole.

Measured: planner median 3.3 min (1.2 to 7.4) and $0.43 over the 35 newest test films. In this repo's 10-12 test runs: launch films median 7.9 min and $1.04 (4 runs); painted 3.9 min and $0.43 (15); footage edits 4.4 min and $0.56 (44).

### 3.4 What the planner reads

The first message's layout is in 1.5.2. The files pasted whole, by kind:

| Kind | Pasted, in this order | The note after the files |
|---|---|---|
| Launch film with a card (`LAUNCH=1`) | `skills/h3-film/references/motion.md` (7.7 KB), `agent/h3film/exemplars/hero-edit-magic-hour-ugc-form.txt` (1.5 KB), `skills/h3-film/references/translate.md` (8.7 KB), `skills/h3-film/references/template.txt` (7.3 KB), `agent/h3film/exemplars/films/v13-clip1.txt` to `v13-clip3.txt` (31 KB), Orchids `orchids-clip1.txt` to `clip4.txt` only when the card has no example clips, the card, the card's `refs/<id>/example/clip*.txt` | THIS IS A LAUNCH FILM: follow the skill's launch path, not PAINTED.md. The card sets only the look (style sentence, palette, type, finish, sample stills as style references, how surfaces are presented); its example shows the style done well, never its topic, words or beats. Do not read the Orchids example films or `styles.md`. Read `CASTABLE-index.md` whole before planning, and for each cast component its `library/shapes/<id>.md` and `references/components/<id>.md`. Call `make_soundtrack` in the same batch as the first stills. Card `refs/` paths are relative to `agent/web/app/styles/`. Never open other runs |
| Painted film | `skills/h3-film/PAINTED.md` (22.7 KB), the use-case file, the card, its `refs/<id>/exemplar-prompt.txt` if any (3 cards), every file in `refs/<id>/example/` (PLAN.md and clip prompts, 1.4-38.7 KB), `<run>/lyrics-ids.vtt` when the brief names a `.vtt`, then the `EXAMPLES` runs (1.3) | The files are whole: do not open them again. LOOK at the card's sample sheet before picking, every still right after making it, and each clip's stills again before writing that clip; do every web lookup the storyboard tool asks for; never open RULES.md, MERGE-AUDIT.md, briefs.md, other runs or code. The example runs are the best-rated films so far: the bar to beat, never their topic, story, objects, words or compositions. With lyrics: the lyric-id rules |
| Minimal (`bold-flat-poster`) | `skills/h3-film/MINIMAL.md`, the card, its exemplar prompt if any | the painted note |
| With "References the user attached" | `skills/h3-film/REFERENCES.md` added to the list | |
| With footage | `skills/h3-film/FOOTAGE.md` (21 KB) after the note | the footage lines of 1.5.2 |
| Only when started by hand with no card | the launch files plus all 8 Orchids clips | read `CASTABLE.md` and `styles.md` |

Why paste whole files: an audit of 25 painted runs (10-04) found about 1.4 min a film of reading turns, hunts for wrong paths (card `refs/` paths live under `agent/web/app/styles/`) and reads of other runs. The 10-09 rebuild cut a painted planner's prompt from 121 to 71 KB by pasting only the painted files.

A film modelled on a given video, or one whose look was studied from the user's own linked or uploaded video, gets `reference/` (2.12): the shot sheets ride in the first message as pictures (`agent/h3film/with-pictures.mjs` wraps text and pictures as one stream-json user message) and `reference.txt` follows the prompt. The `ref-NN.jpg` frames are for drawing stills only (storyboard `shots`); the stop hook refuses a `render.json` that attaches one, because whatever they show would walk into the film.

Lyric films: `agent/h3film/lyric-ids.py <vtt> <run>` writes `<run>/lyrics-ids.vtt` (each cue's line replaced by an id `[L1]`, `[L2]` … with its word and character count; each distinct line gets an id in order of first appearance; cues with no letters or with `#` are dropped) and `<run>/lyrics.json` (`{"[L1]": "<words>"}`). The planner only ever writes ids: the model's output filter refuses copyrighted lyrics. The tool server puts the real words into every tool argument (`[Ln]`, or a word range `[Ln:a-b]`), and render-all puts them into the prompts.

### 3.5 The tool server's settings: `mcp.json`

`{"mcpServers": {"h3": {"command": "node", "args": ["<repo>/research/h3/mcp.mjs"], "env": {…}}}}`. The env holds only these names, and only when set: `H3_OUT`, `H3_FOOTAGE`, `H3_BUDGET_USD`, `H3_ACCURACY`, `H3_PAINTED`, `H3_CALL_LIMIT_S`, `NANO_BANANA_MODEL`, `VOICE_PROVIDER`, `RATIO`, `H3_REFS`, `CODE_SHOTS`, `MAPS`, `MAPS_CARD`, `STORYBOARD_INLINE`, `FOOTAGE_COMPACT`, `EDIT_LIST`, `H3_CHECK_HOOK`, `H3_DURATION`. API keys never go in it: `mcp.mjs` reads `.env.local` itself when it starts.

| Setting | Set by the launcher to | What it changes |
|---|---|---|
| `H3_OUT` | the run folder | where every tool writes |
| `H3_PAINTED` | `1` painted, `0` launch | painted: no `check_prompt` or `join_film`; `make_soundtrack` takes `effects` and fractional `parts` and moves seams into pauses |
| `H3_FOOTAGE` | `1` when the brief has footage | `make_soundtrack` takes `talk_edit` and `song` can be the user's video; with the hook on, `user_video` carries the EDIT.json format |
| `H3_REFS` | `1` when the brief lists the user's references | the tools say how a user's file is used; files in `<run>/attached/` |
| `MAPS`, `MAPS_CARD` | `1` and the card id, every painted film | registers `map_shots`; `make_soundtrack` also writes `soundtrack/soundtrack.json` |
| `H3_CHECK_HOOK` | `1` when `planner-hooks.json` exists and `PLANNER_CHECK_HOOK` is not `0` | `check_prompt`'s text says the write hook already checks |
| `H3_CALL_LIMIT_S` | `1750` | the "STILL WORKING, call again" reply |
| `H3_BUDGET_USD` | `0` from `auto.mjs` | `generate_video` refuses |
| `RATIO` | the film's frame | still canvas, Nano Banana aspect, code-clip size |
| `H3_DURATION` | the set length | `make_soundtrack` refuses another `duration` |
| `STORYBOARD_INLINE`, `FOOTAGE_COMPACT`, `EDIT_LIST` | passed only if set (all on by default) | `=0` turns off inline storyboard pictures, compact `user_video` results, the EDIT.json note |
| `H3_ACCURACY` | not set (`fetch`) | `ground` asks Nano Banana to search Google itself (does nothing on the default fal route) |
| `CODE_SHOTS` | never in practice | would add `map_clip` and `map_stills`; crashes the server (11.3) |

### 3.6 The hooks

`agent/h3film/planner-hooks.json`, passed as `--settings`:

```json
{ "hooks": {
  "PostToolBatch": [ { "hooks": [ { "type": "command", "command": "node \"$REPO/agent/h3film/planner-stop.mjs\"", "timeout": 60 } ] } ],
  "PostToolUse": [ { "matcher": "Write|Edit|MultiEdit", "hooks": [ { "type": "command", "command": "node \"$REPO/agent/h3film/planner-check.mjs\"", "timeout": 300 } ] } ]
} }
```

Both read `H3_OUT` and log one line per decision to `<run>/planner-hooks.log`.

**After every file write: `agent/h3film/planner-check.mjs`.**

- A write of `<run>/EDIT.json` runs `build-edit.mjs` at once (1.5.3). The answer rides back with the write: either what is wrong ("Fix these in EDIT.json: every write of it is built and checked again") or that `prompts/clip1.txt` to `clipN.txt` and `render.json` are written from it word for word, not to write them by hand, and that `NOTES.md` is next.
- A write of `<run>/prompts/clip*.txt` in a launch film whose text contains the exact string "Software launch film" runs the arrival check (below) and reports the prompt's length against the 20,000-character cap; over the cap it says to rewrite the whole file once, cutting only what repeats the rows.
- The clip-prompt check never runs on a painted film.
- `PLANNER_CHECK_HOOK=0` turns it off.

Why (10-10): launch planners had called `check_prompt` after each prompt and each fix, one small request at a time at 230-300k tokens of context: 3-7 extra requests a film ($0.11-0.29). One planner trimmed an 11,032-character prompt against a stale 10,000 cap with ten edits over four requests, about $0.40 of a $1.93 film.

**The arrival check: `uncoveredRows(text)` in `agent/h3film/check-prompt.mjs`.** It lists every row that brings something into the film but names no Image the prompt attaches:

- a row is a line starting with a time: `/^\d+(\.\d+)?(\s*-\s*\d+(\.\d+)?)?s\b/` ("2.7-3.3s — …", "3.6s — HARD CUT: …");
- it brings something in when it matches `appears`, `arrives`/`arriving`, `enters`, `pops (in)`, `opens`, `draws itself`, `writes itself`, `fades up/in`, `rises in/up/from/into`, `blooms`, `lands dead/in/on/centred/from/as`, `slides in`, `drops in`, `is pressed`, `pressed`;
- not counted: camera rows ("— the frame/eye/camera/view …", optionally after "HARD CUT:") and a shot that opens on an empty, blank, bare or plain field;
- it is covered when it cites an Image line the prompt has (`Image 4`, `Images 3 and 4`, `@Image 4`) or quotes a string that one of the prompt's "Image N is …" lines contains.

Why (09-29): over five films, both leaks of another product's interface sat on an arrival row with no still; with no picture, H3 paints that moment from the reference video. The two approved films had no such row. Launch films only: on painted films every flag was false (sample stills are style references that rows never cite) and planners weakened their motion to pass it (10-04).

**After every batch of tool calls: `agent/h3film/planner-stop.mjs`.** It ends the session right after the batch that finishes the film, by printing `{"continue": false, "stopReason": "Film planned: … The runner renders it now."}`. Why (10-10): all 35 planners of a batch spent one more request on a chat summary nothing reads. It decides only after a batch that writes `render.json` or `EDIT.json` (or any write after such a batch that did not stop), and stops only when all of these hold:

1. No call in the batch failed (a `<tool_use_error>`, or Bash "Exit code N"), and the batch called nothing but file writes, Read, Glob, Grep, Bash or `check_prompt` (a hook cannot see an MCP tool's failure).
2. Every write of the batch is on disk as written.
3. With EDIT.json: `EDIT.built.json` shows a clean build of exactly that EDIT.json.
4. `render.json` parses and has clips.
5. Every file it names exists and is not empty (any string that is an absolute path or ends in a media, text or JSON extension), except files under `<run>/maps/`, which arrive after the session. If any is missing, the hook tells the planner every missing path and that Read cannot check a video. Why (10-10): one planner wrote three made-up clip paths, "checked" them with Read and ended; the film never rendered.
6. No clip attaches a frame from `<run>/reference/`.
7. Every clip prompt it names was written by this session (a resumed session must not stop on old prompts).
8. `NOTES.md` exists (`PLAN.md` is not required: 4 of 35 planners never wrote one).
9. Prompts that use `@@` blocks have them (below).
10. A launch film (`kind` not `painted` and no footage videos) has no row render-all would refuse (the arrival check on every H3 clip, with no "Software launch film" gate).

State between batches is in `<run>/planner-stop.state.json`. `PLANNER_STOP=0` turns it off. `planner-stop.mjs` exports `decide(run, calls, io, state)` for replays over old transcripts.

**Dormant: `agent/h3film/expand-prompts.mjs`.** Both hooks can read clip prompts that use shared blocks (a line `@@<name>` standing for a block in `prompts/_shared.txt`). Nothing tells the planner to write them, and nothing expands them before the render. Treat such lines as an error.

### 3.7 After the session

1. If `EDIT.json` is newer than `render.json` (the hook timed out or the last build failed), the launcher builds it now; if it does not build, it stops without rendering.
2. Writes `t1`. Exits 1 on `FAILED.json`, a non-zero session exit, or no `render.json`.
3. If `map_shots` started the map engine (`<run>/maps/request.json`), waits for `maps/done.json` or `maps/failed.json`, checking every 15 s; a map process that died with neither gets a `failed.json`. Writes `t-maps`.
4. With a frame other than 16:9, writes `"ratio": "<RATIO>"` into `render.json` whatever the planner wrote.
5. Renders only with a budget above 0 (never from `./film`). Writes `t2`.
6. `agent/h3film/reading-report.py` prints what the session read (skipped required files, cast components never opened: a report, not a gate), a usage summary is printed, and `manifest.py session` adds the `session` block.

Then `auto.mjs` retimes lyric rows when needed and runs render-all (1.1).

### 3.8 The instructions the planner follows

The rules live in layers. When they disagree, the newer and closer one wins in practice: tool descriptions and the card are followed over skill prose (learned on the Gemini planner, 09-29 and 09-30; the image tool's rules are what fixed product stills). Put a new general rule in the first layer every affected film reads, as one positive sentence.

| Layer | Files | Reaches |
|---|---|---|
| Launch path | `skills/h3-film/SKILL-gemini.md` | launch films whole; every other film only its opening role lines |
| Painted path | `skills/h3-film/PAINTED.md` | every painted film except `bold-flat-poster` (`MINIMAL.md`) |
| Footage | `skills/h3-film/FOOTAGE.md`; `FOOTAGE-swap.md` for a swap (1.3) | every brief with footage |
| The user's references | `skills/h3-film/REFERENCES.md` | briefs that list them |
| Kind of film | `skills/h3-film/usecases/<id>.md` | painted films of that kind |
| Look | `agent/web/app/styles/cards/<id>.md`, `refs/<id>/` | films in that style |
| Tools | descriptions in `research/h3/mcp.mjs`, `tools-*.mjs` | every film that calls the tool |
| Launcher notes | `agent/h3-film-agy.sh` | as in 3.4 |

**`SKILL-gemini.md`: the launch path.** Its name is left from the Gemini planner it was written for; Claude follows it.

0. The brief. A non-launch film follows PAINTED.md (for `LAUNCH=1` the launcher's note overrides: the card is only the look). Fix length, aspect, whether the film speaks, style, product, URL, attached visuals. Invent no public claims for a real company.
1. The indexes: `CASTABLE.md` (the index for `LAUNCH=1`), `references/music.md` only if the brief names a library track. With a URL, `screenshot` up to four real product surfaces and look at them. A capture with browser chrome, an OS bar, a cookie banner or a marketing page is rebuilt with `image kind=edit` as its hero version.
2. `PLAN.md` in one Write. The style decides four things: the room (`glow`, `studio`, `spot`, `paper`, `gradient`, `flat`, `none`; the same in every still), the type, how surfaces sit, and the grammar of rows (framings for product films). Theme from the product's real site. Arc: claim, then the product shot that proves it, cause before effect. Cast only components in `CASTABLE.md`: 6-12 beats from their parts (`film/component/part`), each part at its own measured span (never stretched or squeezed), from at least three source films, no film more than half the beats, no three hot beats in a row, every seam one gesture. A film of 15 s or more carries at least one flagship component (★). Only the flagship beat gets the full recipe: a before-state still made from the same screenshot as its after-state, rows that name every arrival, its motion clip attached. H3 cannot do petal blooms, count-ups, a line growing from its centre, three discrete steps on the beat, moves under 0.5 s, or small text. Clips: 5-15 whole seconds, ending only on a hard cut; `seconds = ceil(span + 0.3)`, at least 5; the last real event ends at least 0.7 s before the clip ends; at most 6 images a clip. Fixed `PLAN.md` sections: `# <title> (<seconds>s)`, `## Style`, `## Theme`, `## Music`, `## Narration`, `## Beats` (`| t0 | t1 | parts | what happens | copy on screen | temp |`), `## Clips` (`| id | start | end | seconds | beats | images |`), `## Surfaces` (one `### id` per still).
3. Sound first: one `make_soundtrack` call; `parts` = the clips' spans (the seconds the film keeps), never their render seconds. The returned times are the clock. A narrator never shown is the house voice; a line said by someone on screen is their voice. The music prompt names a real genre and instruments and commits; no arrangement notes in seconds, no hedging words.
4. Stills. A product surface is the real screenshot redrawn as its hero version (`image kind=edit`, a keep-list prompt in the shape of `hero-edit-magic-hour-ugc-form.txt`); every later state is an edit of the previous still ("Return this exact image unchanged except …"); never a close-up or crop still; never an empty screen. A surface behind a login is drawn with `image kind=frame` in the product's design. Every on-screen line gets a type still (`still kind=text`) painted in the film's room; the end card is one designed `still kind=lockup`. Five or six images a clip is normal.
5. Read the cast components' `references/components/<id>.md` and `library/shapes/<id>.md`, `translate.md`, the template and the example films; then one prompt per clip: `references/template.txt` filled in, the component's proven rows verbatim with this product's nouns and times, every noun in a row something an attached still shows. Five checks before each prompt (seconds, spans, empty-field stills, the flagship before and after from one screenshot, a Video line per motion clip).
6. `render.json`, `NOTES.md`, stop. Never call `generate_video` or `join_film`.

Standing rules: never probe a rejection ("User is locked" or a top-up message is billing: stop and report); a number on screen carries what it counts; on-screen copy is 2-5 words; no two runs ship the same recognisable film.

**`PAINTED.md`: every other film.**

1. Read the card and the use case (pasted) and look at the card's `sheets/pool.jpg`. The card's Storytelling outranks the use case on voice, rate, hook and ending; the two rhythm rules and the text rule outrank both.
2. `PLAN.md`. Explaining films: 2-3 compositions per 30 s, each held and built up while it is explained. Beat films (event, logo, lyric): one picture per beat. Something visibly moves at least every second. Clips cut only where one picture ends and the next begins; 5-15 whole seconds; `span` = the clip's length in the film; `seconds = ceil(span + 0.3)`, at least 5; no narration line across a seam; a change of place is a hard cut (H3 cannot carry the camera to a far place the opening picture does not hold: it comes out as a black void or a rebuilt set). The film's own lead; one SETTING sentence with only what is true in every clip and the exact number of people; per clip the sample stills by the card's rule (at most 9, one ground always). Never a number above three for things the frame shows (asked for seven sailors, H3 drew eight).
3. Sound, one call: natural words, every fact from the brief; write the script, then read it once as a viewer who knows the real thing. `lines` at planned times, `duration`, `parts` = the clip lengths, `voice`, a committed `music_prompt`. Every row's time comes from the returned timings.
4. Stills. Anything given to a clip with no time is true for the whole clip: design stills and every line every clip repeats hold only what is true all film; a state goes on its row, in a state still, or in a pin.
   - A card with `## Content stills` (exact diagrams): one exact still per composition in one `storyboard` call, then each composition's before-state by `image kind=edit`. Each state still gets a full Image line with its time and is cited on exactly one row, the row that ends on it.
   - A card with `## Subject stills`: one design still per recurring object the sample pool lacks (at most 3) and one for every lead character who speaks or recurs (at most 5 a clip), in one `storyboard` call with `style` = the 3 sample stills that show the style best. Its line: "Image N is <the object>'s design: exactly how it is drawn in this film, at every size and angle. It is not a frame of the film." Rows never cite it or open on it; they call each character by the same short look every time. A character from a real film, show or game is its official picture (`reference_image`), never redrawn, and the prompts keep its name.
   - Otherwise the card makes no stills of its own except UI, labelled diagrams and real map stills, which every film draws first. Sample stills get one "Images N-M are STYLE references only" line and are never cited. A sample still showing a person goes only to a film that draws no characters of its own.
   - Pins (render.json `pins`): a pinned still is the picture at that moment and lands within about 0.5 s of its time; H3's own cuts land late or never. In a clip of several shots, each shot opens on its own pin (the first at 0), drawn as that moment looks, never reused; no pin inside a shot. Pinned stills of one place come from one master picture of it plus the characters' designs. A pinned still is not also attached and is never cited. Pins never replace designs: a clip attaches the design of every character it shows. A take that runs across a seam keeps its pinned still as the last pin of its clip and the first pin of the next; the renderer then renders the next clip after it, starting on its exact last kept frame.
5. One prompt per clip, under 20,000 characters, blocks in a fixed order (3.10). Every clip stands alone: no Video line for a previous clip, its own rows timed from 0. The picture fills the frame edge to edge; never letterbox bars.
6. `render.json`, `NOTES.md`, stop. Never `generate_video`, `clip_tail`, `assemble` or `join_film`.

**`FOOTAGE.md`: the user's own video.** (A swap reads `FOOTAGE-swap.md` instead: the same file as the approved swap films ran it, with the two swap-only rules marked below. 1.3.) Their video wins over anything above that says otherwise. Call `user_video` on each attached video first, with no start, and look at the whole contact sheet, the cuts and the transcript.

1. The use, from the brief's first word (with none: EDIT for speech or a person to camera, CLIPS otherwise):
   - EDIT: one stretch of their footage, opening on a hook and ending on its payoff, its dull middle cut with jump cuts; only what the brief asks is added. A short-form edit of people talking that should be engaging: a soft white flash into a punchline (once or twice), 3-5 B-roll inserts of 1-1.5 s painted by H3 showing what is said, their speech as captions (`{"speech": true, "place": "middle"}`), a music bed (`talk_edit`). Cuts need a reason; an unbroken take stays one shot until about 5 s, then changes picture only at a sentence start (an insert, or a held 1.4x punch-in, `"zoom": {"from": 1.4, "to": 1.4}`); a slow push-in carries across cuts. This applies even when the card says "only their footage".
   - CLIPS: their footage about every other clip, between painted clips; footage clips stay clean.
   - B-ROLL: our narration and music; their footage under every line about what it shows, at least a third of the film.
   - REFERENCE: only their look or content, no footage clips. Never when the request changes who is in it: that is an EDIT that restyles it, every clip carrying its segment as Video 1. Swap path only: a scene with several people remade in another look with someone new in it (a movie scene redone in Pixar style) is a painted film drawn from pinned stills.
   - MONTAGE (a highlight, hype, recap or sports edit, a promo cut from their clips, or any card whose first line is `footage: edit`): cut on the music's beats; every clip that adds something is an H3 edit; a shot with nothing added plays clean.
   - Every word on footage is a code caption (`"style": "title"` for titles); H3 never paints words onto footage.
2. Segments: one per footage clip, cut with `user_video` (start, duration = the clip's render seconds). A clean clip is not an H3 clip: `{"id", "footage": <segment>, "seconds", "span"}`. A clip that adds something: the segment is its Video 1, and the picture follows it second for second.
3. The prompt of a footage clip: clean unless the brief asks for something. Then: a style sentence about only what is added, then "Video 1 is the user's own footage of <what it shows>: keep it as the picture — the same people, places, framing and camera, second for second — and <the edit>." MOTION: "The footage keeps its own motion and camera; only the added graphics move". Images on a footage clip are only type stills, graphics, or the picture of who takes someone's place. A person swapped in gets a full design line in words, positively, the exact skin tone first, in their own clothes; a voice from someone off screen is named as theirs and the person in frame listens with lips closed. Pick shots where the person to change is big (a third or more of the height). Swap path only: live-action swaps of real people use MiniMax's own reference-prompt layout (3.10) and mark each clip `"swap": true`, with no pin at 0 s (render-all makes a swapped first frame).
4. Sound: an EDIT with speech uses the footage's own sound (`song` = the video, `song_start`, parts = clip lengths). A talking edit lays each kept stretch as a `{from, start, end, at}` line plus `music_prompt` and `talk_edit: true`. A MONTAGE is the music plus a few 1-4 s bites of the plays' own sound. A real person's words come only as real audio (their footage, or a clip found with `web_clip`), never written for our voices. A hook plays picture and sound from the same moment.
5. MONTAGE: H3 does the edit. Each shot is its own clip (a seam is exact on its beat; a cut inside a clip lands late and replays a moment). One segment per clip, `span + 0.3` long; the renderer pins its first frame. No sample stills. The prompt is the one `user_video`'s description gives. Only what moves in the footage moves: effects that change the real frame (punch, shake, flash, slow motion, speed ramp, blur) are fine; never a camera move or angle the footage lacks. A shot wider or taller than the film gets `frame`; a zoom is render.json `zoom`, built by the renderer (a row asking for a zoom paints nothing). A highlight edit tells a story: who they are before the drop, their best moments after it.

**`REFERENCES.md`: what the user attached.** Each reference has an @Name, a kind and files. The @Name is used in PLAN.md only, never in a still, a frame description, a line or a prompt. In a drawn film H3 gets stills drawn from the user's files, never the files; in a live-action film or an edit of real footage it gets their photos of people, things and places themselves, each with a full design line in words. Character and object: one subject still each (`storyboard`, `content` = their photos, `style` = 3 sample stills or the moodboard). Location: one frame of the place, empty. Brand kit: the logo only ever by `still kind=lockup` (`mark=` or `wordmark=`); its colour is the accent; a product screenshot is an `image kind=edit` hero; a physical product is an object. Moodboard: style references only, never content, never attached. Audio: `music=` is the bed under narration; `song=` is the whole soundtrack.

**`MINIMAL.md`.** A 2.4 KB sheet of facts about H3 with no row format or pacing rules, used only by `bold-flat-poster` (its best take, rated 8, came from it). It names the tools and the render.json shape.

**Use-case files: `skills/h3-film/usecases/`.** 21 files, each with the same 12 sections: what it is, inputs, defaults, arc (shares of the film), pacing, text, sound, opening and ending, what H3 cannot do here and the substitute, a worked example plan, pipeline gaps, evidence. Only painted films paste one.

| File | Menu section | Default |
|---|---|---|
| `explainer.md`, `documentary.md`, `tutorial.md` | Explainer, Documentary, Tutorial | 30 s |
| `map-video.md` | Map video | 30 s; its §0 (map shots) wins over everything below it |
| `event-promo.md` | Event promo | music only, no voice |
| `logo-animation.md` | Logo animation | one 10 s clip unless the brief says otherwise |
| `lyric-video.md` | Lyric video | a 30 s window of the song; plain-subtitle lyrics are one code caption `{"lyrics": true}` |
| `ambient-loop-uc.md` | Ambient loop | one held calm picture |
| `baby-sensory-uc.md`, `size-comparison-uc.md`, `stick-action-uc.md`, `storytime-uc.md`, `cgi-space-uc.md` | Baby Sensory, Size Comparison, Action short, Storytime, Space Epic | 30 s |
| `comedy-short-uc.md`, `raise-beast-uc.md`, `viral-short-hi.md`, `viral-short-v3.md`, `sports-edit-uc.md` | Comedy Short, Creature What-if, Viral short hi, Viral short v3, Sports Edit | 30 s, 9:16 |
| `fruit-drama-uc.md` | Fruit Drama | 32 s, 9:16 |
| `fan-edit-uc.md` | Fan Edit | a 30 s window, every shot its own clip, 16:9 |
| `anime-music-video-uc.md` | none on the menu: never used | 30 s |

Launch films have no use-case file.

**Style cards and their example films.** `agent/web/app/styles/menu.ts` lists 85 styles; 77 have a card in `cards/<id>.md`. The folder also holds cards the producer wrote for looks it studied (their header says so). Kinds of card, by what they carry:

- Sample-pool card (house styles such as `bold-geometric`): a style sentence (the first line of every prompt), a pool of sample stills in `refs/<id>/pool/` with a tagged table, a labelled sheet `refs/<id>/sheets/pool.jpg` and a picking rule, a verbatim job line and no-copy line, often an ink line (a fixed colour per thing, so colours hold across clip seams), `## Subject stills` rules, a MOTION block pasted verbatim into every prompt, `## Storytelling`, `## Never`.
- Named-genre card: a style sentence that names a genre H3 knows, plus a few stills.
- Clip card (`flat-pop`, `holographic`, `kinetic-wordmark`, `line-draw-on`): the style is a motion, so `refs/<id>/clip.mp4` goes to every clip as Video 1 with the card's job line and no style text. The only painted films that get a style reference video.
- Content-stills card (`system-diagram`, `clean-infographic`, `fireship-100s`, `how-to`, `illuminated-manuscript`, `instruction-manual`): one exact still per composition.
- Design-world card (`2-5d-hybrid`, `editorial-motion-graphics`, `paper-collage`): forks `refs/<id>/exemplar-prompt.txt` block for block.
- Footage-edit card (a `footage: edit` line under its title, 5 cards): the user's footage is the look; nothing painted.
- Studied-look card: written by the producer for one film (2.13).

57 cards end with `## Approved example (8+)`: a film rated 8 or more in that style, whose `PLAN.md` and clip prompts sit in `refs/<id>/example/` (59 styles have that folder). It is pasted after the card as the quality bar and the shape to match, never its topic, story, objects, words or beats; a launch film pastes only its `clip*.txt`. Each card was frozen at the exact text that made its example, so editing a card changes what its example proves.

**The launch library.**

- `agent/h3film/library/CASTABLE.md` (82 KB): the only components a launch film may cast, 60 of them, grouped by role (FLAGSHIP, OPEN, LINE, ASK, SHOW, PROVE, REVEAL, TRAVEL, TURN, CLOSE, SCAFFOLD, OTHER), 10 marked ★ (flagship). Each entry: `**<id>** <film> <flat|3D> <length> — <what it is>`, a `NEEDS:` line (what its stills must show), its parts with their spans (`the whip down the plane 1.53–1.83 | …`), and `✗` for what H3 cannot paint with the substitute. By source film: Orchids 20, Blossom 12, GoConfirm 9, beehiiv updates 9, Ghost Note 5, Chatbase 4, Framer Agents 1. `CASTABLE-index.md` is the same without the NEEDS lines (41 KB, re-read on every request; picked from as well as the full list, 10-10).
- `agent/h3film/library/shapes/<id>.md` (62 files): each component's proven H3 rows, with the reference clip and the stills its proof used. Opus rewrote 38 of them offline (`library/proven/`).
- `skills/h3-film/references/components/<id>.md` (92 files): what each component does, part by part.
- `skills/h3-film/references/motion.md`: the motion clip of every component (`ingest/<film>/run/*-ref.mp4`, `research/lab/run/*-ref.mp4`, `agent/h3film/library/proven/*/ref.mp4`), attached as a Video with "Video N is the MOTION of beat N — its camera, its arrivals, its pacing. Not its product, its colours or its type." At most 3 a clip, 15 s in all.
- `skills/h3-film/references/translate.md`: how a component's code times become rows (it points to `agent/h3film/RULES.md` and `research/h3/prompts/orchids-reveal/GUIDE.md`).
- `skills/h3-film/references/template.txt`: the launch prompt template (3.10).
- `agent/h3film/exemplars/films/`: two whole approved films, every clip prompt (Magic Hour v13, 3 clips; Orchids, 8 clips). `exemplars/hero-edit-magic-hour-ugc-form.txt`: the approved hero-edit prompt.
- `agent/refs/<product>/`: logo packs (`logo-mark.svg`, `logo-word.svg`) for 17 products.
- `ingest/orchids/compositions/screens/endcard.html`: the default end card layout.
- The code versions of the components (`framework/components/` in the lab) are not in this repo; nothing a film runs needs them.

### 3.9 The tools

One MCP server, `research/h3/mcp.mjs` (`McpServer` "minimax-h3" over stdio), registers tools from itself and `tools-film.mjs`, `tools-footage.mjs`, `tools-codeshot.mjs` and, with `MAPS=1`, `tools-maps.mjs`. Every description is planner instruction. What each kind sees (measured with MCP `tools/list`, description lengths in characters):

| Tool | Launch | Painted | Description length |
|---|---|---|---|
| `make_soundtrack` | yes | yes (+ `effects`; + `talk_edit` with footage) | 452 launch, 1,113 painted |
| `storyboard` | yes | yes | 2,017 |
| `image` | yes | yes | 5,211; 5,633 with `H3_REFS=1` |
| `still` | yes | yes | 997 |
| `reference_image` | yes | yes | 802 |
| `screenshot` | yes | yes | 362 |
| `user_video` | yes | yes | 6,367; 9,460 with the EDIT.json note |
| `web_clip` | yes | yes | 719 |
| `code_clip` | yes | yes | 5,255 |
| `map_shots` | no | yes | about 1,840 (it names the card's map look) |
| `check_prompt` | yes | no | 801 with the hook note |
| `join_film` | yes (never used) | no | 267 |
| `generate_video` | yes (never used) | yes (never used) | 320 |

Launch films get 12 tools, painted films 11.

Shared behaviour:

- **Pictures come back.** `screenshot`, `reference_image`, `still`, `image` and `storyboard` return a small JPEG (up to 640 px) as MCP image content plus the `.view.jpg` path (at most 1216 px on the long side), so the planner sees what it made. Prompts and `render.json` name the full-size file. `user_video` and `code_clip` return contact sheets.
- **Two kinds of failure.** A mistake the planner can fix comes back as an error result with what to change. A provider, render or account failure is fatal: the tool writes `FAILED.json` and answers "RUN STOPPED … end the session now" (1.7). Films had shipped without their narration, a trophy or every photo when a provider ran dry.
- **Refused pictures.** A picture refused for its content is retried, then returned as `FAILED <name>: <fal's reason>` plus a hint: a refused picture usually names a film, cartoon or game character; its design is its official picture (`reference_image`); other pictures describe them by look with no names; clip prompts keep the names (10-11: sixteen frames came back with no reason and the planner guessed for three rounds).
- **Nano Banana runs on fal.** `quotaWait()` in `tools-film.mjs` sends every Nano Banana call to fal (`fal-ai/nano-banana-2.1`, or its `/edit` route when pictures are attached) unless `NANO_BANANA_VIA=vertex` (Vertex refused every request on 10-09). `GOOGLE_VERTEX_PROJECT` must still be set for the client to start. Model `NANO_BANANA_MODEL`, default `gemini-nano-banana-2.1`; $0.0336 an image at 1K. Results are cached by content hash in `agent/artcache/`.
- **Lyric ids** in any argument are replaced by their words before the tool runs.
- **The user's attached files** (`<run>/attached/`) are refused by `still` and `generate_video` as pictures: a drawn film draws a still from them. Live-action films and footage edits attach the user's photos directly in `render.json`; render-all allows that.

**`make_soundtrack`** (`mcp.mjs`, `research/h3/soundtrack.mjs`): the film's finished soundtrack, built before any prompt, in one call. Inputs, behaviour and the mix are in section 4; its answer is in 1.5.6.

**`storyboard`** (`mcp.mjs`): Nano Banana draws stills from frame descriptions. One call draws up to 9 frames: frame 1 first, then the rest at once.

| Input | Notes |
|---|---|
| `look` | 2-4 sentences, applied to every frame |
| `frames[]` | `{name, description, use?, shots?}`. The description is a picture, not an event: what is where, which way it faces, every string in double quotes. `use`: which `references` this frame gets. `shots`: 2-3 `reference/ref-NN.jpg` files whose framing fits, for a film whose look comes from a real video (in place of `style`) |
| `references` | up to 6 product screenshots (launch edit mode: screenshots placed as flat cards in a 3D scene) |
| `style` | up to 3 style references (Nano Banana's limit) |
| `content` | up to 3 real photos or diagrams (saved with `reference_image`) whose parts, order and count the frame copies, in the style's look; or one user reference's photos |
| `compositions` | `true` only for a content-stills card |
| `ground` | Google search grounding (does nothing on fal) |

Its description, for every film: a technical subject is looked up on the web first and its real parts written into frames and rows; one real diagram is fetched with `reference_image` and passed as `content`. Every piece of UI a shot shows and every diagram with labelled parts is drawn here first, alone, every word in quotes, and attached to the clips that show it (10-08: described in words, a browser came out with two address bars). Code: `style` plus `references` draws the screenshots in the style instead of edit mode; a frame with no references of its own is drawn with frame 1 attached so the film stays one drawing; quoted strings become an exact text list (each set at least a twentieth of the frame tall), and a frame with no quotes gets "There is no text anywhere in the frame". Output `{frames: [paths or "FAILED …"], views, rule?}`; files `storyboard/NN-<name>.png`. Pictures are also sent inline (`STORYBOARD_INLINE`, on: planners had opened 100 of 101 frames with a request each, 10-10).

**`image`** (`tools-film.mjs`): Nano Banana 2.1 with a wrapper per `kind`. Inputs: `name`, `kind` (`frame`, `edit`, `cutout`, `backdrop`, `diagram`, `free`), `prompt`, `refs` (up to 14), `aspect`, `size` (`1K`, or `2K` only for a still shown full-frame by code). Its description: never draw the product's logo, symbol or name as lettering (the film has one logo: the one `screenshot` captured or the brief gives, shown by `still`); a still of the product's screen is always `kind=edit`; the hero is one call per screenshot whose prompt is only a keep-list (every element that stays, with its string, region by region, then what goes), never a background; every later state is an edit of the previous still starting "Return this exact image unchanged except …"; never a close-up or crop still; every product still shows the product in use; never invent a screen the product lacks; regenerate anything with a wrong label, an invented element or a broken layout. It carries the approved Cal.com hero and state prompts as worked examples. Code: an `edit` of a real screenshot adds the hero wrapper (fill the frame edge to edge, no container) and the screenshot's sampled ground colour; an edit of the run's own still is sent as written. `cutout` is matted to a transparent PNG with rembg. Output `{file, kind, cached, cost_usd, view}`; file `images/<name>.png`.

**`still`** (`tools-film.mjs`, `agent/h3film/still.mjs`): exact pictures rendered in HTML with HyperFrames: `text` (a type still), `lockup` (the end card), `surface` (an image placed in the film's room), `screen` (an ingested film's HTML screen), `blank` (the empty room). The room is painted as pixels the same way in every still. Fields and rules are in 6.13.

**`reference_image`** (`mcp.mjs`): saves one real picture from a direct image URL (PNG, JPEG or WebP) into `refs/<name>.<ext>` and returns it, so the planner checks it shows the subject. Its description: a map shot starts here (a real map of the tightest area, Wikimedia Commons first, then redrawn by `storyboard` in the film's look, with no words); a named character's design is its official picture, attached as it is, never redrawn first.

**`screenshot`** (`mcp.mjs`): Playwright Chromium at 1280x800, device scale 2 (a 2560x1600 PNG), after network idle plus 2.5 s; one browser per session. It also saves the site's logo: `shots/logo.png` (as the site draws it), `logo-mark.svg`, `logo-word.svg`, and the site's app icon. Inputs `url`, `name`, `full_page`, `scroll_to`. Output `{file, view, url, logo, logo_mark, logo_word}`.

**`user_video`** (`tools-footage.mjs`, registered in every film): inputs `file` (a local path as the brief writes it, or a URL, downloaded once with yt-dlp at up to 1080p into `footage/<stem>-src.mp4`), `name`, `start`, `duration` (0.5-15), `segments` (many `{start, duration, name}` in one call), `as_edited` (run through the source's own cuts, for a known meme or clip shown whole).

- With no start: the overview: length, size, whether it has sound, scene cuts (ffmpeg scene score above 0.3), the speech as timed phrases (`transcript()`), and a contact sheet of 8-20 frames labelled with their times.
- With a start: cuts each segment into `footage/<stem>-<start>s-<length>s.mp4` (video only, at most 1080 rows, CRF 18), ending it at the source's next scene cut, and returns frames from the part that plays plus the speech inside it, times from 0. A cut inside the part that plays is reported with the longest span that fits.
- Its description is the footage playbook: clean clips go in directly; a clip with additions is an H3 clip whose prompt opens with a style sentence about the additions and the job line; a montage prompt plays the footage as filmed. It opens "A vertical <kind of edit> made only of the user's real footage, played as filmed: real video with its own colours, light and on-screen graphics, nothing redrawn."; job line "Videos 1-N are the user's own footage. Play them exactly as they are, the same frames, people, plays, camera angles and colours, in this order, cut on the beats of Audio 1. Nothing is added to the picture except the edit effects the rows name: no new frames, players, angles, overlays, glows or drawings." (one-shot clips: "Video 1 is the user's own footage. Play it exactly as it is, the same frames, people, camera angle and colours. Nothing is added to the picture except <its edit moves, or nothing at all>: no new frames, people, angles, overlays, glows or drawings."); audio line "Audio 1 is the finished soundtrack: keep it verbatim."; and rows that are an edit list on the beats. A run of cuts faster than one a beat is one row giving the rate in beats (asked for 24 quarter-second cuts one row each, H3 made 2).
- With `H3_FOOTAGE=1`, the hook on and `EDIT_LIST` not `0`, it ends with the EDIT.json format (1.5.3).
- Results are compact lines (`FOOTAGE_COMPACT`, on: a night's 8 edits went from 292 to 153 KB of tool text that every later request re-reads).

**`web_clip`** (`tools-footage.mjs`): a YouTube search with no API quota (`ytSearch()`, 2.9). Inputs `query`, `short`. At most 6 searches a film (one planner had made 38). Returns url, title, channel, views and length for every result (about 55; the description says up to 8). Then `user_video` with the URL downloads and transcribes it. Films that are not edits use such a clip for its audio only, as a `make_soundtrack` line.

**`code_clip`** (`tools-codeshot.mjs`): one shot written as HTML and GSAP, rendered with HyperFrames, for what H3 truly cannot paint (a simulation whose outcome is the point, a chart of real numbers). Section 6.12.

**`map_shots`** (`tools-maps.mjs`, painted films): sends the moving-camera map clips to the map engine. Section 6.2.

**`check_prompt`** (`tools-film.mjs`, launch films): input `file`; output `{ok: true}` or `{ok: false, uncovered: [rows]}` by the arrival check (3.6). A prompt without "Software launch film" returns ok. With the hook on, its description says to use it only to re-check after a fix.

**Registered but never used by `./film`:**

- `generate_video`: one clip on fal (default) or MiniMax's own API (`H3_BACKEND=direct`), waiting 3-10 min, behind a spend gate (`<run>/spend.json`) that refuses everything at `H3_BUDGET_USD=0`. Frame mode (`first/middle/last_frame`) and reference mode cannot mix; fal needs reference videos of 2-15 s, 15 s in all.
- `join_film`: joins finished clips under the soundtrack (launch films only).
- `map_clip`, `map_stills`: only with `CODE_SHOTS=1`, which crashes the server at start (11.3).

### 3.10 The H3 clip prompt

One plain-text file per H3 clip, `prompts/clipN.txt`. H3 gets it word for word.

**Rules for every prompt.**

- References by number: "Image N" is `images[N-1]`, "Video N" is `videos[N-1]`, "Audio 1" is the clip's `audio`. Every attached reference has a line saying what it is and its job, in array order. Pins are not references: no line, never cited. The H3 node labels references `<Picture N>`, `<Video N>`, `<Audio N>`; render-all rewrites a prompt to those tags only for swap clips (5.2 step 5).
- Limits per clip: at most 9 images (launch films 6), 3 videos, one audio.
- Rows: `<a>-<b>s — <what happens>`, in the clip's own seconds from 0, coarse (tenths), about one row a second (launch films 1.5-2 a second). Two-decimal rows landed 1-2 s off and rows with no times were worse (09-17). Cuts are "HARD CUT:"; holds say "Held."; painted clips end "Held still from <t> s." The last real event ends at least 0.7 s before the clip ends: H3 runs about 0.4 s late and drops a last event that comes later.
- Framings, not camera verbs: each row says what fills the frame, where, how large as a share of the frame, and what happens. Camera verbs and waypoints are ignored (09-15/16).
- Every noun can appear on screen: name only what the shot shows. Describe what to show, positively, the distinctive things first (10-12: "not X" clauses gave the same film as positive wording; a more exact positive word fixed it).
- Words: exact text comes from stills or code captions; every string quoted; a COPY LIST of exact strings. H3 garbles words it animates or invents.
- Counts: three or fewer of anything that must be counted.
- No file paths and no @Names of the user's references in a prompt.
- Length: under 20,000 characters (Magic Hour's cap). Only the launch write hook checks it. Measured in this repo: launch prompts median 8.4 K characters (max 11.7 K), painted 4.0 K (max 11.8 K), footage 2.5 K.
- Lyric videos: lyric lines are written as ids (`[L3]`, `[L11:1-6]`). Every lyric line on screen is a type still (`still kind=text`, text = the id) cited on its row; each line takes an arrival row of about 0.5 s ending on its picture, then a hold row citing nothing; at most 4 lyric lines and 9 images a clip (H3 slips about 0.5 s per line change; a 7-line clip ended 2.5 s late); never words revealed one by one; nothing asked to land "on the beat". Plain-subtitle lyrics are one code caption `{"lyrics": true}` instead.

**Launch film layout** (`skills/h3-film/references/template.txt`), filled in slot by slot, every sentence outside the slots kept exactly:

1. "Software launch film, 16:9, <seconds> seconds, fast punchy product-film pace, every move short and decisive, with the hard cuts named below. One <light|dark> room: <what this clip shows>. Every surface is a crisp flat 2D surface; the camera is the only depth."
2. One "Image N is <what it is, when it appears>. It is the design: this layout, this type, these colours, exactly, at every distance and angle." per still; then "Each surface appears only at its own moment named below; before that it is not in the film."
3. "Audio 1 is the soundtrack: keep it verbatim. Cut on its beats."
4. "Video N is the MOTION of beat n (t0–t1 s) — its camera, its arrivals, its pacing. Not its product, its colours or its type." per motion clip.
5. THE ROOM (the backdrop as in Image 1, a still picture), THE APPLICATION (a flat page floating in front, casting a soft shadow), THE HEADLINES.
6. BEAT SHEET, 1.5-2 rows a second: every row says what fills the frame with a fraction, every string quoted from its still; every row that brings something in lands on its Image; physics words only in the flagship beat; holds "Held."; cuts "HARD CUT:"; every beat opens on its first event arriving.
7. TYPE, COPY LIST, LINES, CONSISTENCY, CAMERA & MOTION, RENDER blocks.

Aim for 8-9.5 K characters; when long, shorten the Image lines and the blocks that restate them, never the rows. The two whole example films show it filled.

**Painted film layout** (`PAINTED.md` §5):

1. The card's style sentence (or its clip job line).
2. The sample pool's job line and the card's no-copy line ("Images N-M are STYLE references only …"), with the clause that everything in the film, including every thing no reference shows, is drawn in this style.
3. The ink line, if the card has one.
4. The Image lines: design stills ("Image N is <the object>'s design: …"), state stills ("Image N is composition <X> as it opens: … It appears at <start> s. It is the design: this layout, these shapes and levels, exactly." / "Image N+1 is the SAME picture once its builds are done: <only what changed>. Reached at <t> s.").
5. The audio line: "Audio 1 is the finished soundtrack: keep it verbatim, cut on its beats, each spoken line lands on the row it names. Do not add narration, music or sound effects." (Lyric videos use the use case's song line.)
6. The TEXT line.
7. The card's MOTION block, verbatim.
8. The SETTING line, word for word the same in every clip.
9. `SHOTS (<ratio>, <seconds> s, timed to the soundtrack):` and the rows. Each composition opens on its before-state still or a picture in words that already holds everything later rows use. A line said by someone on screen plays over their face with "lips moving" on every row of it; an off-screen voice is named as that speaker's on every row it plays over, and the person in frame listens, lips pressed together, with a clear expression.
10. The COPY LIST.

A clip card: its clip in `videos` with its job line and no style text. A design-world card: its exemplar prompt forked block for block. PAINTED.md carries one filled example (a Vox-style explainer clip) for its shape only.

**Footage clip layouts.**

- Clean: no prompt at all (a `footage` clip).
- Something added: the style sentence about only the additions, the job line, the footage MOTION line, rows naming what is added and when.
- Montage shot: the opening line, job line, audio line and edit-list rows from `user_video`'s description, written once as EDIT.json's `template`.
- Live-action swap (FOOTAGE rule 3, swap path only): MiniMax's own reference-prompt layout (from MiniMax's reference-prompt writing guide in the MiniMax-H3 model repository, `docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md`) with the node's tags, six sections in this order: `subject_definitions:` (one line per person who changes: "<Subject 1> is <name>, whose appearance comes from <Picture 1>: <who they are at a glance from the photo>, and whose movement, position, size in the frame and mouth movements come from <the filmed person> in <Video 1>."; one line for everything that stays; "<Video 1> is the source video for the target video edit."; "<Audio 1> is the clip's own soundtrack and is reused as it is."), `summary:`, `retention_analysis:` (`attribute_transfer`, `fully_preserved`, `fully_copy`), `detailed_description:` (`[Shot N]` lines, speakers as `(S1)` with `<d>[English] <words></d>`, later shots opening "At MM:SS.mmm"), `overall_soundscape:`, `non_diegetic_music:`. The clip is marked `"swap": true` and has no pin at 0 s; only clips so marked get the swapped first frame and the tags (5.2).

## 4. Sound, captions and the join

Sound is made first, in one tool call, and every later step is timed to it. The planner writes its prompt rows from the line times the call returns. H3 draws each clip against that clip's slice of the finished soundtrack, held fixed. The join plays the same soundtrack once under the whole film. The film's sound is only that soundtrack: whatever audio H3 returns with a clip is dropped at the join. So every voice, piece of music, sound effect and piece of real audio a film has must go through `make_soundtrack`.

### 4.1 Files

| File | What it does |
|---|---|
| `research/h3/soundtrack.mjs` | `makeSoundtrack()`: voices, music, sound effects, the mix, seam placement, one audio part per clip, the beat grid. Also `clipTail()` (a clip's last 3 s, for the legacy `chain` mode) |
| `research/h3/mcp.mjs` | the `make_soundtrack` tool: its parameters and their descriptions (planner instructions), the length check, the write of `soundtrack/soundtrack.json`. It also puts the sung words in place of `[Ln]` ids in every tool's arguments (4.11) |
| `research/h3/voices/` | `narrator.mp3`, `narrator-f.mp3`, `young-m.mp3`, `young-f.mp3` (samples for Magic Hour's voice cloner), `mh-presets.json` (1,266 Magic Hour preset voice names), `native.json` (native Hindi and Japanese ElevenLabs voices) |
| `agent/music/` | 5 library beds, each with a `.music.json` beat file, and `INDEX.md` (their sources). The tool server does not start without this folder |
| `research/tools/analyze_music.py` | beats, downbeats and per-bar loudness bands of a music file (madmom and librosa; always run with `ALLIN1=0`) |
| `research/h3/tools-footage.mjs` `transcript()` | speech to text of a file, or a fetched song's synced lyrics (2.9) |
| `agent/h3film/fetch.mjs song` | a song and its synced lyrics (2.9) |
| `agent/h3film/auto.mjs` | the producer: each sound file's kind and words, a song's `.vtt`, the film's set length (`H3_DURATION`), the lyric retime before the render |
| `agent/h3-film-agy.sh` | runs `lyric-ids.py`; passes the sound settings to the tool server |
| `agent/h3film/lyric-ids.py`, `lyric-retime.py` | a song's `.vtt` to `[Ln]` ids; lyric rows moved to their sung times |
| `agent/h3film/build-edit.mjs` | gives each montage shot its audio |
| `agent/h3film/render-all.mjs` | expands the caption entries and calls the join |
| `agent/h3film/join.mjs` | frame-exact cuts, captions drawn with Pillow, the soundtrack laid once, the exact length |
| `assets/fonts/` | Inter Bold and Inter Light: caption and title fonts where the macOS fonts are missing |
| `research/h3/runpod/comfy_r2v.py` | holds each clip's audio fixed inside H3 (5.3) |
| `skills/h3-film/PAINTED.md` §3, `FOOTAGE.md` rules 1 and 4, `SKILL-gemini.md` §2-3 | what the planner is told to put in the call (4.3) |

### 4.2 How sound moves through a film

1. The producer session sees each uploaded sound file as the words heard in its first minute (it cannot hear) and returns its `audio` kind: `song`, `instrumental`, `speech`, `mix`, or `none` (left out). The session fetches a real song when the film needs one (`fetch.mjs song`). `auto.mjs` then transcribes speech, mixes and songs, writes a song's sung lines as a `.vtt` (4.11), copies uploaded pictures and sound files (and a fetched song, when the user attached none) into `<run>/attached/`, and writes into the brief which `make_soundtrack` input takes each file (2.14). With `--duration N`, or with `DURATION=1` (2.15), it sets the film's length, passed on as `H3_DURATION`.
2. For painted films the launcher runs `lyric-ids.py` on every `.vtt` path in the brief. For every film it passes `H3_PAINTED`, `H3_FOOTAGE`, `H3_REFS`, `MAPS`, `H3_DURATION` and `VOICE_PROVIDER` to the tool server (`mcp.json`, 3.5).
3. The planner writes the script, makes ONE `make_soundtrack` call for the whole film, and writes every row from the times it returns.
4. `make_soundtrack` writes `<run>/soundtrack/` (1.5.6) and returns where each line landed, the final clip spans, the beat grid and notes.
5. The planner writes `render.json`: `music` = `soundtrack.mp3`; each clip's `audio` = its `part_N.mp3`; `span` = that part's length; `captions` if the film has any. For a montage, `build-edit.mjs` writes it from `EDIT.json` (4.9).
6. Before the render, `auto.mjs` runs `lyric-retime.py <run> 0` when the run has `lyrics.json`, `soundtrack/song.json` and clip prompts with `[Ln]` ids.
7. render-all renders each H3 clip with its part held fixed as its own sound, expands the captions and calls `joinFilm()`.
8. The join cuts each clip to its span on the frame grid, draws the captions, plays `soundtrack.mp3` once from 0 s and writes `final-gpu.mp4`.

### 4.3 The `make_soundtrack` call

What the planner sees depends on the kind of film. Launch films (`H3_PAINTED=0`) get the short version. Painted films (every other film, edits and lyric videos included) also get `effects` and fractional parts. Painted films with footage (`H3_FOOTAGE=1`) also get `talk_edit`.

| Parameter | Type, limits | Films | Meaning |
|---|---|---|---|
| `lines` | array, default `[]` | all | one entry per sentence or beat, in film order |
| `lines[].at` | number ≥ 0 | all | requested start, film seconds. A line starts only after the one before ends (+0.25 s after a read), so long reads push later lines |
| `lines[].text` | string | all | the words read |
| `lines[].from`, `start`, `end` | path, seconds | all | real audio instead of our voice: the whole file (the user's video or recording, or a clip downloaded with `web_clip` and `user_video`) and the moment in it. At most 15 s; up to the film's length with `talk_edit`. A real person's words come only this way |
| `lines[].speaker` | string | all | a line said by someone on screen: the exact name of a Magic Hour preset (or, in a language Magic Hour cannot speak, a native voice from `native.json`). Left out for narration |
| `voice` | `narrator`, `narrator-f`, `young-m`, `young-f` | all; required on every painted call (even one with no lines), default `narrator` on launch films | who reads every line with no `speaker` and no `from` |
| `language` | ISO 639-1 | painted | the lines' language; left out for English. Launch films do not get it: the code guesses the language from the lines' letters (4.5) |
| `music` | string | all | a library bed name from `agent/music/`, or the path of a music file in `<run>/attached/` |
| `music_prompt` | string | all | generate the bed with ElevenLabs Music |
| `song` | path | all | the file is the whole soundtrack (4.6): a lyric video's song, the user's video whose own sound is the soundtrack, a finished mix; no lines, no music |
| `song_start` | number ≥ 0 | all | where in the song (or an attached `music` file) the film starts |
| `duration` | integer 4-120 | all | the whole film's length; must equal `H3_DURATION` when set |
| `parts` | painted: numbers 0.25-15; launch: whole numbers 4-15 | all | each clip's span in order, adding up to `duration`. Launch films give the clips' spans, never their render seconds |
| `effects` | array of `{at, sound, seconds?, from?, start?}` | painted | sound effects (4.7) |
| `talk_edit` | boolean | painted with footage | an edit of people talking: their speech carries the film and the music sits far under it |

The tool always passes `beats: true` and `snap: H3_PAINTED` (move seams into pauses, 4.9). It is marked `readOnlyHint`, so Claude Code runs it side by side with `storyboard` calls (3.3).

The painted description adds:

- The narrator reads about 2.2 words a second, and a long read pushes later lines back.
- Make one call per film. Give rough `parts`; the tool moves seams out of lines and returns the final spans.
- Build the plan from what the call returns, and never call again only to fix seams.
- No captions or subtitles (a running transcript of narration, dialogue or footage speech) in any prompt or still unless the request asks, because H3 garbles text. Code draws captions (4.12).

The `music_prompt` description, on every film: genre, mood, tempo, instruments, instrumental, short and concrete, written from the film's look; a piece of music somebody would want to listen to; no notes about seconds (the model ignores them); no hedging words ("muted", "restrained", "filtered", "subtle", "background" give a track with nothing in it). `PAINTED.md` §3 and `SKILL-gemini.md` §2 add: name a real genre and real instruments and commit to them.

Fixable refusals give a message, and the planner calls again:

- `duration` differs from `H3_DURATION`.
- no lines, music, music prompt or song.
- `music` is neither a library name nor a file in `attached/`.
- a `from` line whose file is missing, whose `end` is not after `start`, which is too long, or whose file has no sound (name the whole video: footage segments are cut without sound).
- a line with neither `text` nor `from`.
- a `speaker` that is not an exact preset name. The message offers the nearest names: asked for "Family Guy Peter Griffin", it offers "Peter Griffin".
- a `speaker` who cannot speak the film's language.
- voices that run past `duration` (the message lists every pushed line).
- a seam that cannot leave a line without making a clip shorter than 4 s or longer than 15 s.
- a missing `song` file.

The two refusals about running past `duration` and about seams come after the reads and effects are paid for, and the next call makes them again. Provider and ffmpeg failures stop the film (`FAILED.json`, 1.7): a film is never made without the voice or music it asked for.

Which call each kind of film makes:

| Film | The call | Rule from |
|---|---|---|
| Narrated painted film (explainer, documentary, story) | `lines` in our voice with a `voice` role, `music_prompt`, rough `parts`, `effects` | `PAINTED.md` §3; the tool's `effects` text |
| Characters talking | `lines` with a `speaker` each, `music_prompt`, `effects` | the `speaker` text; `PAINTED.md` §3 and §5 |
| Lyric video, sing-along | `song`, `song_start` (left out: measured, 4.6), `duration`, `parts` and the required `voice`; no lines or music | the brief's hard rule or reference line (2.14) |
| Montage, highlight, fan or sports edit | `music` = the song under a few 1-4 s `from` bites, or `song` = it with no bites; one part per shot, on `beat_grid` times | `FOOTAGE.md` rules 4-5; `fan-edit-uc.md` |
| Edit of footage whose speech matters | `song` = the video, `song_start` = the window's start, parts at the transcript's pauses | `FOOTAGE.md` rule 4 |
| Talking edit (podcast, interview) | each kept stretch a `from` line, back to back; `music_prompt`; `talk_edit: true`; a `{"speech": true}` caption | `FOOTAGE.md` rules 1 and 4 |
| The user's voice recording | alone: its sentences as `from` lines plus `music_prompt`; over its own music: `song` = it | the brief's reference line (2.14) |
| Launch film | usually music only (`music_prompt`, or a library bed the brief names); a voice when the brief or product wants one; `parts` = the spans in whole seconds | `SKILL-gemini.md` §2-3 |
| Event promo, logo animation | music only | the brief's hard rule |

### 4.4 What it writes

The files and the answer are in 1.5.6. `vo-N.mp3` counts lines from 1 in call order; a run of bites of one recording is one file under the first bite's number. `mix-base.wav` is made and deleted during the mix. `soundtrack.json` is written only when `MAPS=1`, which the launcher sets for every painted film, so painted films have it and launch films do not. Map shots and narration captions read it.

The order of work inside `makeSoundtrack()`:

1. Song mode does its own work and returns (4.6).
2. The checks that give fixable refusals.
3. The real-audio cuts.
4. All preset reads at once, then all clone reads at once.
5. The ElevenLabs reads, one by one; each read is trimmed and placed in call order (4.5).
6. The past-`duration` check.
7. The effects, all at once (4.7).
8. The seams (4.9).
9. The music, the bed and the mix (4.6, 4.8).
10. The parts, cut from `soundtrack.mp3`.

`SOUNDTRACK_REUSE=1` mixes again from the reads, effects and `music.mp3` already made (real-audio bites are always cut again). It checks only that each file exists, not that its line's words are the same: a second call with changed words would reuse the old reads. Use it for remixing by hand, not for normal runs.

### 4.5 Voices

Who reads a line:

| Line | Its language is one Magic Hour speaks (`en es fr de it pt ru zh ko`) | Any other language (`ja`, `hi` and the rest) |
|---|---|---|
| has `from` | cut from that file | the same |
| has `speaker` | a Magic Hour preset voice | ElevenLabs: a native voice of that language from `native.json`, or a stock role |
| neither | Magic Hour's voice cloner, reading in the `voice` sample. ElevenLabs reads it when `VOICE_PROVIDER=elevenlabs`, or when the cloner fails | ElevenLabs: that language's native voice for the `voice` role, else the stock voice |

`VOICE_PROVIDER` changes only narration; lines with a `speaker` in a Magic Hour language always go to Magic Hour presets.

**Magic Hour presets** (character dialogue): 1,266 celebrity and character voices with accents and manners one cloned sample cannot give. Each character keeps one voice and no two share one.

- Calls go to `api.magichour.ai` with `Authorization: Bearer $MAGIC_HOUR_API_KEY`.
- `POST /v1/ai-voice-generator` with `{"name": "vo <file>", "style": {"prompt": <text>, "voice_name": <preset>}}` returns `{id}`.
- Then `GET /v1/audio-projects/<id>` every 1 s until `status` is `complete` (download `downloads[0].url`), `error` or `canceled`. The tool gives up after 5 minutes.
- The read is loudness-normalised (`loudnorm=I=-18:TP=-1.5`, 44.1 kHz, 128 kbps). Presets come back between -33 and -20 LUFS, and the quiet ones sank under the music (10-09).
- All preset lines are read at once. A failed preset stops the film; there is no fallback.

**Magic Hour voice cloner** (narration): Magic Hour's voice generator has only celebrity and character voices. So narration is read by its AI Voice Cloner in one of four stock voices, from a clean sample, `research/h3/voices/<voice>.mp3`. Each sample is a read by the matching ElevenLabs voice: `narrator.mp3` 25.2 s, `narrator-f.mp3` 20.8 s, `young-m.mp3` 4.5 s, `young-f.mp3` 4.3 s.

For each line:

1. `POST /v1/files/upload-urls` with `{"items": [{"type": "audio", "extension": "mp3"}]}`.
2. `PUT` the sample to the returned `upload_url`.
3. `POST /v1/ai-voice-cloner` with `{"name", "assets": {"audio_file_path": <file_path>}, "style": {"prompt": <text>}}`.
4. Poll as above.

The read is set to its sample's mean volume. All narration lines are read at once, and every call uploads the sample again. If any cloner read fails, ElevenLabs reads the whole film's narration instead, in the same voices (the clones are clones of them). Magic Hour voices are the default since 10-07, at Magic Hour's request.

**ElevenLabs voices**: `POST api.elevenlabs.io/v1/text-to-speech/<voice_id>?output_format=mp3_44100_128` with `{"text", "model_id": "eleven_v4"}` (`ELEVENLABS_TTS_MODEL`) and header `xi-api-key`. No voice settings and no language code are sent; eleven_v4 reads 94 languages. These reads run one after another.

| Stock role | ElevenLabs voice id | Use |
|---|---|---|
| `narrator` | `dXtC3XhB9GtPusIpNtQx` | male, warm, unhurried: the house narrator |
| `narrator-f` | `EXAVITQu4vr4xnSDxMaL` | female, the same read |
| `young-f` | `cgSgspJ2msm6clMCkdW9` | a young woman on screen, casual |
| `young-m` | `TX3LPaxmHKxFdv7VOQHJ` | a young man on screen, casual |

A line that belongs to someone on screen is read in a voice that matches them. `voice` is required on painted films because a missing voice once gave a woman's lines to the male narrator (10-09). Every returned line says who read it.

**Languages.** Magic Hour's voices speak only the languages in `MH_LANGS` and garble others: Hindi lines read by English presets came back from speech to text as Dutch and English gibberish (10-11). Japanese is left out of `MH_LANGS` on purpose: Magic Hour speaks it, but its presets hold almost no native Japanese speaker. (The `language` parameter's own description still lists `ja` among Magic Hour's languages; the code reads Japanese in ElevenLabs.) `research/h3/voices/native.json` maps a language to its native ElevenLabs voices: 13 Hindi and 12 Japanese, from the ElevenLabs Voice Library, standard rate, usable without adding them to the account, with one for each stock role:

```json
{"hi": {"language": "Hindi",
        "roles": {"narrator": "Raghav", "narrator-f": "Monika Sogam", "young-m": "Bunty", "young-f": "Simran"},
        "voices": {"Raghav": {"id": "4BoDaQ6aygOP6fpsUmJe", "about": "man, calm, confident storyteller"}, "...": {}}}}
```

`elVoice(lang, name)` takes a native voice by name, else the language's voice for a stock role, else the stock voice. A language with no entry is read by the stock voices. In such a film a `speaker` must be one of the language's native voices or a stock role; the refusal lists them.

The language is the call's `language` when given. Otherwise the code guesses from the letters of all lines that are not `from`:

- kana in more than a tenth of the letters means `ja`.
- letters outside the Latin, Cyrillic, Han, kana and Hangul scripts in more than half of them means `other`. `other` is read by the stock voices in ElevenLabs; only `language: "hi"` gets the native Hindi voices.
- anything else means `en`.

Chinese, Korean and Russian therefore count as `en` and go to Magic Hour, which speaks them. Hindi written in Latin letters cannot be detected: the planner must pass `language: "hi"`.

**Real audio lines** (`from`). Each is cut with `-vn -ac 2 -ar 44100 -af loudnorm=I=-16:TP=-1.5`. Bites of one recording that belong together play as one stretch. A bite joins the previous one when it:

- is from the same file;
- is in sync with it (film time minus source time equal within 0.05 s);
- starts at or after it in the source;
- starts at most 2 s after it ends.

The run is cut once, from its first word to its last, with the pauses between, and normalised once. Before this, a remade movie scene given as 13 bites had silences between them and a different level for each (10-11). The 2 s comes from measured pauses inside real scenes (0.04-1.5 s). Bites from other moments are cut one by one. A bite with no `text` comes back, and is stored in `soundtrack.json`, as "(their video <start>-<end> s)".

**Placement.** Every read (not a `from` bite) loses its trailing silence (`areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.1,areverse`). Magic Hour reads end in about 0.5 s of silence, and placed whole they pushed every later line late (a 13-line film ran 2.4 s late, 10-09).

Then, in call order, each line starts at `max(at, cursor)`:

- After a read, the cursor is its end plus 0.25 s.
- After a `from` bite, or a run of bites, the cursor is its end with no gap. The exception is when the next line is the next chunk of the same recording (it starts in the source within 0.3 s of this one's end): then the 0.25 s gap stays, because each chunk is normalised on its own, and with no gap their levels jumped mid-phrase.
- A later bite of a run sits inside the run's cut at its own place and is never pushed.

If the last line ends after `duration`, the call is refused.

### 4.6 Music

One music source per call: `song` wins, then `music_prompt`, then `music`.

- **Generated** (`music_prompt`, what nearly every narrated film uses): `POST api.elevenlabs.io/v1/music?output_format=mp3_44100_128` with `{"prompt", "music_length_ms": duration × 1000, "force_instrumental": true, "model_id": "music_v2_5"}` (`ELEVENLABS_MUSIC_MODEL`). A prompt that names an artist or a game is refused with a 400 carrying a cleaned prompt (`detail.data.prompt_suggestion`), and the call is made once more with it. A 400 with no cleaned prompt stops the film. Generated music starts at 0 s. It is made after the voices and effects.
- **Library** (`music: "<name>"`): `electronic-drive`, `epic-trailer`, `house-groove`, `synthwave-punch`, `tech-house` (174-226 s each). The bed starts at its first downbeat (else its first beat) minus 0.05 s. The launch skill reads `skills/h3-film/references/music.md` only when the brief names one. That file also lists an `agent/music/vo/` shelf that is not in this repo, and the tool refuses those names (11.4).
- **The user's music as the bed** (`music: "<run>/attached/<file>"`; only files under `attached/` are accepted). Start: `song_start` if given; else, in a film the music carries (4.8), its strongest part; else 0 s. Writes `song.json` and returns `music_start`.
- **A song as the whole soundtrack** (`song`): lyric videos, an edit whose footage's own sound is the soundtrack (`song` = the video), a finished mix, a voice recording over its own music.
  - `lines`, `effects`, `music`, `music_prompt` and `talk_edit` are ignored in this mode, and seams are never moved.
  - The window `[song_start, song_start + duration]` is cut with `loudnorm=I=-16:TP=-1.5:LRA=11` and a 0.8 s fade-out at the end. A song shorter than the film is not padded (as in the batches): the soundtrack comes out shorter.
  - Default start: the strongest part when the run has `lyrics-ids.vtt` (a sung song), else 0 s (the tool text and the brief say the strongest part either way: 11.3).
  - Two checks against the lyric ids come back as a `note`. A window that opens inside a sung line moves back to 0.5 s before that line (never before the previous line's end), so the line is not heard with no words on screen. A line that starts in the last 1.5 s is named, to get no row (the end would cut it off).
- **Strongest part** (`strongestStart`). Before this, edits played their song's quiet intro (10-09). The candidate windows are those that start where a loudness band starts (a downbeat) and fit inside the track. Take the one holding the most seconds of `high` band, then of `mid`, the earliest on a tie. Then start two downbeats earlier, minus 0.05 s, so the film opens on the run-up and the drop lands a few seconds in. The start is 0 s when there is no analysis.
- **Beat grid**:
  - `research/tools/analyze_music.py` runs once per file (cached as `<file>.music.json`) with `ALLIN1=0`.
  - It does madmom downbeat tracking plus per-bar loudness in dB, cut into `low`/`mid`/`high` at the 33rd and 75th percentiles and median-smoothed over 3 bars. A bar at least 5 dB louder than the one before keeps its own higher label (a drop).
  - It takes about 6 s for a 30 s track.
  - The grid comes back in film seconds, `{bpm, beats, downbeats, energy: [{label, start, end}]}`, with a note that every cut that follows the music lands on one of these times.
  - If the analysis fails (for example, no madmom), there is silently no grid and the strongest part is 0 s.
- **Seams off the beat** (song mode only): in a film cut on the beat (median part 4 beats or less), every seam more than 0.05 s from a measured beat is listed in a `note`, asking for another call (10-09: an AMV planner sized its shots before it had the grid, and its seams fell up to 0.3 s off). Lyric videos keep their seams in the gaps between sung lines.

### 4.7 Sound effects

Painted films only. H3 plays the soundtrack it is given, so these are the film's only effects (films had none until 10-09).

- `{at, sound, seconds?}`: ElevenLabs text to sound, `POST api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128` with `{"text": sound, "prompt_influence": 0.5, "duration_seconds": seconds}`. `duration_seconds` is sent only when `seconds` is given (the tool allows 0.5-10). Left out, the effect keeps its own length with its tail (effects squeezed to 0.5-0.9 s were cut off). The planner writes `sound` concretely ("a rubber balloon bursting with a sharp loud pop").
- `{at, sound, from, start?, seconds?}`: a real sound file the brief gives (a meme's own sound), cut from `start` for at most `seconds` or 4 s (never past the file's end), its last 0.15 s faded.
- All effects are made at once. Each is timed to the moment its picture happens, also during a spoken line: it plays under the words and never moves a line. An effect running past the film's end is cut there.
- Launch films have no `effects` parameter. `SKILL-gemini.md` §3 still says the prompt asks H3 for sound effects. With the clip's audio held fixed and the join playing only the soundtrack, such words add no sound.

### 4.8 The mix

Music and voices are set against each other first. The whole is then brought to programme loudness by one fixed gain, and effects are laid at the level of the speech, so nothing moves the music or a voice.

| Constant | Value | Meaning |
|---|---|---|
| `VO_MEAN` | -20 dB | every read (not `from` bites) is set to this mean volume, so every voice sits at one level (presets and the narrator voices differed by 5 dB) |
| `BED_MEAN` | -22 dB | the music's mean volume before ducking, whatever its source, measured over the whole source file |
| bed in a film the music carries | -19 dB (`BED_MEAN + 3`) | the song drives the film; it had sat about 6 dB under a meme edit's dialogue (10-10) |
| duck under narration | 0.35 (about -9 dB) | music under a narration line or the user's recording |
| duck under characters talking | 0.2 (about -14 dB) | when any line has a `speaker`, or `talk_edit`: at -9 dB a cast of characters was hard to hear (10-09) |
| duck when the music carries the film | 0.6 (about -4.4 dB) | under real-audio bites in an edit: at 0.35 a song sat about 11 dB under its calls (10-09) |
| duck ramps | 0.35 s down before the sound, 1.2 s back up after | a linear trapezoid per sound; overlapping sounds take the lowest |
| bed fade | last 0.8 s | |
| programme loudness | -16 LUFS integrated | one gain, measured on music plus voices without effects |
| effects under a line | 0.32 (about -10 dB) | while a line's words play, with 0.1 s ramps, worked out every 64 samples |
| limiter | `alimiter=limit=0.891:level=0:latency=1` | about -1 dBFS; it only catches the moment the sum would clip |

A film the music carries (`carried` in the code) has no `talk_edit`, and either every line is a `from` bite from a video file or it has no lines at all. A run of bites of one recording ducks once, across its pauses too. Only reads and real-audio bites dip the music; effects never do.

Steps:

1. `bed.wav`: the music source (`-ss <start> -t <duration>`; generated music from 0 s) goes through `volume=<BED - mean>dB`, the duck envelope, a fade-out over the last 0.8 s, and, on the swap path only, `apad=whole_dur=<duration>`, so a bed shorter than the film is padded (10-12: a TikTok's song started 27.3 s into its 44 s had made a 16.5 s soundtrack for a 57 s film); every other film keeps the batch's bed, not padded. No music, or a silent music file: silence.
2. `mix-base.wav`: the bed plus every sound, each delayed to its `at`, reads set to `VO_MEAN`, mixed with `amix=normalize=0:duration=first`.
3. Gain = -16 minus the integrated loudness of `mix-base.wav` (ffmpeg `loudnorm`, measuring only); 0 when it cannot be measured.
4. The effects' target level is the median, over all sounds, of each sound's loudest 400 ms as it sits in the mix. The loudest 400 ms is ffmpeg `ebur128`'s momentary maximum, each file padded with 0.5 s first so a short sound fills a window; for an even count the median is the upper middle value. With no voice at all, the target is the bed's integrated loudness + 6 (-16 with no music either). Each effect gets `target - its own loudest 400 ms + gain`, its delay, and the under-a-line envelope.
5. `soundtrack.mp3` = `mix-base` × gain, plus the effects, through the limiter, cut to `duration`, 192 kbps.

Why one gain and not a final loudness pass: a `loudnorm` over the whole finished mix turned the music down about 2 dB after every run of effects (10-11). Why a gain at all: without it, a film that is mostly music shipped at the bed's own ducked level, far too quiet. Why effects at the speech's level and under lines: raised to one loud peak they stood out, and kept to the gaps between lines they pushed the lines (10-11). A talking edit measured its music about 19 LU under the speech on a test film; that number comes from the settings above, not from a constant.

### 4.9 Seams and the parts

A seam is where one clip ends and the next begins. Clips are rendered apart, so a seam is a hard cut, exact to the frame.

**Painted films: seams go into pauses** (`snapSeams`, on when `H3_PAINTED=1`). The planner gives rough `parts`. Each seam in turn is wanted at the running sum of the asked parts, not rounded (10-12: a sum of 40.12 came out as 40.120000000000005, just inside a line that started at 40.12; 11.3):

- The pauses are the gaps before the first line, between lines and after the last.
- Each pause offers one place: the wanted time if it falls in that pause, else the pause's middle.
- Only places that keep this clip 4-15 s, and let the rest of the film split into clips of 4-15 s, count.
- The nearest to the wanted time wins. If none is left, the call gets a fixable refusal.

So whenever the film has lines that count and two or more clips, every clip must be 4-15 s. Which lines count:

- Every film but a swap (the batch's rule): every line counts, ours and the user's own (`from`); if no seam fits, only our own lines count. So in an edit the footage's own speech can move a seam.
- A swap (the approved swaps' rule): only our own lines. The footage's own lines never move a seam: a remake cuts on the movie's cuts.

A replay of all 1,268 past calls (10-12) showed that ignoring the user's lines in every film would have put 11 cuts of two storytime films inside sentences.

On the swap path, footage edits with no lines of ours keep their parts as given (down to 0.25 s, one shot per clip). In every other film the footage's own lines also move seams into their pauses when every clip can stay 4-15 s; otherwise (a montage of short shots) the parts are kept as given. Launch films do not snap: their whole-second parts are kept. Song mode never snaps: lyric videos and footage-sound edits place their seams themselves. The planner had re-called the tool only to move seams in 12 of 16 runs (10-04), so the tool moves them and returns the final spans in one call.

Nothing checks that `parts` add up to `duration`, or that `render.json` spans equal the returned parts. When seams are snapped (a painted film with lines that count and two or more parts), the last part is whatever is left of `duration`; otherwise the parts are cut as given. Without a set length, the join ends at the shorter of picture and sound, so a mismatch shortens the film or cuts its end. With a set length (`H3_DURATION`), the join pads or trims to it.

How each clip gets its sound:

| Clip | `render.json` `audio` | Notes |
|---|---|---|
| painted or launch H3 clip | `soundtrack/part_N.mp3` | `span` = the part's length |
| montage H3 shot (`build-edit.mjs`) | `part_N.mp3` when the soundtrack has exactly one part per shot; else `shot_N.mp3`, cut from `soundtrack.mp3` at the shot's film start for its render `seconds` | for example, a talking edit laid as `from` lines with no `parts` (10-11: before this fallback a podcast edit could not add one H3 shot) |
| clean footage, code or map clip | none | picture only; the soundtrack carries their sound only if the call put it there |

Inside H3 (5.3), the part is padded with silence or cut to the clip's render length and held fixed. The painted audio line is "Audio 1 is the finished soundtrack: keep it verbatim, cut on its beats, each spoken line lands on the row it names. Do not add narration, music or sound effects."

### 4.10 Silent, unreadable and missing files

| Input | What happens |
|---|---|
| `song` missing | fixable refusal |
| `song` unreadable (ffprobe fails) | the film stops |
| `song` with no audio stream (a screen recording, an AI clip) | the soundtrack is silence for `duration`, and a `note` says to call again with `music_prompt` if the film needs music (10-12: it used to stop the whole film) |
| `music` (attached) unreadable | the film stops |
| `music` (attached) with no sound | no music under the voices, and a `note` says so |
| `from` file missing, or with no sound | fixable refusal |
| an effect's `from` file missing or silent | not checked: ffmpeg fails and the film stops |
| a song or bed shorter than the film | a bed is padded with silence on the swap path; a song, and a bed in any other film, are not (as in the batches) |
| a network error (no response) | every Magic Hour and ElevenLabs call in `soundtrack.mjs` is tried 3 times, 3 s apart; HTTP errors are not retried there (10-09: a dropped connection killed a whole film) |
| ElevenLabs 429 "system_busy", 5xx, or no response | voices, effects and music: up to 5 tries, 4, 8, 16 and 32 s apart; speech to text has no retry |
| `ELEVENLABS_API_KEY` missing | the first ElevenLabs call stops the film |

### 4.11 Lyrics

Planners never write lyrics: Anthropic's output filter refuses copyrighted lyrics, so the planner writes ids and code puts the words in.

1. **The words and their times**: a fetched song comes with LRCLIB's synced lyrics (2.9). `transcript()` uses them, shifted to the file, or else speech to text. A lyric video with no `.vtt` from the user gets one written from `transcript()`, and so does a sung song in any other film.
2. **Ids**: the launcher runs `lyric-ids.py` (3.4).
3. **Words back in**: `mcp.mjs` replaces `[Ln]` and `[Ln:a-b]` (words a to b of the line) in every tool argument, so a type still gets the real words. It does this when `<run>/lyrics.json` exists as the tool server starts. render-all writes `prompts-lyrics/<clip>.txt` with the words for H3. Captions replace whole-line `[Ln]` ids only.
4. **Rows on the sung times**: `lyric-retime.py <run> 0` copies `prompts/` to `prompts-unretimed/` once, and rewrites each H3 clip's prompt (the file `render.json` names) from that copy. In each clip:
   - A row that names an id not yet seen in the clip moves to that line's sung time: the `lyrics-ids.vtt` cue, less `songStart` from `song.json`, less the clip's start. For a repeated line, it takes the sung time nearest the row's own start, within 1 s of the clip.
   - The row keeps its length (at least 0.3 s). The row before it ends there. The row after starts where it now ends, if it started where this row used to end.
   - A move that would put the row before an earlier row is skipped.
   - Then rows are kept in order, each at least 0.2 s long; an arrival row that ends on an Image keeps at least 0.4 s.
   - Sync wording is removed: "on the beat", "with the vocal", "in time with the music", "to the beat", and the audio line's "cut on its beats, each … line lands on the row it names."
   - The lead is 0 s (`auto.mjs` passes 0, which is also the default). The old 1 s lead was for the reference-audio mode; with the audio held fixed, lead 0 beat it (10-08).

### 4.12 Captions drawn by code

Code draws on the finished film every word that must stay the same while the picture changes, with the same words, size and place in every frame: a meme's caption, a running title, subtitles, lyrics shown as plain subtitles, a voiceover or speech captioned as said, and every word added on top of real footage. H3 had painted a meme's caption at a different size and place in each clip, and repainting real footage under it moved what was in it (10-10). Words designed into a style's picture (a type still) stay in the picture.

`render.json` `captions` (footage edits put it in `EDIT.json`, and `build-edit.mjs` copies it):

| Field | Default | Meaning |
|---|---|---|
| `text` | | the words; `[Ln]` ids replaced; `\n` starts a new line; empty text is dropped |
| `from`, `to` | 0, the film's end | when it shows, in film seconds |
| `place` | `bottom` | `top`, `middle` or `bottom`: the text block's centre at 0.12, 0.5 or 0.86 of the height |
| `x`, `y` | 0.5, from `place` | the block's centre as a share of width and height; `y` overrides `place` (0 counts as unset) |
| `color` | white | any colour Pillow reads (`#RRGGBB`, a name) |
| `style` | | `"title"`: thin, widely spaced capitals with a soft shadow that fade in and out; the style for titles on footage |
| `speech` | | `true`: becomes the film's heard words |
| `narration` | | `true`: becomes the soundtrack's spoken lines |
| `lyrics` | | `true`: becomes every sung line |
| `words` | 3 | words per chunk, for `speech` and `narration` |

How render-all expands them (each chunk keeps the entry's place, colour and style):

- `{"speech": true}` (a podcast, an interview, a talking head): ElevenLabs speech to text of `render.json` `music`, cached as `<run>/speech-words.json`.
  - Every heard word is grouped `words` at a time; the entry's own `from` and `to` are not applied (11.3).
  - A chunk shows from its first word's start until its last word's end + 0.15 s, or the next chunk's start if sooner. A speech or narration entry's own `from` and `to` are not applied: it draws every word heard (10-12: a film captioned to 40.1 s also drew the closing song's 36 sung words; 11.3).
  - If speech to text fails, the film is made without these captions and says so; a re-render tries again.
  - The cache is not remade when the soundtrack changes: delete `speech-words.json` after making a new soundtrack.
- `{"narration": true}` (a voiceover captioned as said): every line of `soundtrack/soundtrack.json` with text.
  - Each line is split into chunks of `words` words. A line of one word or with no spaces (Japanese, Chinese) is split into 8-character pieces instead.
  - The chunks are spread over the line's `at`-`end` in proportion to their length.
  - The entry's own `from` and `to` are not applied: every spoken line is captioned.
  - It needs `soundtrack.json`, which launch films do not have.
- `{"lyrics": true}`: every cue in `lyrics-ids.vtt` that falls in the film, its words from `lyrics.json`, at its sung time less `songStart`. It shows until the next line starts or 0.8 s after the cue ends, whichever is sooner, for at least 0.5 s and never past the film's end. The entry's own `from` and `to` are not used.
- Anything else: one caption.

Drawing (`join.mjs`, Pillow): each caption is one full-frame transparent PNG at the film's size, written next to the output as `final-gpu.mp4.captionN.png`.

| Setting | Caption | Title (`style: "title"`) |
|---|---|---|
| font size | round(0.065 × the shorter side): 31 px at 480 rows | 0.7 × that |
| font on macOS | Arial Bold | Helvetica Neue Light |
| font elsewhere | `assets/fonts/Inter-Bold.ttf` | `assets/fonts/Inter-Light.ttf` |
| text | as written | upper case, letter spacing 0.3 × font size |
| outline | black, max(2, round(0.09 × size)) px | none; a black shadow at alpha 170, blurred by 0.12 × font size |
| line height | 1.18 × font size | 1.5 × font size |
| on and off | cuts on and off, like a platform's captions | fades in over 0.4 s from `from` and out over the last 0.4 s before `to` (with no `to`, it only fades in) |

Lines wrap at width × min(0.88, 2 × min(x, 1 - x) - 0.04), at spaces; each Chinese, Japanese or Korean character can wrap on its own. The block is centred on (x, y) and kept 4 px inside the top and bottom edges. Later captions draw over earlier ones.

### 4.13 Non-Latin scripts and emoji

`pick()` in `join.mjs` chooses the font for each caption from its text (macOS paths):

- any Hangul → Apple SD Gothic Neo;
- else any kana, CJK ideograph or full-width form → Hiragino Sans W6 (`ヒラギノ角ゴシック W6.ttc`);
- else any character outside U+0000-052F and U+2000-206F (Devanagari, Arabic, Thai, many Vietnamese letters, "€", emoji) → Arial Unicode MS;
- else Arial Bold (Inter Bold off macOS).

A title with such a character uses the picked font at the caption size, not the thin title font. What breaks:

- Off macOS every non-Latin caption comes out as empty boxes. The macOS font files are not there, so Pillow falls back to its built-in font, which has no Devanagari, CJK or emoji glyphs. Fonts for these scripts (for example the Noto families) and their paths in `pick()` are needed.
- No text shaping anywhere. Pillow's complex-text layout (raqm) is off in this `.venv` (`PIL.features.check('raqm')` is False): Pillow's font module loads the FriBiDi library at run time and turns raqm on only when it finds it (untested here). Without it, Arabic and Hebrew are drawn left to right with unjoined letters, and Devanagari, Bengali and Thai lose their conjuncts and vowel-sign placement. Chinese, Japanese and Korean are fine on macOS.
- Emoji are empty boxes, also on macOS (no colour emoji font is used).
- Scripts written without spaces (Thai, Lao, Khmer) cannot wrap: a sentence is one unit and runs off both sides.

### 4.14 The join (`agent/h3film/join.mjs`)

`joinFilm({clips: [{file, seconds}], music, out, size, target, captions})`. render-all passes:

- each clip's file, with `seconds` = its `span`;
- `music` = `render.json` `music`;
- `out` = `<run>/final-gpu.mp4` (`final-novid.mp4` with `NOVID=1`);
- `size` (5.2 step 11);
- `target` = `H3_DURATION` if set;
- the expanded captions.

1. Frame grid. The frame rate is the first clip's: 24 for H3 clips. render-all has already conformed footage and code clips to it; a film of only footage or code clips takes its first clip's rate. Clip i keeps `round(end_i × fps) - round(start_i × fps)` frames, where start and end are running sums of the spans. Cutting each clip with `-t` had kept up to a frame too many per clip, and over the 28 clips of an AMV the picture ran 0.3-0.6 s behind its song (10-09). What H3 returns past the span is dropped.
2. Each clip goes through `fps=<fps>,trim=end_frame=<n>,setpts=PTS-STARTPTS,scale=<w>:<h>,setsar=1` (a clip of another shape is stretched to the film's size), then `concat=n=<N>:v=1:a=0`. Every seam is a hard cut: no crossfade, no retiming. The clips' own audio is not used.
3. Exact length (only with `target`). The film is left as it is when its frame count is between `round(target × fps)` and `floor((target + 0.45) × fps)`, which a player shows as the target whether it rounds or floors. Otherwise it goes to the nearer bound. If shorter, the last frame is held (`tpad=stop_mode=clone`) up to `round(target × fps)` frames. If longer, the picture is cut at `floor((target + 0.45) × fps)` frames. Either way, the sound is cut or padded with silence to the same length and fades out over its last 0.15 s.
4. Captions: each PNG is an input (a title as a looped image with `fade` on its alpha), placed with `overlay=0:0:enable='between(t,<from>,<to>)'`, chained in list order. Every caption chunk is one more input and overlay: word-by-word speech captions can mean 100 or more.
5. Sound: `soundtrack.mp3` from 0 s, encoded to AAC at ffmpeg's default bitrate. Without `target` it is read for at most the sum of the spans, and `-shortest` ends the film at the shorter of picture and sound. With `target`, the trim in step 3 applies. No `music` in `render.json` means no audio stream.
6. Output: H.264 (`libx264 -crf 18 -pix_fmt yuv420p`). Returns `{out, seconds}`.

The planner's `join_film` tool, offered to launch sessions only, calls the same function without captions or target; `./film` never uses it.

### 4.15 Settings

The tool server reads the `soundtrack.mjs` settings from its environment and from `.env.local`, which `mcp.mjs` loads. render-all reads `H3_AUDIO_MODE` from its own environment (`./film` exports `.env.local`).

| Variable | Default | Effect |
|---|---|---|
| `MAGIC_HOUR_API_KEY` | | preset voices and the voice cloner |
| `ELEVENLABS_API_KEY` | | music, effects, speech to text, voices in languages Magic Hour cannot speak, the cloner's fallback |
| `VOICE_PROVIDER` | `magichour` | `elevenlabs`: narration read by the ElevenLabs stock voices (presets unchanged) |
| `ELEVENLABS_TTS_MODEL`, `ELEVENLABS_MUSIC_MODEL`, `ELEVENLABS_STT_MODEL` | `eleven_v4`, `music_v2_5`, `scribe_v2` | ElevenLabs models (the sound-effect model is not named: the endpoint's default) |
| `ELEVENLABS_VOICE_ID` | the house narrator | used only when no `voice` is passed, which the tool never does |
| `SOUNDTRACK_REUSE` | unset | `1`: mix again from what was already made (4.4) |
| `MAPS` | set by the launcher for every painted film | `1`: the answer is also written to `soundtrack/soundtrack.json` |
| `H3_AUDIO_MODE` | `inpaint` | `reference`: the part only as a reference to H3 (the measured worse mode) |
| `H3_DURATION` | unset | set by `auto.mjs` from `--duration`, or with `DURATION=1` from the request or the use case: `make_soundtrack` refuses any other length and the join fits the file to it |
| `ALLIN1` | `0`, set by the code | music analysis by madmom |

## 5. Rendering

This step turns `render.json` into one video clip per entry, then hands the clips to the join. MiniMax H3 (reference to video) draws each H3 clip in ComfyUI on one GPU. Clips drawn in code and footage played as filmed skip H3.

### 5.1 Files, and how the step is started

| File | What it does |
|---|---|
| `agent/h3film/render-all.mjs` | the whole step: checks, preparing each clip, one GPU job per H3 clip, reuse of finished clips, conforming code and footage clips, captions, the join, the records |
| `research/h3/runpod/comfy_r2v.py` | one clip: builds its ComfyUI graph and input files, sends them to the GPU worker, writes the clip's mp4 |
| `research/h3/runpod/r2v_v1.json` | the base ComfyUI graph: Magic Hour's production reference-to-video graph from its H3 notebook (`minimax_prod_v1`). Never changed on disk; `comfy_r2v.py` edits a copy for each clip |
| `research/h3/modal_h3.py` | the GPU worker on Modal: app `h3-render`, class `H3`, ComfyUI v0.36.0 |
| `agent/h3film/boxed-check.py` | finds a clip H3 drew with black bars; render-all only logs it |

The folder name `research/h3/runpod/` is left from the RunPod pods this first ran on; nothing in it uses RunPod now.

`auto.mjs` runs `node agent/h3film/render-all.mjs <run>` up to 3 times until `final-gpu.mp4` exists, passing `GPU_ROWS` (an empty string, `704` for the `2-5d-hybrid` card, or the shell's own value) and `H3_DURATION` when `--duration` was given; `./film` sets `H3_BUDGET_USD=20`. By hand:

```sh
set -a; . ./.env.local; set +a       # render-all reads .env.local only after the clips are made
GPU_ROWS= H3_BUDGET_USD=20 node agent/h3film/render-all.mjs agent/runs/h3film-<name>
```

- Before the clips are made render-all needs the Modal token (`MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`, or `~/.modal.toml`), and for swapped first frames `FAL_KEY` and a non-empty `GOOGLE_VERTEX_PROJECT`, in its environment.
- Set `GPU_ROWS=` (empty) to reuse clips that a `./film` run made. `auto.mjs` passes an empty string, and the raw value is part of every clip's reuse key: with `GPU_ROWS` unset, every key differs and every clip renders again.
- Add `H3_DURATION=<seconds>` for a film made with `--duration`, and run `lyric-retime.py` first for a lyric film (7.4).

To render one clip while debugging, use the clip JSON render-all wrote (it holds render-all's changes) and the same flags:

```sh
.venv/bin/python research/h3/runpod/comfy_r2v.py --clip=<run>/render-gpu/<id>.json <out.mp4> \
  --refh=360 --ratio=<ratio> --audio=inpaint [--rows=N] [--footrows=N] [--seed=N]
```

The older form, `comfy_r2v.py <run> <clip-id> [out] [--novid]`, reads `render.json` raw: no trimming, no pins added by the renderer, no tags, and without `--audio=inpaint` the sound goes in only as a reference.

### 5.2 What render-all does, in order

The fields of `render.json` are in 1.5.5. render-all also reads `FAILED.json`, `maps/failed.json`, `lyrics.json`, `lyrics-ids.vtt`, `soundtrack/song.json`, `soundtrack/soundtrack.json`, `speech-words.json` (a cache), `agent/h3film/library/proven/*/stills.json` and, after the clips, `.env.local`.

**1. Refusals.** Exit 1 before anything renders when `FAILED.json` or `maps/failed.json` exists, or a code clip's mp4 is missing.

**2. Reference cuts.** Each launch motion clip from `agent/h3film/library/proven/` is cut to the stretch its proof render used (`stills.json` `"trim": [start, length]`, set for 29 components), silent, into `render/refs/<name>-<start>-<length>.mp4`; a cut shorter than 2 s holds its last frame to 2.05 s. Why: a source clip often carries its neighbours (another scene, a caption card), and H3 copies what a reference shows.

**3. Render length.** H3 renders at 24 fps; its frame count is the smallest 17k+5 at or above max(5, round(seconds × 24)) (7.8 s becomes 192 frames, 8.0 s).

- Painted and launch clips (no footage video): seconds = min(seconds, span + 0.3), and pins at or past the new length are dropped. `EDIT_TRIM=0` or `chain` turns this off. Why: the picture is drawn to the fixed soundtrack, so nothing past the cut is ever seen, and H3 spreads the action over an empty tail. On 16 painted films the frames past the cut went from 9.9% to 5.9%; before the trim, nine painted shots of one edit rendered 46.5 s to keep 12 s.
- A clip whose only video is a footage segment: seconds = span + 0.3, with no 2 s floor (a one-beat shot rendered at 0.88 s matched its footage as closely as a 2 s render, for half the GPU time).
- A footage zoom shot with no stills (not `chain`): the smallest H3 frame count that holds the frames the join keeps (F = the smallest 17k+5 ≥ max(6, kept frames), seconds = F / 24); pins past frame F − 1 are dropped and, if no pin covers the last kept frame, an end pin is added on the same zoom curve. Only when it saves frames (13 same-seed renders matched their footage as before).

**4. Pins the renderer adds.** Each pin becomes one `MiniMaxH3AddGuide` node (5.3), on top of the planner's own pins.

- (a) A footage shot's first frame: a clip whose only video is footage, with no stills and no pin at 0 s, gets `{"t": 0, "video": <the segment>, "at": 0}`. The shot must open on its real frame, and planners told to write this pin skipped it. Not with stills: the raw frame has no caption banner, and H3 then dropped the banner (a meme film lost its caption).
- (b) Zoom and framing on a footage shot with no stills: pins every `ZOOM_STEP` seconds (0.2), from 0 to seconds − 0.05, each the shot's own frame at that time, cropped. Zoom z(t) = a + (b − a) × (1 − (1 − t/D)²), with D the clip's seconds (fast at the start, easing out); the crop is iw/z × ih/z, centred, or with `frame` a crop of the film's shape around (x, y), divided by z. These pins replace all other pins and are saved in `render-gpu/zoom/`; the footage still goes in as Video 1. Why: a single end pin held the shot and then snapped, while a pin every 0.2 s followed a planned 1.0 → 1.6 push within 0.01. Each pin costs about 2.9 GPU seconds.
- (c) A footage shot that also has stills (someone in it becomes the person or character in a picture, or it is restyled), with `frame` or `zoom`: its own frames are never pinned, because they show the filmed person and H3 kept him. The reference video itself is cropped to the film's shape around (x, y), pushed in if `zoom` is set, and written next to the segment as `<name>-framed-<x>-<y>[-z<a>-<b>].mp4` (CRF 16, silent); `frame` and `zoom` are then cleared. Why: H3 redraws only someone big in its frame; a close shot of one player became the character cleanly, wide broadcast shots did not.
- (d) Swapped first frame (live-action swaps; `SWAP_PIN=0` turns it off), for a clip marked `"swap": true` (only `FOOTAGE-swap.md` asks for it), whose one video is footage, with at least one picture from `<run>/refs/` (the producer's) or `<run>/attached/` (the user's) among its images, and no pin at 0 s. The footage's first frame goes to Nano Banana as Image 1, the clip's images after it, with this text:

  > Image 1 is one frame of a live-action film. Return this exact frame unchanged: the same framing, camera, place, light, and every other person and object in it, except this change: {swap} Each new person has exactly the face, hair, skin tone and build of their picture, in the pose, size and place of the person they replace, photographed like the rest of the frame.

  `{swap}` is built from the prompt's `subject_definitions` lines, with `<Subject N> is ` removed, `<Picture n>` changed to `Image n+1` and `<Video k>` to `Image 1` (or from the older one-line "… becomes … (Image N)" form). Model `NANO_BANANA_MODEL` on fal (`fal-ai/nano-banana-2.1/edit`) at 1K, with the aspect nearest the frame's; cached as `render-gpu/swap/<id>-swapped-<hash8>.png` and pinned at 0 s. A refused or failed edit leaves the clip as it was. This paid call happens before the render cap check. Why: H3 copies the filmed face back from the footage over a few seconds; opening on a frame where the swap is already made was judged better overall side by side (10-12).
- (e) A shot that continues across a seam: step 8.

**5. Prompt text.** The prompt goes to H3 word for word: nothing rewrites, summarises or expands it. render-all makes only these changes:

- Lyric films (`lyrics.json` exists): `[Ln]` and `[Ln:a-b]` become the sung words, written to `prompts-lyrics/<id>.txt`.
- Swap clips (`TAGS=swap`, the default): `Image N` becomes `<Picture N>`, `Video N` becomes `<Video N>`, `Audio N` becomes `<Audio N>`, written to `prompts-tagged/<id>.txt`. The H3 node labels its references with these tags and says to use them in the prompt. Tested on swap clips only (10-12); `TAGS=all` tags every clip (untested on other kinds), `TAGS=0` none.
- `NOVID=1` (off) removes the "Video N is …" lines and the videos.

**6. Launch row check.** Only when `kind` is not `"painted"` and no clip has footage: render-all refuses the film if any row that brings something into the frame names no attached Image (`uncoveredRows`, 3.6).

**7. Render cap.** render-all refuses the film when the estimate is above `H3_BUDGET_USD` (default 5; `./film` sets 20): the sum over H3 clips of $0.05 × (max(5, seconds) + the seconds of every reference video + 3 for a chained clip), plus $0.08 for each image past the fifth. These are fal's prices, not the GPU cost; it is a leftover guard to replace with Magic Hour's own limits. `H3_BUDGET_USD=0` refuses every film with an H3 clip, before any GPU call.

**8. Sending the clips.** Each H3 clip is one call of `.venv/bin/python research/h3/runpod/comfy_r2v.py --clip=<run>/render-gpu/<id>.json <run>/render-gpu/<id>.mp4` with `--refh=360`; `--ratio=<ratio>`; `--rows=$GPU_ROWS` if it is not empty; `--footrows=360|480` for a footage clip with no stills (360 when `GPU_ROWS` is unset or at most 480, else 480); `--audio=inpaint` unless `H3_AUDIO_MODE=reference`; `--seed=<clip seed or H3_SEED>` if set; `--footage=<H3_FOOTAGE_MODE>` if set. The clip JSON is the clip as render-all changed it.

- All clips of a film start at once (`Promise.all`); render-all has no limit of its own, and the Modal account's GPU cap queues the rest (10 at once on the Starter plan).
- A shot that continues across a seam: when the previous clip's last pin (largest t) and this clip's pin at 0 s are the same picture (same SHA-1), both are H3 clips and there is no `chain`, this clip waits for the previous one, and its 0 s pin becomes the previous clip's frame `keep − 1`, the last frame the join keeps of it (`render-gpu/chain/<prev>-frame<k>.png`). Why: rendered apart, both clips started the shot from the same master still and the picture jumped back at both seams of a phone call (10-11). Such films take longer.
- `chain` films (legacy) render clip by clip, each given the last 3 s of the one before as Video 1.
- A clip with `first` or `last` fails: frame mode does not render on this path.
- No clip is retried inside render-all, `comfy_r2v.py` or the Modal class. One failed clip makes render-all exit with "<id> failed on modal: <last log line>"; `auto.mjs` reruns render-all, and finished clips are reused, so only failed ones render again, each with a new seed.

**9. Reusing finished clips.** A clip is reused only if it was rendered from exactly the same inputs. Its key, stored in `render-gpu/<id>.key`, is the SHA-1 of a JSON object holding: the prompt text; the SHA-1 of every image, video, the audio and `first`/`last`; every pin as `[t, SHA-1 of its image]` or `[t, [SHA-1 of its video, at]]`; `tail` (for `chain`); `seconds`, `expansion` and `ratio`; `rows` (the raw `GPU_ROWS`), `r2v` (the raw `R2V`) and `footrows`. If the inputs changed, the old clip is renamed `<id>.mp4.stale-<ms>` and renders again. A clip with no key file is kept only if the prompt embedded in its mp4 (ComfyUI writes the graph into the file's metadata, node 138) equals the current prompt. The seed is not in the key: a rendered clip is never re-rolled while its inputs are unchanged, and any new render draws a new seed.

**10. Boxed clips.** `boxed-check.py` samples a clip at 2 fps and flags black bars on both opposite sides (columns or rows with 98th-percentile luma ≤ 20 from the edge inward, ending on a full-height picture edge, at the same width in at least half the frames). A flagged clip is only logged ("came back boxed"). About 1 clip in 700 comes back boxed with nothing in its inputs to explain it (a scan of 1,336 clips); a hidden retake was removed on 10-09 (one take per request), and the main cause, wide footage sent uncropped, is fixed at the input.

**11. Code and footage clips.** Conformed to the film's size and frame rate, video only, into `render-code/<id>.mp4` (libx264, CRF 16, yuv420p, last frame held if short, cut to `seconds`): a code clip is fitted inside the frame and padded, never stretched; a footage clip fills the frame, centre-cropped, or cropped at `frame`, or shown whole on black with `"fit": "whole"`; a footage `zoom` becomes an eased, centred zoompan. The film's size: a map clip's own size if the film has map shots (the H3 clips are scaled up to it, so map type and coastlines stay exact); else the first H3 clip's size; else the size H3 would render for the ratio. The frame rate is the first H3 clip's (24); a film of footage only keeps its footage's rate.

**12. Captions, then the join.** render-all expands `captions` (4.12) and calls `joinFilm({clips: [{file, seconds: span}], music, out: final-gpu.mp4, size, target: H3_DURATION, captions})` (4.14). H3's own audio track in each clip is never used.

**13. Records.**

| File | Holds |
|---|---|
| `render-<id>.log` | the clip's output; the last line is `clipN: <wall> s (<gpu> s rendering on <GPU name>) → <path>`. The second number is the GPU time used for cost |
| `render-gpu/<id>.mp4`, `.json`, `.key` | the clip, exactly what was sent, its reuse key |
| `render-gpu/zoom/`, `swap/`, `chain/` | the pictures the renderer pinned |
| `spend.json` | `{"spent", "cap"}`: the fal-priced estimate of step 7, not what the GPUs cost |
| `manifest.json` → `render` | 1.5.8 |
| the last line printed | `rendered N clips in X s[ (K code or footage clips, no H3 call)], on Modal → <final>` |

`python3 agent/h3film/planner-cost.py <run>` prints a run's planning minutes, planner cost and GPU minutes.

### 5.3 One H3 clip as a ComfyUI job

**The base graph, `research/h3/runpod/r2v_v1.json`** (ComfyUI API format; the file keeps Magic Hour's sample values, which `comfy_r2v.py` overwrites for every clip):

| Node | Class | Settings | Role |
|---|---|---|---|
| 127 | `UNETLoader` | `minimax_h3_ref2va_pruned_int8_convrot.safetensors`, weight_dtype default | H3 reference-to-video model, pruned, int8 |
| 141 | `PathchSageAttentionKJ` (KJNodes) | sage_attention `auto`, allow_compile false | SageAttention; the worker sets `disabled` on a B200 |
| 142 | `MiniMaxH3BlockCacheT8` | residual_diff_threshold 0.12, start_percent 0.08, end_percent 0.95, max_consecutive_hits 2, cache_device `cpu`, metric_stride 8 | the T8 block cache |
| 128 | `CLIPLoader` | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`, type `minimax` | Qwen3-VL 32B text encoder in nvfp4 (needs Blackwell) |
| 119 | `VAELoader` | `minimax_h3_video_vae_fp16.safetensors` | video VAE |
| 120 | `VAELoader` | `minimax_h3_audio_vae_fp32.safetensors` | audio VAE |
| 138 | `PrimitiveStringMultiline` | the prompt | |
| 151, 152 | `PrimitiveInt` | width, height | |
| 132 | `PrimitiveFloat` | duration in seconds | |
| 131 | `ComfyMathExpression` | `max(5, round(a * 24)) + (5 - (max(5, round(a * 24)) % 17)) % 17` | frames: the smallest 17k+5 ≥ max(5, round(seconds × 24)) |
| 136 | `MiniMaxH3ReferenceToVideo` | prompt 138, width 151, height 152, length 131, ref_image_size `match`, clip 128, vae 119, audio_vae 120 | text and reference conditioning (output 0) and an empty video+audio latent (output 1) |
| 129 | `RandomNoise` | noise_seed | a new random 48-bit seed for every clip, unless one is given |
| 123 | `KSamplerSelect` | `res_multistep` | |
| 124 | `BasicScheduler` | scheduler `simple`, steps 25, denoise 1, model 142 | |
| 126 | `BasicGuider` | model 142, conditioning from 136 (or the last pin) | one positive conditioning, no CFG (H3 is CFG-distilled) |
| 125 | `SamplerCustomAdvanced` | noise 129, guider 126, sampler 123, sigmas 124, latent from 136 (or the sound-holding node) | |
| 122, 121 | `VAEDecode`, `VAEDecodeAudio` | | picture and sound |
| 130 | `CreateVideo` | fps 24 | |
| 92 | `SaveVideo` | format and codec `auto`, prefix `video/<clip id>-<8 hex>` | H.264 at 24 fps with AAC at 32 kHz stereo, with the graph embedded in its metadata |

The graph has no `ModelSamplingMiniMaxH3` node, so the model's built-in shifts apply (12 for video and 3 for audio in ComfyUI v0.36.0). The T8 block cache always computes H3's first block; when both the video and the audio are stable enough (residual difference under 0.12) it reuses the residual of the later blocks instead of computing them. It is off before 8% and after 95% of the steps, refreshes after 2 hits in a row, and keeps its cache in CPU memory. It is approximate, so the same seed with and without it is not pixel-identical.

**What `comfy_r2v.py` sets and adds for each clip:**

- Prompt, length, seed: node 138 gets the prompt file's text; node 132 gets `seconds`; node 129 gets `random.randrange(2**48)` or `--seed`.
- Size: nodes 151 and 152 (5.7).
- Reference pictures: each image becomes a `LoadImage` node wired to `ref_images.ref_image_<i>`, sent as it is (the node scales it).
- Reference videos: each becomes a `VHS_LoadVideo` node (force_rate 24, every frame) wired to `ref_videos.ref_video_<i>`. Every video is re-encoded with ffmpeg `-an`, so it is silent (09-28: a reference clip's sound came back sung as a foreign voice).
  - Footage (path contains `/footage/`), with no stills: it fills the film's frame, centre-cropped (`scale=W:H:force_original_aspect_ratio=increase,crop=W:H`), at `--footrows` rows on its short side, never scaled up. With stills: fitted inside the frame at the render size, keeping its shape. Why fill: H3 copied a wide reference as a thin strip between black bars in a tall frame (10-09), and several videos sent whole came back boxed. Why fit with stills: filled, a meme film dropped its caption banner after 1 s (10-10). Why 360 or 480 rows: the footage reference is 21-52% of an edit's GPU time at render size; smaller references gave 18-29% less GPU on long clips and looked the same at 720p. Never with stills: at 360 rows a talking head's speaker vanished, at 480 a chart came out too small.
  - Style and motion clips (any other path) go 360 rows tall (`scale=-2:360`). Why: the node encodes a reference video at up to 1344x768 for 16:9, so full-size references cost several times the clip's own tokens (one launch clip on a B200 went from 13.5 to 4.9 min).
- **Sound held fixed** (`--audio=inpaint`, the default): `ffmpeg -af apad=whole_dur=<seconds> -t <seconds>` pads or cuts the clip's part to exactly `seconds`, as a WAV. `LoadAudio` goes to `ref_audios.ref_audio_0` and also to `VAEEncodeAudio` (audio VAE 120) → `SetLatentNoiseMask` with a `SolidMask` of value 0.0 → `LTXVConcatAVLatent` (video_latent = node 136 output 1, audio_latent = the masked sound) → the sampler's `latent_image`. Mask 0 means the sound is kept as given at every step and never denoised: H3 draws only the picture, against the exact voice and music. All stock ComfyUI nodes; no extra render time. Why: given the voice only as a reference, H3 re-speaks it: word errors were 59-92% on the production graph; held fixed they were 0% once the voice was padded to the clip's length (3-18% unpadded, from words invented in the silent tail); lip and beat sync were judged best of the three ways tested (10-08). With `H3_AUDIO_MODE=reference` the sound goes only as `<Audio 1>`.
- **Pins**: a `video` pin is first turned into the frame at `at` seconds (`ffmpeg -ss`); every pin picture is scaled to cover the render size and centre-cropped. Each becomes a `LoadImage` node and a `MiniMaxH3AddGuide` node (positive = the previous guide or node 136, vae 119, latent = node 136 output 1) with `frame_idx` = min(round(seconds × 24) − 1, max(0, round(t × 24))). The guides chain into node 126's conditioning. Why: an attached still has no time, so whatever it shows can appear in any frame; a pin fixes what the frame shows at that moment. With pins a film kept one studio, cut hard at every pin, and popped balloons stayed gone (10-09). A pin lands within about half a second of its time.
- **The call**: all input files travel with the call as `{name: bytes}`, named `<8 hex>-<file name>`: `modal.Cls.from_name('h3-render', 'H3')().render.remote(graph, files)`. The returned mp4 is written to the output path.
- `--footage=guide|v2v50|v2v70` (off) lays the footage segments end to end on the clip's own timeline (`guide` pins a real frame every 12 frames; `v2vN` makes the footage the starting latent at denoise N/100). Off: it kept the footage real, but H3 then drew none of the effects the rows asked for.
- `R2V=v2`, `v2-shipped` or `v2-sage` stops `comfy_r2v.py` with a message: the newer R2V V2 graph is not in this repo.
- Flags that exist for tests and that render-all never passes: `--te=bf16`, `--unet=bf16` (the full 66 GB model), `--nocache`, `--steps=N`, `--sampler=X`, `--refmax`, `--turbo` (Magic Hour's I2V speed settings with a turbo LoRA that `modal_h3.py` does not download; untested here), `--nosage`.

### 5.4 What the H3 node does with these inputs (ComfyUI v0.36.0, `comfy_extras/nodes_minimax_h3.py`)

- Tags: references are labelled pictures first, then videos, then standalone sound, each numbered from 1: `<Picture i>`, `<Video k>`, `<Audio j>`. The node says to use the same tags in the prompt. Our prompts say "Image N", "Video N" and "Audio N" (fal's names), except on swap clips. The text encoder sees only the tags; it never hears the sound.
- Limits: 9 pictures, 3 videos, 3 standalone sounds (inputs `ref_image_0` … `ref_image_8`, 0-indexed).
- Pictures (`ref_image_size: match`): each scaled down, never up, keeping its shape, to the clip's pixel area, each side rounded to 32.
- Videos: a canvas with a 768 short edge, capped at 768 × 1344 (1344x768 for 16:9); a smaller video keeps its own size, rounded to 32. Frames past the clip's frame count are dropped and the rest cut down to 17k+5. A video needs at least 5 frames (the tooltip says 2-15 s). The text encoder sees videos at 2 fps. Reference tokens ride through every sampling step, so reference size is render time.
- Length: frames snap up to 17k+5 at 24 fps; the tooltip calls 124-362 frames (about 5-15 s) the trained range. Our clips run from under 1 s (one-beat footage shots, tested at 22 frames) to 15 s.
- `MiniMaxH3AddGuide`: one picture encoded by the video VAE and anchored at `frame_idx`, re-injected at every step and never denoised. `frame_idx` past the clip's frames is an error.
- `LTXVConcatAVLatent`: keeps the video latent and swaps in our sound. A sound shorter than the latent is zero-padded and the padding left unmasked, so H3 generates it; that tail lies past `seconds` (up to 16 frames) and is never heard, because the join plays only the soundtrack.
- Sound format: the parts are 44.1 kHz stereo MP3s; the node resamples to the audio VAE's 32 kHz. A mono part was never tried.

### 5.5 What this graph adds to Magic Hour's production graph

`r2v_v1.json`, as Magic Hour's notebook runs it, has neither of the two things the films depend on:

1. **The clip's own sound held fixed** (audio inpainting), on every H3 clip with an `audio` file. Without it, H3 re-speaks the voice and the mouths follow H3's version.
2. **Pictures fixed at set frames** (`MiniMaxH3AddGuide`), on every clip that has pins: the shots the planner pins (PAINTED.md asks for a pin where each shot opens on a set picture), footage shots' first frames and zooms, swap clips' swapped first frames, shots continued across a seam. Launch films write no pins.

Both use nodes that ship with ComfyUI v0.36.0, so Magic Hour's graph needs only the extra wiring. Other differences from a plain run of that graph: the inputs are prepared outside the graph (footage filled or fitted at render size or 360/480 rows; style and motion clips at 360 rows and silent; pins fitted to the render size; the sound padded to the clip's length); a one-line fix to the T8 cache node (5.6); SageAttention off on a B200; and **no prompt enhancement of any kind**. If Magic Hour's H3 service runs a prompt rewriter (MiniMax's hosted rewriter, fal's `prompt_expansion_mode`, or its own), it must be off for these prompts. Why: a rewriter summarised long prompts to a paragraph a shot and dropped their framings and timings (09-17); MiniMax's own rewriter cut about 17%, mostly the consistency lines (09-08); style words added by a rewriter fixed one film's look but made its motion worse (09-30).

### 5.6 The GPU worker on Modal: `research/h3/modal_h3.py`

- App `h3-render`. A volume `h3-weights` is mounted at `/weights`; ComfyUI lives at `/opt/ComfyUI`.
- Image: base `nvidia/cuda:12.8.1-devel-ubuntu24.04` with Python 3.12; apt git, ffmpeg, aria2, wget, libgl1, libglib2.0-0, build-essential; torch 2.8.0, torchvision 0.23.0 and torchaudio 2.8.0 (cu128), plus setuptools, wheel, packaging, ninja and requests; ComfyUI `v0.36.0` (git tag) with its requirements and `huggingface-hub<2.0`; custom nodes `kijai/ComfyUI-KJNodes`, `T8mars/comfyui-minimax-h3-blockcache-T8` and `Kosinkadink/ComfyUI-VideoHelperSuite`, each cloned at its latest commit (unpinned), with their requirements; SageAttention `v2.2.0` built with `CC=gcc CXX=g++ TORCH_CUDA_ARCH_LIST=12.0 MAX_JOBS=8 pip install . --no-build-isolation` (for sm_120 only: RTX PRO 6000 Blackwell, RTX 5090); an `extra_model_paths.yaml` pointing `diffusion_models`, `text_encoders` and `vae` at `/weights/…`.
- Weights: `modal run research/h3/modal_h3.py::download` downloads them once with aria2c (16 connections) from the Hugging Face repo `Comfy-Org/MiniMax-H3`:

  | File | Size |
  |---|---|
  | `diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors` | 20.97 GB |
  | `text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 15.69 GB |
  | `vae/minimax_h3_video_vae_fp16.safetensors` | 5.21 GB |
  | `vae/minimax_h3_audio_vae_fp32.safetensors` | 0.61 GB |
  | `diffusion_models/minimax_h3_ref2va_bf16.safetensors` | 66 GB, used only by `--unet=bf16`; remove it from `WEIGHTS` on a new account |

  The four files the films use total 42.5 GB (39.6 GiB); the model and the text encoder alone are about 37 GB.
- Class `H3`: `gpu=['RTX-PRO-6000', 'B200']` (an RTX PRO 6000 Blackwell first, a B200 if none is free; the file's header comment says "B200 first", the code is what runs), `timeout=3600` per call, `scaledown_window=30` (a container stops after 30 s idle), `max_containers=40` (the account's GPU cap binds first: 10 on Modal's Starter plan).
- Container start (`@modal.enter`): patches the T8 node, then starts ComfyUI (`python -u main.py --listen 127.0.0.1 --port 8188 --disable-auto-launch --dont-print-server --input-directory /tmp/comfy/input --output-directory /tmp/comfy/output --user-directory /tmp/comfy/user`, with `PYTHONNOUSERSITE=1` and `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`) and waits up to 300 s for `/object_info`.
- The T8 patch: in `custom_nodes/comfyui-minimax-h3-blockcache-T8/nodes.py`, `PREFETCH_CLEANUP_TAKES_MODULE = hasattr(comfy.model_prefetch, "GRAPH_MODULES")` becomes `PREFETCH_CLEANUP_TAKES_MODULE = "module" in inspect.signature(comfy.model_prefetch.cleanup_prefetched_modules).parameters`. In v0.36.0 `cleanup_prefetched_modules(module, comfy_modules)` takes two arguments, but `GRAPH_MODULES` does not exist; unpatched, T8 calls it with one argument on its first cache hit and fails. The patch is a text replacement at container start (the same edit at image build time silently did nothing). If the line ever changes, the replacement does nothing and nothing says so.
- `render(graph, files)`: writes each file into `/tmp/comfy/input/`; if the GPU's compute capability major is 10 (B200), sets node 141 to `disabled`; POSTs `{"prompt": graph, "client_id": …}` to `/prompt`; polls `/history/<id>` every 3 s until it completes (raises on `status_str == "error"`); returns `{"mp4": <bytes>, "seconds": <POST to completion>, "gpu": <device name>}`. `seconds` includes model loading when the container is fresh, not container boot or ComfyUI start.
- Setup on a new Modal account: 7.2.

### 5.7 Render sizes

`comfy_r2v.py` sets the size: 16:9 is W×H with H = `--rows` (no flag: 832x480) and W = round(H × 16/9 / 32) × 32; 9:16 is the same, turned; any other ratio a:b keeps the 16:9 tier's pixel count with each side rounded to 32 (k = √(W·H / (a·b)), width = round(a·k/32)·32, height = round(b·k/32)·32).

| `GPU_ROWS` | 16:9 | 9:16 | 1:1 | 4:5 | 3:4 | 4:3 | 21:9 |
|---|---|---|---|---|---|---|---|
| unset or empty (480p tier) | 832x480 | 480x832 | 640x640 | 576x704 | 544x736 | 736x544 | 960x416 |
| 704 (720p tier) | 1248x704 | 704x1248 | 928x928 | 832x1056 | 800x1088 | 1088x800 | 1440x608 |
| 800 (1080p tier) | 1408x800 | 800x1408 | 1056x1056 | 960x1184 | 928x1216 | 1216x928 | 1632x704 |
| 480, set explicitly | 864x480 | 480x864 | 640x640 | 576x704 | 544x736 | 736x544 | 992x416 |

Leave `GPU_ROWS` unset or empty for the 480p tier: set to `480` it gives a different width and a different reuse key. The film is written at H3's size; to deliver 720p and 1080p as 1280x720 and 1920x1080, scale up at the end (the code does not). `./film` has no resolution option; the tier is `GPU_ROWS`. Only the `2-5d-hybrid` card renders at 704 by default. Text gets steadily sharper with more rows, with no threshold (10-01/10-02).

### 5.8 GPU, memory and time

- GPUs: the nvfp4 text encoder needs Blackwell (ComfyUI v0.36.0 turns nvfp4 compute off below compute capability 10; whether it then falls back or fails was not tested). Known to work: RTX PRO 6000 Blackwell (96 GB) and B200. An RTX 5090 (32 GB) ran the same graph in a 10-03 test, but a clip with reference videos took about 15 min. On an older GPU, the bf16 text encoder (`--te=bf16`, 51.5 GB, not downloaded) or the int8 one would be needed; untested apart from the bf16 encoder looking nearly the same on one seed (10-03).
- Memory: no peak VRAM figure was recorded. The T8 cache lives in host memory. Modal's bill for one busy hour (10-10) works out to about 2.3 CPU cores and 56 GiB of host memory per GPU, which added 12-18% to the GPU cost.
- GPU seconds per clip (warm RTX PRO 6000, 480 rows, from the clip logs): clips with no footage reference (painted, launch), median 22.0 GPU seconds per rendered second (p10 19.3, p90 28.0); footage clips, median 38.9 (short clips, so the per-clip floor weighs); a fit on 469 calls (10-10): about 21 per rendered second, 22 per second of footage sent at render size, 2.9 per pin, 9 per still, and a floor of 48-60 per clip. `planner-cost.py` holds a fit on 310 calls (10-07): RTX 23.49 × clip seconds + 15.02 × reference-video seconds + 5.53 × reference images − 25.6; B200 17.29, 11.26, 4.96, −63.4.
- Per film: median 781 GPU seconds, about 23 per second of film: painted films about 23, footage edits 51-63 (35 films). The latest batch (21 films, 10-12) averaged 26 GPU seconds and about 8 s of render wall time per second of film, with all of a film's clips at once.
- Fresh containers: a clip on a fresh container pays about 10-16 s of model loading inside its logged seconds, and about 21 s outside them (10 s to start the container, 12 s for ComfyUI, 2 s to return). A warm call adds 2-4 s.
- Wall time: a film's render time is about its slowest clip when every clip has a GPU; clips continued across a seam add up. Under a 10-GPU cap shared by several films, clips waited 5-28 min (10-10).
- Resolution: render time grows as about pixels^1.137 on the RTX PRO 6000, measured from 832x480 to 1248x704: about 2.45x at 1248x704 and about 3.25x at 1408x800 (the 800-row figure extrapolated). The Overview rounds these to 2.5x and 3.5x. A sweep on another H3 graph (10-02) gave pixels^1.5.
- GPU type: a B200 renders about 1.4-1.5x faster than an RTX PRO 6000 at 2.06x the hourly price, so it costs about 1.4-1.5x more per clip; that is why the RTX PRO 6000 is asked for first (10-06: about $0.90 a film against $1.40 on B200s).

### 5.9 Running on Magic Hour's own GPUs instead of Modal

The Modal coupling is one call in `comfy_r2v.py`:

```python
import modal
res = modal.Cls.from_name('h3-render', 'H3')().render.remote(g, SEND)
```

Everything before it builds a plain ComfyUI API graph `g` and a dict `SEND` of input files; everything after writes `res['mp4']`.

**Keep this repo's graph.**

1. Build a worker image like `modal_h3.py`'s: CUDA 12.8, Python 3.12, torch 2.8.0 cu128, ComfyUI `v0.36.0`, KJNodes, T8 (pin it at `36336dc`, its commit of 2026-09-07, which still has the patched line) and VideoHelperSuite, each pinned, ffmpeg, and SageAttention 2.2.0 built for your GPU's architecture (`TORCH_CUDA_ARCH_LIST=12.0` covers the RTX PRO 6000; a B200 build was never tried, so set `sage_attention` to `disabled` there as the worker does).
2. Put the four weight files in ComfyUI's `diffusion_models`, `text_encoders` and `vae` folders, or point an `extra_model_paths.yaml` at them.
3. Apply the T8 one-line patch.
4. Run one ComfyUI process per GPU and keep it running between clips (a warm process skips the 10-16 s model load), with `--input-directory`, `--output-directory`, `--user-directory` and `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`. ComfyUI runs one prompt at a time.
5. Serve `render(graph, files) → {mp4, seconds, gpu}` exactly as `H3.render` does. Keep the mp4's embedded metadata (no `--disable-metadata`): render-all reads each clip's seed and prompt from it.
6. Replace the two lines above with a call to that service. Nothing else in `comfy_r2v.py`, render-all or the graph changes.
7. Add a queue: render-all sends every clip of a film at once, each needing one GPU for its whole render. Modal allows 3,600 s per call; the longest clip in the 10-10 batch took 694 GPU seconds.
8. Run `comfy_r2v.py`'s side on a machine with ffmpeg: it resizes footage, pins and sound before upload.

**Use Magic Hour's own H3 service and graph.** It must accept, for each clip: the prompt, verbatim; width and height (multiples of 32); the frame count (17k+5 at 24 fps); a seed (random unless given); up to 9 pictures (`<Picture N>`); up to 3 silent reference videos, prepared as above (`<Video N>`); one sound (`<Audio 1>`) that is also held fixed as the clip's own track, padded to `seconds`; and any number of pins as (frame index, picture fitted to the size). It must run with these settings: the ref2va pruned int8 model, the nvfp4 text encoder, the fp16 video VAE, the fp32 audio VAE, `res_multistep`, scheduler `simple`, 25 steps, no CFG, the T8 cache at the values above, `ref_image_size` `match`, prompt enhancement off. If the newer graph splits long clips into windows, render each clip as one window: every prompt times its rows from the clip's own 0 s over the whole clip, and a second window would replay them from its own start. As tested in September and October, Magic Hour's public H3 API and fal take sound only as a reference and no pictures fixed at set frames alongside references, so neither can render these films at full quality.

**Testing a port.** First for free: run render-all against a stand-in for the worker that logs each graph and the SHA-1 of each file, and compare with a finished run's `render-gpu/<id>.json` and `.key` files (8.1). Then render a finished run's clips with their recorded seeds (`manifest.json` `render.clips[].seed`, put into each clip's `seed`) after moving `render-gpu/` aside, and check that each clip has the right size, 24 fps and a 17k+5 frame count; that the clip's own audio track matches its soundtrack part (the sound was held); and that the frame at round(t × 24) matches each pin. On Modal the same seeds reproduced a film at 43 dB; whether the same seed gives the same clip on another GPU type was not measured.

### 5.10 Switches

| Name | Default | What it does |
|---|---|---|
| `GPU_ROWS` | unset (`auto.mjs` passes an empty string) | render tier: 704 or 800 (5.7); part of the reuse key |
| `H3_BUDGET_USD` | 5; `./film` sets 20 | the fal-priced render cap (5.2 step 7) |
| `H3_DURATION` | unset | the film's exact length, passed to the join; set by `--duration` |
| `H3_AUDIO_MODE` | `inpaint` | `reference`: sound only as `<Audio 1>` (the measured worse mode) |
| `H3_SEED` | unset | one seed for every clip without its own `seed` (A/B tests) |
| `EDIT_TRIM` | on | `0`: render the planner's `seconds` instead of span + 0.3 |
| `SWAP_PIN` | on | `0`: no swapped first frame |
| `TAGS` | `swap` | `all`: node tags on every clip (untested); `0`: none |
| `ZOOM_STEP` | 0.2 | seconds between zoom pins (0.4 was tried and set aside) |
| `NOVID` | off | `1`: no reference videos; clips go to `render-gpu-novid/`, the film to `final-novid.mp4` |
| `H3_FOOTAGE_MODE` | unset | `guide`, `v2v50`, `v2v70`: footage on the clip's own timeline (off: H3 then drew none of the asked effects) |
| `R2V` | unset | `v2`, `v2-shipped`, `v2-sage` stop the render (that graph is not in this repo) |
| `NANO_BANANA_MODEL`, `NANO_BANANA_VIA` | `gemini-nano-banana-2.1`, fal | the swapped first frame's picture model |
| `ELEVENLABS_STT_MODEL` | `scribe_v2` | speech captions |

## 6. Maps and shots drawn in code

Three kinds of picture are drawn by code in headless Chrome, not painted by H3. None uses a GPU on Modal.

| What | Made by | Comes out as | Offered to |
|---|---|---|---|
| A map shot whose camera travels (a route, a march, a voyage, a pan from place to place, a globe turn), or that needs many exact labels, counters or borders changing over time | the `map_shots` tool (`research/h3/tools-maps.mjs`), which starts `agent/h3film/maps.mjs`, which runs the map engine in `agent/v2/` | one mp4 for each run of consecutive map clips, 1920x1080 (1080x1920 for 9:16), played in the film as it is | painted films (edits and minimal films too), never launch films |
| A simulation or a chart of real numbers | the `code_clip` tool (`research/h3/tools-codeshot.mjs`) | one mp4, played as it is or given to H3 as a reference video | every film |
| A still with exact words: a type still, an end card, a picture placed in the film's room | the `still` tool (`research/h3/tools-film.mjs`) and `agent/h3film/still.mjs` | a PNG that H3 gets as a reference picture or a pin | every film |

Where things stand: no film made with the map engine is rated 8 or more. The best is 7: `v41-x10`, a Hannibal map film of 10-11 (`batches/films/v41-x10`). The documentaries rated 8 showed their maps the other way: H3 painted each map from a real map still. That is why H3 still paints every map shot whose camera stays put, and the engine gets only the shots that travel. `code_clip` made a film rated 9 (`v42-x20`, 10-11: a ball bouncing in a spinning ring, one code clip and nothing else).

### 6.1 Which map shots go where

The planner decides per shot, from four texts it reads:

1. A paragraph the launcher adds to every painted film: H3 paints a map shot only when its camera stays on one place the whole shot, from a real map still (`reference_image` fetches a real map of the tightest area the shot shows; `storyboard` redraws it in the film's look, with no words); the camera holds, drifts or pushes in; a new place is a hard cut to its own map still. Every shot whose camera moves across the map, or that needs many exact labels or borders changing over time, comes from `map_shots`, called once right after `make_soundtrack` with just those clips.
2. The `reference_image` description: a map shot starts with a real map of the tightest area (Wikimedia Commons first; never a world or continent map for one region), redrawn in the film's look, the card's own map sample frames as style only.
3. `skills/h3-film/usecases/map-video.md` §0, for map videos: plan the film as map clips and cutaway clips; facts first, from at least two sources, at the top of `PLAN.md`; lines written as talk (short sentences, one fact each, at most six named places); one `map_shots` call after `make_soundtrack`. The rest of that file was written for H3-painted maps and does not apply to engine shots.
4. The `map_shots` description (6.2).

Two of these texts are narrower than the others. The `map_shots` description opens "FAR MAP SHOTS ONLY" (a camera that travels farther than one map picture holds: a globe turn, continent to continent, space down to a city), and a bullet of §0 says "Far shots only". The launcher's paragraph and §0's heading send every shot whose camera moves across the map.

`PAINTED=1` sets `MAPS=1`, and `MAPS=1` clears `CODE_SHOTS`. The tool server gets `MAPS=1` and `MAPS_CARD=<card id>`; `mcp.mjs` then registers `map_shots` and `make_soundtrack` also writes `soundtrack/soundtrack.json`, which `map_shots` needs. The four map cards (`toy-map`, `satellite-map`, `cartoon-map`, `parchment-map`) and `dark-documentary` set the look of the H3-painted shots and cutaways; the engine's look is set separately (6.3). Why the split: a fully H3-painted Hannibal map film had territories all over the place; H3-painted maps were fine as long as the camera does not travel across the Earth (10-09); a march over the Alps has to move (10-11). The engine draws real coastlines, borders and routes and sets every word exactly.

### 6.2 The `map_shots` tool (`research/h3/tools-maps.mjs`)

Registered only when `MAPS=1`. One call per film, right after `make_soundtrack`.

| Field | Type | Meaning |
|---|---|---|
| `topic` | string, at least 20 characters | the story and every fact the map shows (places, dates, routes, numbers, who holds what) |
| `clips` | array, at least 1, of `{clip: int ≥ 1, intent: string ≥ 10}` | only the travelling map clips, numbered as `make_soundtrack`'s parts (1 = the first); `intent` = what the viewer sees happen on the map, in the order the words say it |

What the call does: refuses if `<run>/soundtrack/soundtrack.json` is missing ("make_soundtrack first"); plans the sections with `planMaps()` from `maps.mjs` (consecutive clip numbers become one section, one continuous map shot; a clip number outside the soundtrack's parts is refused); refuses if a map job is already running for this run; deletes and recreates `<run>/maps/`; writes `maps/request.json` and a copy of the soundtrack answer as `maps/soundtrack.json` (the map is timed to this copy); starts `node agent/h3film/maps.mjs <run>` detached, output to `maps/maps.log`, its pid in `maps/pid`; and answers at once:

```json
{ "started": "the map shots are being made in the background (log <run>/maps/maps.log); the render waits for them",
  "map_clips_for_render_json": [
    { "id": "clip1", "code": "<run>/maps/clip1.mp4", "seconds": 6.73, "span": 6.23 },
    { "id": "clip3", "code": "<run>/maps/clip3.mp4", "seconds": 16.1, "span": 15.6 } ],
  "merged": [ "clips 3, 4 are one continuous map shot: render.json has ONE entry for them, \"clip3\"" ],
  "h3_clips": "paint only clip 2 with H3 (stills, prompts), as usual" }
```

`maps/request.json`: `{card, ratio, topic: "<the planner's topic>\n\nThe film's brief, as the user gave it: <brief.txt>", clips, at}`. `ratio` is the tool server's `RATIO` (16:9 when unset). The brief part is the whole `brief.txt`, the producer's text included. The planner copies the entries into `render.json` exactly, in film order among its own clips, with no prompt, images, videos or audio: `span` = the section's length (the sum of its parts), `seconds` = `span + 0.5` (the engine renders half a second past the cut; the join trims it), `id` = `clip<first clip number>`. The description changes with the card: for `satellite-map` it promises a satellite plate, for every other card a clay relief model on a felt table with toy props and cut-out figures standing on it. It still says the map takes 30-50 minutes, a figure from older stage sessions; measured on Sonnet: 6.3 to 13.4 minutes. Nothing in code stops the planner calling `make_soundtrack` again after `map_shots` (only the tool text forbids it); a second soundtrack would leave the map timed to the old one.

### 6.3 The map job (`agent/h3film/maps.mjs`)

Runs as `node agent/h3film/maps.mjs <run>`. It loads `.env.local` (only keys not already set). Everything lands in `<run>/maps/`:

```
maps/
  request.json, soundtrack.json   written by the tool
  pid, maps.log                   the job's process id and log
  skeleton.json                   the beats as first built (restored after direction)
  direction/                      the stage folder (env V2_OUT and VOX_OUT)
    beats.json                    the film plan in the engine's format
    beats.forked-from.json        the proven film it was copied from
    vo/vo.json, vo/align-<n>.json the word timings, and the raw alignment of line n
    choreo/<shot>.json            the choreography stage's states per map section
    kit_film/                     the cast cut-outs (PNG) and jobs.json
    DIRECTION-NOTES.md            the direction stage's facts and beat-by-beat notes
  film/shots/<shot>/              one workspace per map section (env V2_FILM = maps/film)
  logs/                           each stage session's log and full prompt (env RUNS_DIR)
  .direction-done, .choreo-done   stage markers (a rerun resumes after them)
  clip<N>.mp4, clip<N>-sheet.jpg  the finished map shots and an 8-frame contact sheet each
  done.json  or  failed.json
```

The run's slug for the stages is `h3-<run name without h3film->`.

**Sections** (`planMaps(run, clips, soundtrack)`): parts = `soundtrack.parts` (a soundtrack with no parts is one part, the whole film); sorted, de-duplicated clip numbers; a clip that follows the previous one joins its section. Each section: `start` = its first part's start, `span` = last part's end minus `start`, `seconds` = `span + 0.5`, `id` = `clip<first>`, `mp4` = `<run>/maps/clip<first>.mp4`. It also returns the clip numbers left for H3.

**The look:**

| Card | Engine style | Copied from | Extra |
|---|---|---|---|
| `satellite-map` | satellite | `swim-example` (the longest straight swim short) | none |
| `dark-documentary` | toy | `blackdeath-example` (the Black Death film) | `look: "dark"` from `agent/v2/template/looks.json` |
| any other card | toy | `blackdeath-example` (the Black Death film) | none |

Why only the card (10-12, 10-13): from 10-11 night the planner picked the map's style and colours (`look` on `map_shots`: the map leaned 35% toward the film's colours, paper only on the user's words). No film made that way was liked: two Hannibal takes on paper (v50, nm) and three toy takes with the colour lean on 10-12 were all judged below v48, which was made before it. It was taken out on 10-13, from the tool and the map job: the map takes its card's look, as v48 was made, and the planner is no longer asked (a pick that is never used would only mislead the planner about the map it gets). `map_shots` is offered to every painted film, so its shorter text is the one place where a drawn film's planner input differs from the 10-12 batch's.

**One beat per spoken line, timed word by word.** For each part k, take the lines of `soundtrack.lines` whose `clip` is k (a line with no `clip` goes to the part its `at` falls in). Each line is one beat. A part with no line is one beat with empty narration, its `vo_start` 0.3 s after the part's start and no file. Beats split each pause between two lines at its middle; a part's first beat starts at the part's start and its last ends at the part's end; the last beat of a section gets 0.5 s more. Beat fields: `id` (1, 2, … over the whole film), `narration`, `t0` (film time), `vo_start` (the line's `at`), `vo_file` (`<run>/soundtrack/vo-<line number>.mp3`), `vo_duration`, `shots: [{id: "a", dur, dur_planned}]`. Only lines in map parts are aligned: each line's own recording and its text go to ElevenLabs forced alignment (`POST api.elevenlabs.io/v1/forced-alignment`, multipart `file` and `text`; 3 tries), cached in `direction/vo/align-<n>.json`. `direction/vo/vo.json` holds one entry per beat: `{beat, file, text, duration, words: [{w, t0, t1}]}`, times from the start of that line's recording. Why: the engine lands every change on a phrase of the narration, so a map move happens on the word that names it.

**The copy of a proven film.** Each map beat starts as a copy of the states (the timed changes, 6.5) of one map beat of the proven film: the film's i-th map beat of N takes the proven film's map beat at index `round(i × (M − 1) / (N − 1))` of M. The beat also gets `surface: "map"`, `map: {section: "map", states: [...]}`, the planner's `intent`, and the proven beat's `scene` and `element_motion` on its shot (`kind: "map"`). All map beats share the section id `map`, so a later run of map beats returns to the same world. Why: the two best map films of the September pipeline came from a plan that started as an exact copy of a reviewed film and was edited in place, so camera rhythm, walks, reveals, counts and sizes came for free.

`direction/beats.json` (excerpt, the shape of a 10-12 Hannibal run's file):

```json
{ "project": "h3-nm-x10", "aspect": "16:9", "style": "collage", "map_style": "toy",
  "topic": "<request.json topic>", "collage_style": "…", "scene_style": "<the era and palette the cast is painted in>",
  "cast": [ { "id": "hannibal", "prompt": "Hannibal Barca, Carthaginian general: …", "ref": "<optional id>", "aspect": "<optional, default 3:4>" } ],
  "captions": false, "duration": 30.99,
  "beats": [ { "id": 1, "narration": "…", "t0": 0, "vo_start": 0.3, "vo_file": "…", "vo_duration": 5.8,
               "surface": "map", "map": { "section": "map", "states": [] }, "intent": "…",
               "shots": [ { "id": "a", "dur": 6.73, "dur_planned": 6.73, "kind": "map", "scene": "…", "element_motion": "…" } ] } ] }
```

Fields copied from the proven film and unused here: `voice`, `music`, `mix`, `provider`, `image_model` (the film's sound is the planner's soundtrack). `aspect` is `9:16` when `request.json` says 9:16, otherwise `16:9`.

**Stages:**

1. Direction (`node agent/v2/run.mjs direction <slug>`, 6.4): one Claude session recasts the copied states onto this story. Tried twice at most.
2. Restore: the soundtrack is the clock, so the job puts back from `skeleton.json` each beat's `id`, `narration`, `t0`, `vo_start`, `vo_file`, `vo_duration` and shot durations; drops beats the session added; puts back missing beats; keeps `surface: "map"` and the section id only on the planner's map beats; resets `aspect`, `map_style`, `look` and `captions: false`.
3. Choreography (`node agent/v2/run.mjs choreo <slug>`, 6.4): one Claude session for every map section builds, looks and fixes.
4. Final render: rebuilds every section's workspace from the final states (`agent/v2/tools/map_section.mjs <slug>` with `MAP_NO_PREVIEW=1`), checks the number of sections, then renders all at once: `npx --yes hyperframes@0.8.20 render <workspace> --workers 3 --quality standard --output <run>/maps/clip<N>.mp4`. A section fails on `[Browser:PAGEERROR]`, a missing mp4, or an mp4 more than 0.1 s shorter than its span. It writes `clip<N>-sheet.jpg` (8 frames).
5. `done.json`: `{clips: [{id, code, seconds, span}], sections: [{clips, start, span, seconds, id, mp4, shot}], minutes, model, stages: [{stage, label, turns, s, usd}], stages_usd}` (`model` is always "claude", a label; `stages` from each session's last log line). Any error writes `failed.json` (`{error}`, at most 2,000 characters) and exits 1. A run started by hand resumes after the last finished stage; a new `map_shots` call starts over.

The job gives the stages: `V2_OUT` and `VOX_OUT` = `maps/direction`, `V2_FILM` = `maps/film`, `RUNS_DIR` = `maps/logs`, `H3_MAPS=1`, `H3_RUN`, `FORK` (the proven film's name), `MODEL` = `MAPS_MODEL` or `claude-sonnet-5-5`, `EFFORT` = `MAPS_EFFORT` or `medium`, `FAST` = `MAPS_FAST` or `0`, `CLAUDE_BIN` (or the first `claude` on PATH), `MAP_MODEL=claude` (only labels `done.json`), `PRODUCER_PLAYER_READY_TIMEOUT_MS=180000` (HyperFrames waits up to 3 minutes for a map page to load its geometry before the timeline exists; its default is 45 s).

### 6.4 The two Claude stages (`agent/v2/run.mjs`)

Each stage is one Claude Agent SDK session (`@anthropic-ai/claude-agent-sdk` 0.3.235, locked in `agent/package-lock.json`) with: `pathToClaudeCodeExecutable` = `CLAUDE_BIN`, which `maps.mjs` sets to the `claude` on PATH (started by hand without it, the SDK's bundled CLI 2.1.235 refuses the 5.5 models, so set `CLAUDE_BIN`); model `MODEL` (falls back to `claude-opus-5-5` only when started without `maps.mjs`), effort `EFFORT`, fast mode only with `FAST=1`, `thinking: {type: "adaptive", display: "summarized"}`; `cwd` = the repo root with `settingSources: []` (no `CLAUDE.md` or `AGENTS.md` reaches it) and `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`; `allowedTools` Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch with `permissionMode: "bypassPermissions"` (this only approves them in advance: no `tools` list is passed, so every built-in Claude Code tool is available) and the sandbox off (it refused writes even when allowed, and the builds fetch from CDNs); `maxTurns: 250`; Bash commands may run 15 minutes by default and 30 at most (`BASH_DEFAULT_TIMEOUT_MS=900000`, `BASH_MAX_TIMEOUT_MS=1800000`: a section build took 3-10 minutes, and the SDK's 2-minute default orphaned builds). No wall-clock cap. Logs and full prompts go to `logs/<label>.log` and `logs/<label>.<stage>.prompt.md` (the label is the slug, or `<slug>-<shot>` for a choreography session with one section; `logs/<label>` itself is a link to the session's folder). Sonnet 5.5 at medium: a second model key had kept the stages on Opus fast mode at $1.12 per choreography section (fixed 10-11).

**Direction prompt** (`stagePrompt("direction")`, about 34 KB) = a fixed opening (a non-interactive stage, the folders, Python at `.venv/bin/python`, work in few large steps) + `agent/v2/DOCTRINE.md` + `agent/v2/stages/direction.md` + an H3 block: the planner's topic; the narration is final, one beat per spoken line; beats with `surface: "map"` are the session's, the others are H3's cutaways and stay as they are; of `direction.md`, §0 and §4-§5 apply, §1-§3 do not; the planner's `PLAN.md` path; the copied film's own introduction and the other proven films as references only (`agent/v2/direction/`, `agent/v2/reference/*-sheet.jpg`); a move the base film lacks is copied state for state from the film that proved it (`agent/v2/template/mapfilm/MOVES.md`); keep each map beat's skeleton, change the content (every `on` phrase copied word for word from this beat's narration, places, camera looks, paint, cast ids and prompts, sprite files, colours, year stamps, counts, titles, `scene_style`); never change narration, ids, surfaces, section ids, times or durations; never add or delete a beat; write `DIRECTION-NOTES.md` with the facts first, each with its source. It edits `direction/beats.json` in place. Research is asked for, not checked.

**Choreography prompt** (`stagePrompt("choreo")`, about 122 KB) = the opening + DOCTRINE + `agent/v2/stages/choreo.md` + the shot data + the map beats in full + the path of `vo/vo.json` + for each section the file to write (`direction/choreo/<shot>.json`), the build command (`node <repo>/agent/v2/run.mjs map <slug> <shot>`) and the stills folder + the instruction to do every step for all sections together (edit all files in one turn, run all builds in one background command, look at all stills in one turn, at most two rebuild rounds) + reference sheets (`agent/v2/reference/joan-sheet.jpg`, `emuwar-sheet.jpg`) + `CHOREO_NOTE` if set + the state contract (`direction.md` from "## 4." on) + `MOVES.md` + `agent/v2/template/scene/SCENE.md` + the copied film's whole plan + a note that the cutaways are joined by hard cuts. Before the session, `choreo/<shot>.json` is seeded with the states direction left (`{"<beat id>": [state, …]}`); the session edits it, builds, reads every still and territory sheet, fixes, rebuilds; afterwards the states are folded into `beats.json`. A session that dies on an API error is retried once. Why one session for every section (`CHOREO_ONE`, on since 10-11): one session per section, each with a 150 KB prompt pasting two whole example films, cost the Hannibal film $1.76 in map stages; one session with only the copied film's plan cost $0.58. `CHOREO_ONE=0` restores one per section; `CHOREO_EXAMPLES=all` pastes the Black Death and Joan plans.

Text in these prompts that does not fit this repo (sessions have not tripped on it): the opening names an exemplar folder `<repo>/emuwar-1a` that is not here; `DOCTRINE.md` and parts of `direction.md` describe collage shots and keyframes, which map shots never use; `choreo.md` says the Joan plan follows while only the copied plan is pasted; `SCENE.md` describes scene beats, which the restore pass removes.

To run the stages without Claude Code: the prompts can be reused as `stagePrompt()` builds them. The session needs to read and edit `beats.json` and `choreo/<shot>.json`, run the build (minutes per call) and see its `stills/*.jpg` and `territory/*.png` as images, search the web, and run `node agent/v2/tools/map_data.mjs` when a section needs a data layer. Tool calls must be allowed to last longer than a build; give it a turn cap and a wall-clock cap; cache the long prompt; drop old builds' pictures from the history; keep the restore pass after direction.

### 6.5 Building a map section (`agent/v2/tools/map_section.mjs`, `shots.mjs`)

`node agent/v2/tools/map_section.mjs <slug> [shot …]` (or `node agent/v2/run.mjs map <slug> [shot …]`) reads `beats.json` and `vo/vo.json` from `VOX_OUT`, folds in `choreo/*.json`, and builds a workspace per section under `V2_FILM/shots/<shot>/` (only the named sections when shots are given). Consecutive beats with `surface: "map"` and the same `map.section` are one section, named after the head beat's shot (`1a`, `3a`).

**States** are the engine's input: a list of changes, each placed on a spoken phrase:

```json
{ "on": "Rome thought",
  "camera": { "look": [5.8, 44.9], "zoom": 460, "glide": 0 },
  "elements": [ { "id": "hn", "type": "sprite", "src": "assets/kit/hannibal.png", "at": [5.4, 44.7], "w": 1.6, "keep": true },
                { "id": "rome", "type": "territory", "colors": { "rome": "#6b3a8a" }, "set": { "Italy": "rome" }, "reveal": "from Rome, Italy" },
                { "id": "rl", "gone": true } ] }
```

Optional keys: `lead` (seconds before the phrase), `surface` (`plane` or `globe`), and in `camera` also `ease`, `pitch`, `heading`, `roll`, `fov`, `fit`. A state may give `"t": <seconds from the section's first frame>` instead of `on`. Timing: a word's time in the section = its beat's `vo_start` + the word's `t0` − the section's first `t0`. `on` is matched word for word against the section's aligned words, searching from this beat's first word or the previous match, whichever is later; words are compared in lowercase with everything but a-z, 0-9 and apostrophes removed, so a phrase in a non-Latin script would land where the search starts (no such map film has been made). The state lands at that word's time minus `lead` (default 0.15 s: the eye needs the picture just before the ear hears the word). A phrase not found stops the build with an error naming it. An element leaves at the end of the last beat that mentions it, unless `keep: true`, `gone: true` earlier, or it is a fill of named places.

The world carries over: each section's page also holds every earlier section's states at negative times, so the section opens on the world it left (paint on, routes drawn, figures arrived). A section's own first frame is its own first camera, and earlier year stamps and counters are gone at its first frame.

Checks and conversions, in order:

1. Every place name in cameras and elements must be in the gazetteer (`agent/v2/tools/data/mapgeo/geo.json`); unknown names stop the build of the section that has them (other sections drop those elements from the world they carry over).
2. `territory` elements become fills: `colors` maps a status to a colour, `set` maps whole places to a status, `reveal` sweeps the paint open (`from <place>` or `north`, `south`, `east`, `west`; `reveal_dur`, default 1.4 s); a later `set` repaints only what changed; `gone` clears the layer. Small countries inside a painted country take its status, and so does a small region cut out of a painted region. A `fill` given as a `hull` `within` a place is painted as that whole place (hand-drawn hulls left white patches); the stage texts say to paint only what the narration claims about a whole place. For every paint change a flat labelled picture goes to `<shot>/territory/<t>.png` (`territory_sheet.py`) for the choreographer to check.
3. Sea routes (`type: "route"`, `sea: true`) are pathed through water by `agent/v2/tools/sea_route.py` (A* on a grid over the engine's own land, cells of at least 0.05°, coast cells cost more, simplified to a few `via` points). A leg across the date line is not handled; with no water path the route draws as given.
4. Toy style only: every country named in a fill gets mountains, built by `agent/v2/tools/map_relief.py` as an OBJ mesh from the Copernicus GLO-90 elevation tiles (downloaded on first use into `agent/v2/tools/data/dem/` from `copernicus-dem-90m.s3.amazonaws.com`), cached in `agent/v2/tools/data/relief/<country>.obj`. Both cache folders are git-ignored. Regions get none, and neither does a country whose mainland box covers more than 400 square degrees (India, China, the US).
5. The cast cut-outs (6.7) are copied into every workspace as `assets/kit/<cast id>.png`.

The workspace holds `mapscreen.js`, `hyperframes.json` and `package.json` from `agent/v2/template/mapfilm/`; `assets/` (links to `agent/v2/tools/data/mapgeo/` plus `assets/kit/` and `assets/relief/`); `index.html` (the template with the size, duration, `P = {style, dur, w, h, relief, look, lookName}` and the timed states inlined); `states.json`; an empty `motion.js`; `MOTION-NOTES.md`; territory files. Size: 1080x1920 when `aspect` is 9:16, else 1920x1080. The preview (skipped with `MAP_NO_PREVIEW=1`) is `npx --yes hyperframes@0.8.20 render . --workers 1 --quality draft --output preview.mp4`, then one still per camera key into `stills/<film time>.jpg`, 720 px wide. The Python tools (`territory_sheet.py`, `sea_route.py`, `map_relief.py`, `scene_kit.py`) run as `.venv/bin/python` from the repo (`requirements.txt`).

### 6.6 The map engine (`agent/v2/template/mapfilm/mapscreen.js`)

A three.js scene driven by states. `index.html` mounts it, calls `setStates(states)`, then builds one paused GSAP timeline that tweens `{p: 0 → 1}` over the section's duration and calls `screen.apply(p * dur)` on every update; `window.__timelines = {main: tl}`. Everything on screen is computed from the time alone (no clocks, no animation frames), so HyperFrames can seek any frame. The page sets `window.__hfTimelinesBuilding` and fires `hf-timelines-built` when its async load is done. Libraries are fetched at render time from `cdn.jsdelivr.net` at exact versions: GSAP 3.14.2, three.js 0.184.0 with its addons, polygon-clipping 0.15.7; fonts from Google Fonts (Playfair Display, Inter). 24 fps.

| Style | Table and land | Light and camera | Words |
|---|---|---|---|
| toy (default) | felt table, plaster land raised with the relief meshes, plastic fills painted into the land | steep key light, tilted camera, depth of field, ambient occlusion, 3D props, cut-outs as cardboard standees with real shadows | labels as paper cards (Playfair Display 900), titles in Playfair Display |
| paper | paper table, extruded land slabs | ambient occlusion, near top-down | Playfair Display labels, dark red ink |
| satellite | NASA Blue Marble on Mercator (`bm_merc.jpg`) on the plane and `bm.jpg` on the globe, a flat dark ocean over the picture, fills at 70% | no shadows, no occlusion | Inter 800 capitals in white, yellow ink |

The dark look (`looks.json` `dark`, only for the `dark-documentary` card) replaces the toy colours (black table, bone-white land, red ink, a hard white key light, shaded relief multiplied into the land, black props), adds a stronger vignette and grain, and gives the cast its style.

Camera: a state's camera is `{look: <place | [lon, lat]>, zoom: "world" | "continent" | "region" | "local" | <distance>, pitch, heading, roll, fov, glide, ease, fit}` (a distance is in map units, 10 per degree of longitude; the four names are 3400, 1800, 1000 and 500); every key but `glide`, `ease` and `fit` carries over to later states. With no `glide`, a move takes a time set by how far the picture travels (`0.8 + 0.33 × log2(1 + 2 × frames)` seconds); the default ease is an S curve with its fastest point early, and some speed carries through each pose so the camera never stops dead; parked, it drifts slightly. `surface: "globe"` cross-dissolves to the globe.

Elements: `pin`, `route` (from, to, `via`, `straight`, `long`, `sea`, `at` = how far it has drawn, a distance `label`, `pins`), `fill` (a place or `places`, a `hull` of places `within` a country, `data` with a `ramp`, `src` for a flag, `reveal`), `sea`, `label` (`above: "<sprite id>"` hangs it over a standee), `ring`, `badge`, `cluster`, `ribbon`, `sprite` (a cut-out at a place, `w` in degrees, `walk`, `sway`, `flip`, `at: {route: "<id>"}` rides a route's drawing head), `stamps`, `title` (a year stamp or number; `count: [from, to]` counts up), `glow`, `layer` (any GeoJSON), `prop` (a 3D model from the Kenney pieces in `mapgeo/props/`: castle, tower, trebuchet, ship, tree and others), `mark`. An element enters on its first mention (0.35 s), later mentions update it, and it leaves on `gone` (0.3 s). Every word on the map is HTML text, so it is exact. The full writing rules (zoom by what stands on the map, one camera direction per beat, paint only what the narration claims, a sea route with ships riding it, labels above standees, a cutaway every 2-3 map beats) are in `agent/v2/stages/direction.md` §4-§5, `choreo.md` and `MOVES.md`.

### 6.7 The cast cut-outs (`agent/v2/tools/scene_kit.py`, `dehalo.py`)

`ensureFilmKit()` in `shots.mjs` writes `direction/kit_film/jobs.json` (`{style, look, cast}`; style = the dark look's art sentence, else `scene_style`, else "painted storybook, muted colours") and runs `.venv/bin/python agent/v2/tools/scene_kit.py <kit_film>` under a lock (one generator at a time). It runs on every build and skips pictures that exist. For each cast piece:

- The prompt: a painted chibi standee matching the first image (big round head, small body, soft painted shading, clean thick outline), full body, feet at the bottom edge, centred on plain white, no ground shadow, no text; plus "the second image is this same character drawn earlier" when the piece has `ref`; plus `Era and palette: <style>.`; plus the piece's own prompt. With the dark look, the chibi wording becomes "painted in exactly this style: <art>".
- Pictures attached: the first finished piece as the style reference, and the `ref` piece as the identity reference.
- The call: fal `fal-ai/nano-banana-2`, Nano Banana 2 as in the batches (or `/edit` with pictures), `aspect_ratio` = the piece's `aspect` (default 3:4), `resolution: "1K"`, PNG. `NANO_BANANA_VIA=vertex` sends it to Vertex instead (`gemini-3.1-flash-image`).
- The matte: rembg's `remove()` with its default model, bria-rmbg (BRIA RMBG-2.0, non-commercial licence; rembg 2.0.81 downloads it on first use into `~/.rembg`, or `REMBG_HOME`), then `dehalo()` strips the 3 px fringe and any white rim.
- Retries: a cut-out touching the top, left or right edge is asked once more with a margin sentence; a refused picture is asked again with violent words softened, up to twice; a 401, 403 or PERMISSION_DENIED fails at once (a run once slept 17 minutes on 403s); other errors wait 8-45 s; 6 attempts at most. One picture call at a time on the machine (lock files in `~/hyprframes-runs/gemini-slot-0.lock`), with a 4 s pause after each. A piece still missing stops the build with "kit failed, no picture for: …".

`scene_kit.py` also has modes for scene keyframes (Vertex Gemini, Qwen layered images on fal, `LAYERS_URL`) that map shots never use.

### 6.8 Map data (`agent/v2/tools/data/`, in git)

| Path | What | Used by |
|---|---|---|
| `mapgeo/geo.json` (33 MB) | the gazetteer: 17,123 names, each with a centre and a box (278 countries, 3,023 regions, 279 seas, 6,302 cities, "City, Country" forms and a few aliases), plus the world's land as triangulated slabs | every build, the engine, `sea_route.py`, `territory_sheet.py` |
| `mapgeo/geo/countries/`, `regions/`, `seas/` (3,574 files) and `geo/ocean.json` | one outline per feature (Natural Earth 10 m) and the vector ocean | the engine, relief, territory sheets |
| `mapgeo/bm.jpg`, `bm_merc.jpg` | NASA Blue Marble, plain and Mercator ±84° | satellite style |
| `mapgeo/shade.jpg` | Natural Earth shaded relief | the dark look |
| `mapgeo/felt/`, `paper/`, `Plaster001/` | 1K textures | toy and paper styles (`Plastic010/` is also there, unused) |
| `mapgeo/props/castle/`, `nature/`, `pirate/` | Kenney GLB models | toy props |
| `ne10.geojson` (13 MB) | Natural Earth 10 m countries | `map_prep.py`, `map_data.mjs` |
| `fetch/` | cached downloads | `map_data.mjs` |

A bare city name means the biggest city of that name; "Brest, France" picks one; common English names are aliased to Natural Earth's. While choreographing, the stages may fetch data with `node agent/v2/tools/map_data.mjs`: any Natural Earth 10 m layer (`ne`), a World Bank indicator by country (`worldbank`), Wikidata points (`wikidata`), the world's borders in a given year from the historical-basemaps project (`historical`). Upkeep scripts never run by a film: `map_prep.py` rebuilds `geo.json` and the outlines; `map_basemap.py` rebuilds the Blue Marble pictures.

### 6.9 How map clips reach the film

- The launcher waits for `maps/done.json` or `maps/failed.json` after the planner (3.7), with no time limit. If the job's process ends without writing either, the launcher writes `failed.json` itself. `failed.json` means nothing renders and the film fails; there is no fallback to H3-painted maps.
- The stop hook skips files under `maps/` when it checks that every file `render.json` names exists.
- render-all refuses the run on `maps/failed.json` or a missing `code` mp4. A map clip is conformed like any code clip: fitted inside the frame (never stretched), the first H3 clip's frame rate, last frame held to `seconds`, no sound.
- The film takes the map clip's size (1920x1080 or 1080x1920), and the join scales every other clip to it with a plain `scale=w:h`: H3 clips are distorted by about 2.5% across (832x480 stretched to 1920x1080; 480x832 squeezed into 1080x1920). Frames other than 16:9 and 9:16 get 16:9 map clips, and the join would stretch the other clips to 1920x1080 (from the code; no test film covers it).
- The map job's time adds to the film's: render-all starts only after it, so the H3 cutaways wait too (6.11 has a measured run).

### 6.10 Settings

| Variable | Default | Effect |
|---|---|---|
| `MAPS` | set to 1 by the launcher for painted films | registers `map_shots`; `make_soundtrack` writes `soundtrack/soundtrack.json` |
| `MAPS_CARD` | the brief's card id | the engine look for `satellite-map` and `dark-documentary`; the tool text |
| `MAPS_MODEL`, `MAPS_EFFORT`, `MAPS_FAST` | `claude-sonnet-5-5`, `medium`, `0` | the two stage sessions |
| `CLAUDE_BIN` | the first `claude` on PATH | the Claude Code CLI the stage sessions run (the SDK's bundled 2.1.235 refuses Opus 5.5) |
| `CHOREO_ONE` | on | `0`: one choreography session per section |
| `CHOREO_EXAMPLES` | only the copied film | `all`: paste the Black Death and Joan plans |
| `CHOREO_NOTE` | none | notes the choreographer fixes first |
| `LOOK`, `LOOK_JSON`, `MAP_STYLE` | none | force a `looks.json` look (`none` drops it), override its map colours, force toy, paper or satellite (tests only: the job hands its whole environment to the stages, so these in `.env.local` would change every map film) |
| `NANO_BANANA_VIA` | fal | `vertex` sends cast pictures to Vertex (needs `GOOGLE_VERTEX_PROJECT`; Vertex refused every call from 10-09 on) |
| `PRODUCER_PLAYER_READY_TIMEOUT_MS` | 180000 (set by the job) | how long HyperFrames waits for a map page to load |
| `ELEVENLABS_API_KEY`, `FAL_KEY` | required | forced alignment; cast pictures |

### 6.11 Time and cost record

| Run | Map job | AI cost of the stages | Notes |
|---|---|---|---|
| `nm-x10`, 10-12, made from this repo (its run folder is not in git or `batches/`) | 13.4 min: direction 140 s, choreography 10.6 min, the final render of both sections 25 s | $1.16 (direction $0.38, 5 turns; choreography $0.78, 18 turns) | 16:9, 30 s, two map sections and one H3 cutaway; planning 4.5 min, and the map job ended 11.3 min after the planner did; parchment card, paper picked (the planner's own pick, since taken out); not rated |
| `v50-x10`, 10-11 night | 6.5 min | $0.57 | paper on the parchment card; toy was judged better |
| `v48-x10`, 10-11 | 6.3 min | $0.58 | the first take with one choreography session |
| `v41-x10`, 10-11 | 9.7 min | $1.76 | one choreography session per section (three sections); rated 7 |

The dollars are each session's own total at list price. `nm-x10`'s read somewhat high: CLI 2.1.285 logs the Haiku 5.5 helper calls at Opus prices, and only that run set Haiku 5.5 as the helper model. Not counted anywhere: the cast pictures (one Nano Banana call per cast piece, plus retries) and the forced alignment calls. Two Hannibal takes failed in the map stages (one choreography session exited with an error; one had a missing cast picture at the final render, before the fail-fast fix).

### 6.12 Shots drawn in code: `code_clip` (`research/h3/tools-codeshot.mjs`)

Registered in every film (`registerCodeShotTools(server, {maps: CODE_SHOTS === "1"})`); the file's header comment and the launcher's still say `CODE_SHOTS=1` adds it. Only its own description points a planner to it. It says: use it only for what H3 cannot paint, a simulation whose outcome is the point (an evolution run, a physics experiment, an algorithm on real data) or a chart of real numbers; a map is never a code clip; explanations of how something works are H3's; most films have none; look the facts up first and write them into the code as data. It names the search tools by older names (`search_web`, `read_url_content`); the planner has WebSearch and WebFetch. In this repo's runs it was called in four films: the bouncing-ball short and three takes of a remake whose request asked for a promo end card (planners built an animated end card with exact text).

Inputs: `name`, `seconds` (1-30; span + 0.3), `html` (one self-contained page), `stills` (up to 8 times to save as PNG). The page contract, given to the planner as a skeleton: a root `div` with `data-composition-id="main"`, `data-start="0"`, `data-duration`, `data-width`, `data-height`; one paused GSAP timeline; `window.__timelines = {main: tl}`. Every pixel is a function of the timeline's time: computed motion tweens a plain object and redraws the whole frame from its value. Never `Date.now`, `performance.now`, `requestAnimationFrame`, timers, `Math.random` (use `d3.randomLcg(42)`), CSS animations or the network (type may come from Google Fonts with one `<link>`). Labels at least 1/25 of the frame tall; the style card's ground, inks and type; no title card, caption or logo.

Local libraries, built once into `research/h3/codeshot/node_modules/.lib/` and copied into each shot as `lib/` (locked by `research/h3/codeshot/package-lock.json`): GSAP 3.15.0 with MotionPathPlugin, DrawSVGPlugin and SplitText; d3 7.9.0; topojson-client 3.1.0; three.js 0.186.1; world-atlas 2.0.2 as scripts that fill `window.WORLD`.

What it does: refuses a page without `data-composition-id=` or `__timelines`; writes `<run>/code/<name>/` (`index.html` with its size and duration overwritten, `lib/`, `hyperframes.json`, `package.json`); loads the page in Playwright's Chromium, collects script errors, console errors and failed requests, and seeks the timeline to 0, 25%, 50%, 75%, 100%, 50% and 0 (any error comes back as "not rendered, fix and call again"); renders with `npx --yes hyperframes@0.8.2 render . --fps 24 --quality standard --output <name>.mp4`; returns the mp4, the folder, a contact sheet (8 frames, shown to the planner), the size, the frame times, the PNG stills, a warning if the timeline runs longer than `seconds`, and, when the page set `window.__sounds = [{t, note: "E5" | freq, dur, gain}]`, `<name>-sounds.wav`: plucked tones at those times, which the planner may use as `render.json` `music` when the film is that clip. Its text allows at most 3 calls per shot; nothing counts them.

Size: two-thirds of the film's full frame, at 24 fps: 1280x720 (16:9), 720x1280 (9:16), 720x720 (1:1), 720x900 (4:5), 720x960 (3:4), 960x720 (4:3), 1680x720 (21:9). Two ways to use it: a clip that plays as it is (`{"id", "code": "<mp4>", "seconds", "span"}`), or the reference video of an H3 clip whose prompt says to keep every position, path, count and timing and paint it in the film's style. A film made only of code clips comes out at H3's size, the code clip fitted inside with thin bars.

`map_clip` and `map_stills` (an older way to put the map engine in the planner's hands) register only with `CODE_SHOTS=1`, which crashes the tool server (11.3). `map_shots` replaced them.

### 6.13 The still maker (`agent/h3film/still.mjs`) and the `still` tool

Words on screen must come from stills or code: H3 garbles words it animates or makes up. The `still` tool draws exact type, end cards and placed pictures in HTML and hands H3 the PNG. The room behind them is painted by CSS identically in every still of a film (a glow described in words flickered from clip to clip; a painted one holds).

Fields: `name`; `kind` = `text` | `surface` | `screen` | `lockup` | `blank`; `room` = `glow` (default) | `studio` | `spot` | `paper` | `gradient` | `vignette` | `flat` | `none`, with `ground` and `light` colours. For text: `text`, `em` (size as a fraction of the frame's height, its width in a tall frame; default 0.09, up to 0.5), `ink`, `font` (`serif` Instrument Serif, `sans` Geist, `mono` the machine's own monospace font, `condensed` Anton), `italic`, `weight`, `caps`, `track`, `lead`, `wrap`, `place` (`centre`, `left`, `top-left`, `bottom`, `bottom-left`), `bg` (a picture under the words). For surface: `image`, `width` (default 0.7; with `room: "none"` the picture fills the frame's width with no shadow). For lockup (the end card): `product` (required), `mark`, `wordmark`, `line`, `url` (only an address the brief gives or the screenshot tool opened), `bg`, `ink`, and `design` (the planner's own end card as HTML on a page 1920 px on its long side: any Google Fonts family, the logo as `<img src="LOGO">`, no other picture, no `<svg>`, no `url()`, the main line at least 120 px). For screen: `film`, `screen`, `css`, `head`. It refuses the user's own attached files as a surface or background (they are redrawn with `storyboard`). Output `<run>/stills/<name>.png` plus a small `.view.jpg`.

Lockup rules: only a logo the `screenshot` tool captured (`<run>/shots/`), one in `agent/refs/`, or one the user attached is used (a planner once drew its own fake wordmark), and a captured `shots/logo.png` is used whatever mark is passed, unless the user attached a logo; a captured logo that does not read on the ground is recoloured if it is one colour, else the site's app icon is used with the name typed; SVG fills that nearly vanish on the ground (contrast under 1.6) are reversed; a light room gets dark type. Without `design`, the layout is Orchids' end card (`ingest/orchids/compositions/screens/endcard.html`: mark and name on one row, a call-to-action pill, the domain); a tall frame stacks them.

How a still is made: a one-frame HyperFrames page in a temporary folder, on a canvas of about 9.1 megapixels in the film's ratio (16:9 4032x2268, 9:16 2268x4032, 1:1 3024x3024, 4:5 2704x3380, 3:4 2616x3488, 4:3 3488x2616, 21:9 4620x1980), Tailwind's browser build 4.2.4 and GSAP 3.14.2 from jsdelivr, Geist, Instrument Serif and Anton from Google Fonts; `npx --yes hyperframes@0.8.2 render . -c still.html --workers 1 --quality draft --output vf.mp4`; ffmpeg takes the frame at 0.5 s. Text too wide is shrunk to fit 84% of the width; in a tall or square frame long lines wrap. A failed render is tried once more, then the tool writes `FAILED.json` (no film is made without its still). At most 4 stills render at once; stills sharing one workspace (screens, lockups) go one at a time. `kind=screen` works only with `film: "orchids"` (the other films in its list have no screens in this repo), and the one screen there is the end card. In this repo's runs planners used `text` (43 calls), `lockup` (25), `surface` (1) and `blank` (1), never `screen`.

`agent/h3film/still.mjs` also runs alone: `node agent/h3film/still.mjs /tmp/t.png text "Exact words" 0.1` (16:9 unless `RATIO` is set).

### 6.14 HyperFrames, Chrome and Playwright versions

| What renders | Tool | Browser |
|---|---|---|
| map section previews and final map shots | HyperFrames 0.8.20 via `npx --yes hyperframes@0.8.20` | the chrome-headless-shell that version pins (152.0.7977.30) |
| stills and code clips | HyperFrames 0.8.2 via `npx --yes hyperframes@0.8.2` | the chrome-headless-shell that version pins (152.0.7928.2) |
| `code_clip`'s page check, the `screenshot` tool | Playwright 1.61.1 (root `package.json`, locked) | Playwright's Chromium, installed by `npm run setup` |

HyperFrames' `render` uses the exact headless shell its version pins, from `~/.cache/hyperframes/chrome/`, downloading it on first use (`HYPERFRAMES_BROWSER_PATH` or `PRODUCER_HEADLESS_SHELL_PATH` points it at another binary). HyperFrames' own dependencies are resolved by `npx` and not locked. Why two versions: the map pages were proven on 0.8.20, which also fixed video capture; stills and code clips stayed on 0.8.2. Moving either is untested. To pin everything for a server, install both versions into a local `node_modules` with a lock file and pre-download both headless shells. Map pages use WebGL (three.js with ambient occlusion and depth of field); every measured render ran on a Mac with a GPU, and speed and output on a server without one are untested.

## 7. Setup and running

### 7.1 Quick start

1. Do the setup in 7.2, keys included.
2. Make a film:

   ```sh
   ./film "explain how a touchscreen knows where you tapped" --aspect 9:16 --duration 30 --name touch
   ```

3. The film lands in `agent/runs/h3film-touch/final-gpu.mp4`; the last line printed says where. The producer's brief and log are `agent/runs/_auto/touch.txt` and `agent/runs/_auto/touch.log`.

Files go after the request: `./film "lyric video for this song, neon city look" song.mp3`. Every option is in 2.2.

### 7.2 Setup

These steps made a film from a fresh checkout on macOS on 10-12. The scripts were written to run on Linux too, but no film has been made on Linux yet (7.5).

**Accounts.** Keep automatic top-up on for every paid account: an account error (out of credit, a bad key) stops the film.

| Service | What it does in a film | Setting |
|---|---|---|
| Anthropic (Claude) | the producer, the planner and the map stages, all run by Claude Code | `ANTHROPIC_API_KEY`, or the `claude` CLI logged in |
| fal | Nano Banana 2.1 stills and edits (`fal-ai/nano-banana-2.1`, and `/edit` when references are attached), the swapped first frame; map cast cut-outs on Nano Banana 2 (`fal-ai/nano-banana-2`) | `FAL_KEY` |
| ElevenLabs | speech to text (`scribe_v2`), music (`music_v2_5`), sound effects, word timing for map shots (forced alignment), voices in the languages Magic Hour's voices cannot speak, the cloner's fallback | `ELEVENLABS_API_KEY` |
| Magic Hour API | the film's voices: preset voices and the voice cloner | `MAGIC_HOUR_API_KEY` |
| Modal | H3 renders on Blackwell GPUs (app `h3-render`) | `~/.modal.toml`, or `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` |
| Google Vertex | nothing by default; the picture client is built for Vertex and will not start without a project name | `GOOGLE_VERTEX_PROJECT` (any non-empty value) |

**Tools on PATH:**

- node 22 or newer (tested on 26), with npm and npx.
- Claude Code 2.1.285 exactly, as `claude` on PATH (`npm i -g @anthropic-ai/claude-code@2.1.285`), logged in or with `ANTHROPIC_API_KEY` in the environment or `.env.local`. Every test film ran on it; keep it (the server image installs it, 7.7). `CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH` works on it, and the map stages need 2.1.280 or later (the Agent SDK's bundled CLI, 2.1.235, refuses Opus 5.5, so the stages start the `claude` on PATH or `CLAUDE_BIN`).
- ffmpeg and ffprobe (tested on 9), with libx264, libmp3lame and the AAC encoder, and the filters `zoompan`, `tpad`, `loudnorm`, `ebur128`, `alimiter`, `amix`, `adelay`, `afade`, `apad`, `atrim`, `select`, `overlay`, `fade`.
- yt-dlp (tested on 2026.08.19), with a JavaScript runtime such as deno: yt-dlp needs one for YouTube.
- zsh at `/bin/zsh`, and perl.
- Python 3.14 for the `.venv`; any `python3` for the small standard-library scripts the launcher calls by name (`manifest.py`, `lyric-ids.py`, `lyric-retime.py`, `reading-report.py`).
- git (`manifest.py` records the commit and the uncommitted diff), `nice`, `pgrep`, `nohup` (`run-v3.sh`). `caffeinate` is used only where it exists (macOS).

**Steps:**

1. `npm run setup`. It installs the locked packages (`npm ci`) of the repo root (Playwright 1.61.1), `research/h3`, `research/h3/codeshot` and `agent`, then Playwright's Chromium.
2. `python3.14 -m venv .venv && .venv/bin/pip install -r requirements.txt`. 90 pinned packages, the Modal CLI among them; about 75 s on Python 3.14.7. allin1 and torch are left out on purpose (song analysis always runs madmom with `ALLIN1=0`; torch runs only inside the Modal image); madmom installs from a fixed git commit. The code calls `.venv/bin/python` by path, so the venv must be at `<repo>/.venv`.
3. `cp .env.example .env.local` and fill in the keys (7.3). `.env.example` lists every setting with its default and what it does.
4. A Modal token: `.venv/bin/modal token new` writes `~/.modal.toml`, or set `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` in `.env.local`. The token's account needs the app `h3-render`. On a new Modal account, deploy it once:
   - in `research/h3/modal_h3.py`, remove `diffusion_models/minimax_h3_ref2va_bf16.safetensors` from `WEIGHTS` (an unused 66 GB full-precision model);
   - `.venv/bin/modal run research/h3/modal_h3.py::download` puts the other weights, 42.5 GB, in the volume `h3-weights` (the first run also builds the image);
   - `.venv/bin/modal deploy research/h3/modal_h3.py` deploys the app `h3-render`.
5. Give yt-dlp a signed-in account (below).
6. Free check: `node agent/h3film/auto.mjs --catalogue` prints every style with its section, score and planner mode (it needs `.env.local` to exist and makes no API call).

These download on first use, with no step of their own: HyperFrames 0.8.2 and 0.8.20 (through npx) and the Chrome they render with (`npx --yes hyperframes@0.8.2 browser ensure` and the same with `0.8.20` fetch them ahead of time), and rembg's model (bria-rmbg, about 1 GB, into `~/.rembg/models/`) on the first cut-out (`.venv/bin/python -c "from rembg import new_session; new_session('bria-rmbg')"` fetches it ahead).

Rendering needs the internet, not only for the APIs: map shots, type stills and code clips load their scripts (three.js, GSAP, Tailwind) from cdn.jsdelivr.net, and type stills and map pages load their fonts from Google Fonts. A film reaches `api.anthropic.com`, fal's API and storage, `api.elevenlabs.io`, `api.magichour.ai`, Modal's API, YouTube, TikTok, X and Instagram (yt-dlp), `lrclib.net`, `itunes.apple.com`, any site the producer and planner open (WebFetch, `reference_image`: official character pictures, Wikimedia), `cdn.jsdelivr.net`, `fonts.googleapis.com` and `fonts.gstatic.com`, `copernicus-dem-90m.s3.amazonaws.com` (map elevation tiles) and `registry.npmjs.org` (npx).

**yt-dlp and YouTube.** `fetch.mjs`, `kit.mjs` and the planner's `user_video` and `web_clip` tools use yt-dlp. YouTube blocks downloads from servers with a bot check. Only `fetch.mjs get` detects it: `auto.mjs` then stops the film and says so (exit 1); downloads through `kit.mjs`, `user_video` and `web_clip` just fail. Give yt-dlp a signed-in account in `~/.config/yt-dlp/config`: `--cookies-from-browser <browser>[:<profile>]`, or on a server `--cookies <file>` with cookies exported from a signed-in browser. The code passes no cookie flags itself. Keep yt-dlp updated. Fan edits, sports edits, movie recaps, memes, lyric videos (the song and its timed lyrics), every request with a link, and formats the producer looks up on YouTube depend on it.

**Fonts.** Captions and titles (`join.mjs`) use the macOS fonts where they exist and Inter (`assets/fonts/`, SIL Open Font License) elsewhere; non-Latin captions need more (4.13). Frame sheets (`kit.mjs`) use Helvetica on macOS, else Inter Regular. `agent/v2/tools/territory_sheet.py` (line 22) uses Helvetica on macOS, else Pillow's plain font (sheets only, not the film).

**Claude Code on a server** (recommendations, not in the code): give the user that runs films a clean Claude Code home (no `~/.claude/CLAUDE.md`, and no hooks, plugins, MCP servers or `env` in `~/.claude/settings.json`: user-level settings still reach the producer and planner sessions; only the map stages load no settings at all); install a fixed Claude Code version and set `DISABLE_AUTOUPDATER=1`, so a batch never changes CLI version halfway; run films as a normal user (some Claude Code versions refuse `--dangerously-skip-permissions` as root).

**Disk.** A finished film's run folder is 14 to 563 MB (median 37 MB; edits of long footage are the largest). Caches grow and nothing prunes them or checks free space: `agent/runs/_auto/files/` (fetched footage and songs, 1.6 GB after this repo's tests), `agent/runs/_style-builds/kits/` (0.6 GB), `agent/artcache/` (0.34 GB), `agent/v2/tools/data/dem/` and `relief/` (map elevation, 4.2 GB in the lab), `~/.cache/hyperframes/` (about 0.5 GB), `~/.rembg/models/` (1 GB).

**Large files in git.** They are needed: 3,631 files, 129.4 MB in all. Keep them with the repo.

- Map outlines in `agent/v2/tools/data/mapgeo/geo/` (3,575 files, 72.7 MB) and the satellite pictures `bm.jpg` and `bm_merc.jpg` beside them (6.2 MB). Without them map shots break.
- `clip.mp4` in `agent/web/app/styles/refs/` for `flat-pop`, `holographic`, `kinetic-wordmark` and `line-draw-on` (10.9 MB). Each is sent to H3 as that style's video.
- Launch motion clips: the clips in `agent/h3film/library/proven/` (22 files, 22.2 MB: 21 `ref.mp4` and `read-down-a-long-table/07-new-beat.mp4`) and `ingest/blossom/reference.mp4` (15.7 MB). Also two Magic Hour clips in `agent/refs/`.
- Six example runs in `agent/runs/` (their `PLAN.md` and clip prompts): `h3film-t-breathe`, `h3film-breathe-now`, `h3film-style-hand-drawn`, `h3film-t-logo`, `h3film-t-event`, `h3film-style-stickman-cartoon`. They are pasted as example films for tutorials, event promos, logo animations and lyric videos. The launcher stops if one is missing.

Not in git: `.env.local`; the installs (`node_modules/` in four folders, `.venv/`, Playwright's Chromium, `~/.cache/hyperframes/`, `~/.npm/_npx/`, `~/.rembg/models/`, the Modal volume and image); every run folder except the six above, `agent/runs/_auto/`, `agent/runs/_style-builds/`, `agent/artcache/`, the map caches; looks studied by test films (new cards and their `refs/<id>/pool/`); the page builders' `out/` folders; the uploads the test requests name (8.3). The test films themselves, with their records, are in `batches/` (8.4).

### 7.3 Settings: `.env.local`

`cp .env.example .env.local` and fill in the keys. `.env.example` lists every setting with its default; a line `# NAME=` is a setting left at its default. Never commit `.env.local`.

Who reads it, and how:

| Reader | How | When the environment already has the variable |
|---|---|---|
| `film`, `agent/h3film/run-v3.sh`, `agent/h3-film-agy.sh` | `set -a; . .env.local` (every name exported) | `.env.local` wins |
| `agent/h3film/auto.mjs`, `fetch.mjs` | lines `NAME=value`, an optional `export`, one pair of quotes stripped | the environment wins, even with an empty value |
| `agent/h3film/render-all.mjs` | the same, but only after the clips are rendered (for speech captions); load it in the shell first when running render-all by hand | the same |
| `agent/h3film/maps.mjs` | as `auto.mjs` | the environment wins unless its value is empty |
| `research/h3/mcp.mjs` (the tool server), `agent/v2/run.mjs` | only lines `NAME=value` whose name is capitals and underscores with no digits, no `export` (`run.mjs` keeps quotes) | the environment wins unless its value is empty |

So write one `NAME=value` per line, with no `export`, no spaces around `=` and no quotes; the shell scripts source the file, so a value must also be valid shell. The tool server reads its keys from `.env.local` itself but skips names with digits (every `H3_*` setting); those reach it through `mcp.json`, which carries the names listed in 3.5 from the launcher's environment (the launcher sources `.env.local`).

**Keys:**

| Name | Needed | What for |
|---|---|---|
| `ELEVENLABS_API_KEY` | yes | speech to text, music, sound effects, word timing for map shots, speech captions; voices in languages Magic Hour's voices cannot speak (Hindi, Japanese and others), and every voice when `VOICE_PROVIDER=elevenlabs` |
| `FAL_KEY` | yes | Nano Banana stills and edits, map cut-outs, swapped first frames |
| `MAGIC_HOUR_API_KEY` | yes | the film's voices: preset voices and the voice cloner |
| `GOOGLE_VERTEX_PROJECT` | yes, any non-empty value | the picture client will not start without it, though every call goes to fal |
| `GOOGLE_VERTEX_LOCATION` | no (default `global`) | the same client |
| `ANTHROPIC_API_KEY` | unless the `claude` CLI is logged in | producer, planner, map stages |
| `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` | unless `~/.modal.toml` exists | the H3 render |
| `MINIMAX_API_KEY` | no | only `generate_video` with `H3_BACKEND=direct`; never used by `./film` |
| `LAYERS_URL` | no | a picture-layering server for the map engine's scene shots, which films never use |

**Run settings:**

| Name | Default | What it does |
|---|---|---|
| `H3_BUDGET_USD` | 20 with `./film` and `run-v3.sh` (render-all's own default is 5) | the render refuses a film whose clips would cost more than this, priced as on fal, even on Modal (5.2 step 7). At 5, longer films are refused. The planner always gets 0 |
| `CLAUDE_BIN` | the `claude` on PATH | the Claude CLI of the producer and the map stages (the planner always runs the `claude` on PATH) |
| `CMODEL`, `CEFFORT` | `claude-sonnet-5-5`; effort by kind (1.3) | the planner's model and effort |
| `PRODUCER_MODEL`, `PRODUCER_EFFORT` | `claude-sonnet-5-5`, `medium` | the producer |
| `MAPS_MODEL`, `MAPS_EFFORT` | `claude-sonnet-5-5`, `medium` | the map stages |
| `CLAUDE_MODEL` | `claude-haiku-5-5` | the default model of `claude.mjs`; its callers, the producer and the swap question, name their own, so nothing uses it today |
| `GPU_ROWS` | empty (480; 704 for the `2-5d-hybrid` card) | 704 renders the 720p tier (1248x704), 800 the 1080p tier (1408x800) |
| `VOICE_PROVIDER` | `magichour` | `elevenlabs` for ElevenLabs narration |
| `ELEVENLABS_VOICE_ID` | the house narrator | only when no `voice` is passed, which the tool never does |
| `NANO_BANANA_MODEL` | `gemini-nano-banana-2.1`, on fal | the still model (`gemini-3.1-flash-image` is Nano Banana 2, fal `fal-ai/nano-banana-2`) |
| `ELEVENLABS_TTS_MODEL`, `ELEVENLABS_MUSIC_MODEL`, `ELEVENLABS_STT_MODEL` | `eleven_v4`, `music_v2_5`, `scribe_v2` | ElevenLabs models |
| `H3_SEED` | a new random seed for every render | one fixed seed for every clip that names none (A/B tests) |

**For `agent/h3film/run-v3.sh` only:** `TSV` (the run sheet; default `agent/h3film/random-inputs-v2.tsv`), `RUNPFX` (prefix of the run names, default `v3`), `MAXRUN` (films running at once, default no limit), `NICE` (nice level, default 0), `STAGGER` (seconds between starts, default 2).

**Switched off, kept in the code: leave unset.** The defaults made the current films; each of these was measured or may come back.

| Name | Read by | Set to | Effect |
|---|---|---|---|
| `DURATION` | `auto.mjs` | `1` | the producer reads a length from the request's words |
| `PRODUCER_STATIC_FIRST` | `auto.mjs` | `1` | the producer's fixed rules go first as a system prompt |
| `PRODUCER_LEAN` | `auto.mjs` | `0` | the producer gets the account's connectors again |
| `HIDE_STYLES` | `auto.mjs` | `a,b` | those styles are left out of the list |
| `LAUNCH_INDEX` | launcher | `0` | launch planners read the full `CASTABLE.md` |
| `LAUNCH_EXAMPLES` | launcher | `all` / `card` | launch films paste every example film / only the card's own (default: Magic Hour v13 and the card's own) |
| `LAUNCH`, `MINIMAL`, `SKILL`, `EXAMPLES` | launcher (`auto.mjs` sets them) | | the planner path, the skill file, the example films (1.3, 2.12) |
| `INLINE` | launcher | `0` | a launch film with no card gets no reading list pasted |
| `PINLINE` | launcher | `0` | painted films stop getting their files pasted |
| `PLANNER_CHECK_HOOK` | launcher, `planner-check.mjs` | `0` | no check of each launch clip prompt as written |
| `PLANNER_STOP` | launcher, `planner-stop.mjs` | `0` | no hook ending the session once the film is whole |
| `EDIT_LIST` | launcher, `tools-footage.mjs`, `build-edit.mjs` | `0` | montages write each clip prompt instead of one `EDIT.json` |
| `H3_ACCURACY` | `mcp.mjs` | `ground` | Nano Banana's own search grounding instead of fetching a real picture (does nothing on fal) |
| `H3_BACKEND` | `mcp.mjs` | `direct` | `generate_video` renders on MiniMax's own API |
| `NANO_BANANA_VIA` | `tools-film.mjs`, `scene_kit.py`, render-all | `vertex` | Nano Banana through Vertex (it refused every request on 10-09) |
| `STORYBOARD_INLINE`, `FOOTAGE_COMPACT` | `tools-film.mjs`, `tools-footage.mjs` | `0` | older tool result formats |
| `SOUNDTRACK_REUSE` | `soundtrack.mjs` | `1` | mix again from what was already made |
| `H3_NOCAP` | `h3.mjs` | `1` | no warning for prompts over 7,000 characters (`generate_video` only) |
| `ZOOM_STEP`, `NOVID`, `EDIT_TRIM`, `H3_AUDIO_MODE`, `H3_FOOTAGE_MODE` | render-all | | 5.10 |
| `MAPS_FAST`, `CHOREO_ONE`, `CHOREO_EXAMPLES`, `CHOREO_NOTE`, `LOOK`, `MAP_STYLE` | map stages | | 6.10 |
| `KIT_FIT` | `kit.mjs` | `0` | frame sheets in fixed cells |
| `CLAUDE_KEEP` | `claude.mjs` | `1` | keep the producer's session on disk |
| `RESUME` | nothing | | listed in `.env.example` and recorded by `manifest.py`; no code reads it |

**Read by the code but not in `.env.example`:** `H3_SWAP` (auto.mjs; `1` the swap path, `0` the batch path, unset asks, 1.3), `SWAP_PIN` (render-all; `0` turns off the swapped first frame), `TAGS` (render-all; `swap`, `all` or `0`), `R2V` (render-all, `comfy_r2v.py`; `v2`, `v2-shipped`, `v2-sage` stop the render), `PLANNER` (`claude`; anything else stops the launcher), `ANTHROPIC_DEFAULT_HAIKU_MODEL` (Claude Code's helper model; the code leaves it unset, so 2.1.285 uses Haiku 4.5, as every test film did), `MODEL` (`agent/v2/run.mjs`; set by `maps.mjs` from `MAPS_MODEL`).

**Set by the code; never set these in `.env.local`:** `H3_OUT`, `H3_FOOTAGE`, `H3_PAINTED`, `H3_REFS`, `H3_CALL_LIMIT_S`, `H3_CHECK_HOOK`, `MAPS`, `MAPS_CARD`, `CODE_SHOTS`, `REPO`, `CARD`, `UC`, `PAINTED` (the launcher); `H3_DURATION` and `RATIO` (`auto.mjs`, from `--duration` and `--aspect`); `H3_RUN_NAME` (`auto.mjs`, for the cost log); `V2_OUT`, `V2_FILM`, `VOX_OUT`, `RUNS_DIR`, `H3_MAPS`, `H3_RUN`, `FORK`, `EFFORT`, `FAST`, `MAP_NO_PREVIEW`, `PRODUCER_PLAYER_READY_TIMEOUT_MS` (`maps.mjs`); `ALLIN1=0`. `.env.example`'s list also names `AGY_CLI_DISABLE_AUTO_UPDATE` and `V2_SLUG`, which no code here sets.

**Claude Code settings the code puts on each `claude` command, which must stay as they are:** `CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH=12288` (planner; otherwise tool descriptions are cut at 2,048 characters and planners lose the footage and product-still rules), `CLAUDE_CODE_PROMPT_CACHE_TTL=5m` and `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1` (producer and planner; billing only), `MCP_TOOL_TIMEOUT=1800000` with `H3_CALL_LIMIT_S=1750` (planner), `CLAUDE_CODE_WEB_SEARCH_FAST_ARG=0` (producer; whether newer Claude Code versions still read it is unconfirmed), and for the map stages `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, `BASH_DEFAULT_TIMEOUT_MS=900000`, `BASH_MAX_TIMEOUT_MS=1800000`.

Start films through `./film`. Started on its own, `agent/h3-film-agy.sh` gives the planner `skills/h3-film/SKILL.md` unless `SKILL` is set; that skill has a launch film's planner render every clip itself with `generate_video` on fal (charged to the launcher's third argument, $5 by default) and join them with `join_film`. `./film` gives every planner `skills/h3-film/SKILL-gemini.md`, which forbids both.

### 7.4 Making a film

The command and every option: 2.2. What the user can attach after the request: a song (`.mp3 .wav .m4a .aac .flac .ogg`, with an optional `.vtt` of timed lyrics), pictures and logos (`.svg .png .jpg .jpeg .webp .gif`), videos (`.mp4 .mov .webm .m4v`; the producer studies each like a link and decides whether it is footage to edit, a video to follow, a look to take, or several), and any other file as a plain reference. Pictures and sound files are copied into `<run>/attached/`; videos stay where they are. A path that does not exist stops the run.

What it prints, where the logs go and the exit codes: 2.2. The run folder: 1.4. A good result (8.6): the last line is `h3film-<name>: done, …/final-gpu.mp4` and the exit code is 0.

**Rendering a planned film by hand** (after `--plan`, or to re-render): `auto.mjs` does three things around render-all that a hand render must repeat.

```sh
set -a; . ./.env.local; set +a          # render-all reads .env.local only after the clips are made
# lyric films only: when the run has lyrics.json and soundtrack/song.json and its prompts use [Ln] ids
python3 agent/h3film/lyric-retime.py agent/runs/h3film-<name> 0
GPU_ROWS= H3_BUDGET_USD=20 \
  H3_DURATION=<seconds, only for a film made with --duration> \
  node agent/h3film/render-all.mjs agent/runs/h3film-<name>
```

Use `GPU_ROWS=704` for the `2-5d-hybrid` card, and keep `GPU_ROWS=` (empty) otherwise so the clips of a `./film` run are reused (5.1). A rerun reuses every clip whose inputs are unchanged (5.2 step 9). A changed clip renders again with a new random seed, and the old one is kept as `<clip>.mp4.stale-<time>`: any edit to a clip's prompt re-rolls that whole clip, so copy the run folder before re-rendering part of a film you want to keep. `H3_BUDGET_USD=0` makes render-all refuse every H3 clip before any GPU call (but a live-action swap clip asks Nano Banana for its swapped first frame before that check).

### 7.5 Before it runs on another machine

The lab ran on one Mac. The paths tied to that Mac are gone from the code, and the scripts run on macOS and Linux. These spots remain:

- The shell scripts (`film`, `agent/h3-film-agy.sh`, `agent/h3film/run-v3.sh`, `agent/h3film/launch-locked.sh`) are zsh: zsh must be at `/bin/zsh`. They edit files in place with `perl -pi` and read a file's age with zsh's own `zstat`, which work the same on both systems. `caffeinate` runs only where it exists.
- Fonts: titles, Latin captions and frame-sheet labels fall back to Inter. Captions and lyrics in Japanese, Chinese, Korean and other non-Latin scripts need fonts with those letters (4.13).
- On Linux (the server image in 7.7 sets all this up): madmom builds from source and needs a C compiler; `opencv-python` needs `libgl1` and `libglib2.0-0` on a server without a desktop (or `opencv-python-headless` at the same version); Playwright's Chromium and HyperFrames' headless shell need Chromium's system libraries (`npx playwright install --with-deps chromium` installs them on Debian and Ubuntu); on Linux ARM64 HyperFrames has no headless shell build. Map pages use WebGL; their speed and output on a server without a GPU are untested.
- Text the planners read still carries the lab's `/Users/alecli/…` paths: the example plans of `retro-vhs` and `line-draw-on`, the example runs `h3film-t-breathe` and `h3film-t-event`, `agent/h3film/library/proven/TRANSLATE-PROMPT.md`, and `skills/h3-film/references/briefs.md` with its copy in `parts/`. A planner can copy such a path into `render.json`; the stop hook lists missing files back to it, at the cost of a turn. `agent/v2/direction/emuwar-30s/beats.json` (never used by a map film) also names lab paths.
- The test requests name their uploads by the lab's paths (8.3).
- The page builders and `tools/build-batches.py` default their run folders (`RUNS`) to the lab machine's path; point `RUNS` at a copy of the run folders.

### 7.6 Running many films

- One film launch at a time per machine (`/tmp/h3-launch.lock`) and one scene detection at a time (`/tmp/h3-kit-cuts.lock`). A service that gives each film its own working copy does not need the launch lock.
- Every film's clips go to Modal at once, except clips continued across a seam. Modal's Starter plan renders 10 clips at once for the whole account, so a batch of films queues.
- Films write into the repo: studied looks become new cards and `refs/<id>/pool/look-N.jpg` under `agent/web/app/styles/`, launch films rewrite `agent/h3film/library/CASTABLE-index.md`, and caches fill `agent/runs/` and `agent/artcache/`. Give each worker its own writable checkout, and keep these out of unrelated commits.
- Never edit `film`, `agent/h3-film-agy.sh`, `agent/h3film/run-v3.sh` or `agent/h3film/launch-locked.sh` while films run: zsh reads a running script by byte offset, and on 10-10 one such edit killed 6 of 8 running launchers. Edit a copy and `mv` it into place.
- Run folders hold users' uploads. Never commit `agent/runs/`.

### 7.7 Running on a server

`Dockerfile` builds one image that makes one film per container run, as 7.4 does on a Mac:

- Debian 12 with Node 22, Python 3.14 (uv) and `requirements.txt`, ffmpeg and ffprobe 9.0.1, deno, zsh, tini, Chromium's libraries, Noto CJK fonts, yt-dlp 2026.08.19, and Claude Code 2.1.285 from npm (`@anthropic-ai/claude-code@2.1.285`). The producer and the planner start it as `claude -p`, as on the Mac; the map stages' Agent SDK runs the same `claude`.
- Films run as the user `node` (uid 1000): Claude Code refuses to skip permission prompts as root. The image's `.env.local` is empty: keys come from the environment.
- `MAPS_SANDBOX=0`, a guard: the map stages already run with Claude Code's own sandbox off (`agent/v2/run.mjs` starts both with `sandbox: false`), and that sandbox needs bubblewrap with user namespaces, which GitHub's Linux machines refused; the container is the boundary.
- Build for x86_64 (Google Cloud's machines): `docker buildx build --platform linux/amd64 -t h3-film .`, or `gcloud builds submit --tag <region>-docker.pkg.dev/<project>/<repo>/h3-film`. On arm64 the HyperFrames browsers are skipped.
- One film: `docker run --rm --env-file keys.env -v "$PWD/runs:/app/agent/runs" h3-film "<request>" [files…] [--aspect 9:16] [--duration 30] [--name <run>]`. `keys.env` holds the keys of `.env.example` plus `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`. The runs folder must be writable by uid 1000 (`sudo chown 1000:1000 runs`); files given to a film must be mounted too. The film is `runs/h3film-<name>/final-gpu.mp4`; no film means exit code 1, except a request the producer refuses or a lyric video with no song (exit 0, the reason printed).
- Only the runs folder outlives a `--rm` container. Caches that save time across films live elsewhere: mount `/app/agent/artcache` (pictures), `/app/agent/v2/tools/data/dem` and `/app/agent/v2/tools/data/relief` (map relief) to keep them. A film that studies a video's look writes a new card and its pictures under `/app/agent/web/app/styles/`, which its own render reads: plan and render it in the same container (`./film` does both). The seed files copied into the runs folder at start never overwrite what is there, so use a fresh runs folder for a new image. The image has no `.git`, so `manifest.json` records no code version.
- rembg downloads its model on first use in each new container (mount `/home/node/.rembg`, or set `U2NET_HOME` to a mounted folder, to keep it). YouTube needs yt-dlp cookies, in `/home/node/.config/yt-dlp/config` (7.2).
- Tested: on 10-12 the image made row x27 (the Obsidian launch film) on GitHub's x86_64 Linux in about 17 minutes, through `.github/workflows/server-image.yml` (run it by hand from the Actions tab; it makes the film only when the repo has the keys as secrets). That run used this Dockerfile and Claude Code 2.1.285 but the code from before the two paths (1.3): the swap question and a normal film's return to the batch's code have not run on Linux yet, and no other kind of film has run in the image.

## 8. Testing

The same request gives a different film each time: the planner writes something new, and every render draws a new seed. One take is evidence, not proof. Prove the plumbing for free first, then make one real film per kind of film a change reaches, and judge it against the earlier takes of the same request.

### 8.1 Checks that cost nothing

These need no keys and spend nothing. This repo was checked against the lab this way when it was cut (10-12): the planner's input byte-identical, the render jobs identical.

- **The style list:** `node agent/h3film/auto.mjs --catalogue` reads the menu, the cards, `ratings.json` and `best-takes.json` and prints every style with its section, best score and planner mode. It needs `.env.local` to exist and makes no API call.
- **The tool list:** start `research/h3/mcp.mjs` with the env the launcher writes into a run's `mcp.json` (an `H3_OUT` in a scratch folder is fine; nothing is written at start), send MCP `initialize` then `tools/list` over stdio, and compare each tool's name, description length and input fields before and after a change. A launch film lists 12 tools; a painted film 11, with `map_shots` and without `check_prompt` and `join_film` (3.9).
- **The launcher, with a fake `claude`:** mirror the repo in a scratch folder: links to its folders; real copies of `agent/h3-film-agy.sh` and `agent/h3film/launch-locked.sh` (they find the repo from their own path); real folders holding links wherever films write (`agent/runs/`, the style cards and refs, `agent/h3film/library/`). Give the mirror an empty `.env.local` and a HOME inside it. Put a fake `claude` first on PATH that saves its arguments, the names of its environment variables, its working folder and its stdin, then exits 0. Run real briefs the way `auto.mjs` does, under `env -i` with the variables it sets for that brief (`manifest.json` `flags` records the effort, examples and skill):
  `PLANNER=claude CMODEL=claude-sonnet-5-5 CEFFORT=… LAUNCH=… MINIMAL=… EXAMPLES=… SKILL=<mirror>/skills/h3-film/SKILL-gemini.md RATIO=… H3_DURATION=… ./agent/h3film/launch-locked.sh <run dir> -- ./agent/h3-film-agy.sh <name> <brief> 0`.
  Compare what the fake saved before and after the change (stdin is the planner's whole prompt): only the lines you meant to change may differ. Use one brief per kind of film the change reaches (launch, painted, footage, lyric, map, references), and check that nothing was written into the repo.
- **The render, with a fake Modal:** `comfy_r2v.py` makes one Modal call per clip (`modal.Cls.from_name('h3-render', 'H3')().render.remote(graph, files)`). A stand-in `modal` package first on `PYTHONPATH` can log each call (the graph and a SHA-1 of every uploaded file) and return the run's own clip from its `render-gpu/` folder, or an ffmpeg test pattern of the clip's size and length. Set dummy `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` and point `MODAL_CONFIG_PATH` at a missing file, so nothing real can run. Run render-all before and after the change on two copies of one finished run (without `render-gpu/`, `final*.mp4`, its render logs and `spend.json`; the run path inside `render.json` rewritten) and compare: the same clips, the same graphs once upload names and the noise seed are set aside, the same input keys (`render-gpu/*.key`) and clip JSONs, the same `render` block in `manifest.json`, and a `final-gpu.mp4` on both sides.
- **Replays:** `node agent/h3film/build-edit.mjs <run>` rebuilds an edit from its `EDIT.json` (deterministic). `node agent/h3film/check-prompt.mjs <prompt>…` runs the arrival check. `planner-stop.mjs` exports `decide(run, calls, io, state)` for replays over old transcripts. `python3 agent/h3film/reading-report.py <run>` lists required reading a session skipped.
- **Same input, same films:** `tools/same-input/` (its README) records the producer's and the planner's first request on two checkouts against a stand-in API and compares them byte for byte. This is how the two paths were checked against the films that made them (1.3).
- **The render cap:** `H3_BUDGET_USD=0 node agent/h3film/render-all.mjs <run>` on a planned run prints `REFUSED: renders cost $X, budget $0` before any GPU call (a live-action swap clip still asks Nano Banana for its swapped first frame first). An empty `.env.local` makes every paid API call fail.
- **The mix, parts and seams:** a library bed and no lines makes no provider call:
  `node -e "import('./research/h3/soundtrack.mjs').then(async m => console.log(JSON.stringify(await m.makeSoundtrack({music: 'house-groove', duration: 12, parts: [6, 6], snap: true, beats: true, outDir: '/tmp/st/soundtrack'}), null, 1)))"`. Add `from` lines from a local video with speech to exercise placement, ducking and snapping.
- **The join and captions:** call `joinFilm()` from `agent/h3film/join.mjs` on short test mp4s (ffmpeg's `testsrc`) with that soundtrack and a few captions (one plain, one `"style": "title"`, one non-Latin).
- **A type still:** `node agent/h3film/still.mjs /tmp/t.png text "Exact words" 0.1`.
- **A map section of a finished map run** (no AI; no picture calls while every cast PNG exists), on a copy of the run: `V2_OUT=<run>/maps/direction V2_FILM=<run>/maps/film RUNS_DIR=<run>/maps/logs node agent/v2/run.mjs map h3-<name> <shot>`. With `.direction-done` and `.choreo-done` in place, `node agent/h3film/maps.mjs <run>` redoes only the final render.

### 8.2 Testing a change, in order

1. The free checks above.
2. The producer alone: `./film "<request>" --dry`. Compare its pick and brief with the request.
3. Planning without rendering: `./film "<request>" --plan`. This pays for Claude, stills and sound, not for GPUs. Read `PLAN.md`, the stills and the prompts.
4. The render path with the cap at 0.
5. One whole film: `./film "explain how a touchscreen knows where you tapped" --aspect 9:16 --duration 30 --name touch`.
6. Rows of the run sheets, one take each, each judged against the earlier takes of the same row (8.5), one row per kind of film the change reaches. Rows by kind: launch x12 (a launch film for Magic Hour with screenshots and a logo), x27 (a bare product address); footage montage x09, x26; talking edit x06; a cartoon character swapped into footage x01; a video to follow x21, x22; map x10; code clip x20; lyric and music m1-m6, u1; the user's references x05, x13, x19; explainers x02, x08, x16, x17. Live-action swaps of real people and a scene remade in another look are on no run sheet.

### 8.3 The run sheets

| File | Rows | Columns | What it was for |
|---|---|---|---|
| `agent/h3film/random-inputs-v3.tsv` | x01-x28 (10-11) | id, aspect, request, files, seconds, source | the newest test set; the 10-11 batch page |
| `agent/h3film/music-inputs.tsv` | m1-m6, u1 (10-10/11) | id, aspect, request, files, seconds, source | music and lyric videos |
| `agent/h3film/random-inputs-v2.tsv` | r01v-r12v, b11v-b33v (35, 10-10) | id, aspect, request, files | fresh variants of the first sheet; the 10-10 cost study (no length column: the planner picks) |
| `tools/pages/library/random-inputs.tsv` | r01-r12, b11-b33 | id, aspect, request, files | the first sheet, read only by the library page builder; new tests use the variants |

Every request is exactly as a user typed it, typos included. An empty aspect lets the producer pick. x01-x07 and the music rows are requests typed fresh on 10-10 and 10-11; x08-x15 retry styles and kinds that had failed or been dropped; x16-x28 try kinds of film and inputs not tried before (a request in Spanish, a 60 s request, numbers pasted into the request, several clips attached, a bare product address).

```sh
mkdir -p agent/runs/_auto     # run-v3.sh writes its log there before auto.mjs creates the folder
TSV=agent/h3film/random-inputs-v3.tsv RUNPFX=t1 agent/h3film/run-v3.sh x02 x20 x24
```

For each id, `run-v3.sh` loads `.env.local`, clears `CLAUDE*`, sets `H3_BUDGET_USD=20` and starts in the background `node agent/h3film/auto.mjs "<request>" <files> --aspect <aspect> --duration <seconds> --name <RUNPFX>-<id>` (`--duration` only when the fifth column is a number), with its output in `agent/runs/_auto/<RUNPFX>-<id>.out`. It skips an id whose run is already going. The film lands in `agent/runs/h3film-<RUNPFX>-<id>/final-gpu.mp4`. Pick a new `RUNPFX` for each round (earlier rounds used `v3` to `v48`).

The files column names uploads by absolute paths on the lab machine and is split on spaces. Most are under `/Users/alecli/h3-footage-samples/` (2.3 GB), which is not in this repo; x11's and x12's logos are here as `agent/refs/airbnb/logo-mark.svg` and `agent/refs/magic-hour/logo-mark.svg`; x12's three screenshots and x13's mascot picture are not. Rewrite the column to where the files are before running those rows, or use files of your own. Rows with a link, and most others, also need yt-dlp to reach YouTube.

### 8.4 The test films: `batches/`

`batches/` holds every test film shown on the seven pages linked above, plus the latest batch (10-12, made from this repo): 348 films. `batches/films/<run>/` has `final.mp4` (the film as it came out), `brief.txt` (opening with the request as typed), `PLAN.md`, `NOTES.md`, `prompts/clipN.txt`, `render.json`, `EDIT.json` for edits, `soundtrack.json` and `manifest.json` (most runs from 10-09 on). Pictures, sound files and downloads are not included; the record says which ones each clip used. `batches/index.csv` has one row per film: `film`, `pages`, `request`, `kind`, `use_case`, `style`, `planner` (`claude-sonnet-5-5` for the current pipeline; `claude-opus-5-5` for hand-run style examples; `gemini-3.8-flash-high` for films of 10-05 to 10-08), `length_s`, `score`, `ai_usd`, `pictures_sound_usd`, `render_gpu_s`, `render_usd`, `total_usd`, `usd_per_s`, `planning_min`, `render_min`, `longest_clip_gpu_s`, `minutes_all_clips_at_once`, `date`. `batches/README.md` describes every column. `tools/build-batches.py` rebuilds the folder from the run folders, which are not in git.

To see what the current settings make, read the films planned by `claude-sonnet-5-5` with the highest scores (9.1); to see what a change does, compare a new take with the same row's earlier takes there.

### 8.5 The bar for each row

The newest scored take of each row (`ratings.json`; the films are in `batches/films/<take>/`):

| Row | Frame, length | Request in short | Uploads | Take | Score |
|---|---|---|---|---|---|
| x01 | 9:16, 40 s | basketball analysis video with the player replaced by Peter Griffin | | v44-x01 | 7.5 |
| x02 | 9:16, 35 s | short explainer: a milk truck behind you against an oil tanker | | v32-x02 | 7.5 |
| x03 | 9:16, 60 s | movie recap narrated as the main character | | v42-x03 | 7.5 |
| x04 | 16:9, 60 s | trailer for an unreleased Spider-Verse film | | v47-x04 | 7.5 |
| x05 | 16:9, 20 s | the user's character doing the dance of a linked video | 1 picture | v42-x05 | 8 |
| x06 | 9:16, 45 s | podcast clip edited for Shorts | 1 video | v46-x06 | 8 |
| x07 | 9:16, 50 s | satisfying clips under a narrated Reddit story | | v32-x07 | 8 |
| x08 | 16:9, 30 s | DNS explainer in a named YouTuber's style | | v32-x08 | 7.5 |
| x09 | 9:16, 15 s | the user's bike clip edited like a linked TikTok | 1 video | v42-x09 | 7 |
| x10 | 16:9, 30 s | animated map: Hannibal crossing the Alps | | v41-x10 | 7 |
| x11 | 16:9, 10 s | Airbnb logo animation, a shape morphing into the logo | 1 logo | v42-x11 | 8 |
| x12 | 16:9, 30 s | kinetic-type launch film for Magic Hour like a linked one | logo, 3 screenshots | v42-x12 | 8 |
| x13 | 9:16, 20 s | bouncy cartoon ad starring the user's mascot | 1 picture | v32-x13 | 8 |
| x14 | 16:9, 45 s | calm guided animation like a linked meditation video | | v42-x14 | 8 |
| x15 | 16:9, 40 s | charts and callouts on the user's talking video | 1 video | v32-x15 | 8 |
| x16 | 16:9, 40 s | gradient descent explained with smooth math animation | | none scored | |
| x17 | 16:9, 50 s | documentary of the Hyatt Regency walkway collapse | | v38-x17 | 8 |
| x18 | 16:9, 45 s | what standing on Titan would be like | | v42-x18 | 7.5 |
| x19 | 9:16, 15 s | cute 3D dog short like a linked one | 1 photo | v42-x19 | 7 |
| x20 | 9:16, 20 s | ball bouncing in a spinning ring, a note per bounce | | v42-x20 | 9 |
| x21 | 9:16, 30 s | realistic monkey short like a linked one | | v42-x21 | 7.5 |
| x22 | 9:16, 30 s | request in Spanish: raising a megalodon from a baby | | v42-x22 | 8.5 |
| x23 | 16:9, 60 s | baby sensory video, dancing vegetables | | v38-x23 | 9.5 |
| x24 | 16:9, 30 s | size comparison of the biggest ships | | v32-x24 | 9 |
| x25 | 1:1, 20 s | animated chart of the request's monthly numbers | | v32-x25 | 8 |
| x26 | 16:9, 15 s | promo cut from three uploaded business clips | 3 videos | v32-x26-titles | 8.5 |
| x27 | 16:9, 30 s | a bare product address, nothing else | | v39-x27 | 9 |
| x28 | 4:5, 15 s | the user's candle giant in a real city street | 3 photos | v42-x28 | 7 |
| m1 | 9:16, 20 s | anime music video for a named song, style from a link | | v38-m1 | 7 |
| m2 | 16:9, 30 s | cinematic music video in a linked game cinematic's look | | v38-m2 | 6.5 |
| m3 | 16:9, 30 s | lyric video copying a linked lyric video's type | | v38-m3 | 7 |
| m4 | 16:9, 30 s | pixel-art lyric video, style from a link | | v33-m4 | 9 |
| m5 | 16:9, 30 s | animated lyric video, style from a link | | v36-m5 | 8 |
| m6 | 16:9, 30 s | sing-along for toddlers in a linked video's 3D look | | v46-m6 | 6.5 |
| u1 | 9:16, 20 s | lyric video for the user's own song, style from a link | 1 song | v38-u1 | 7.5 |

These takes were made on the lab's code of 10-10 and 10-11, before the fixes of 10-11 night and 10-12, each of which was tested on the film that showed its problem (`docs/history.md` lists them). Map films have not scored above 7, and music videos are the weakest group (four of seven rows at 7 or less).

### 8.6 What a good result looks like

In the files:

- The last line is `h3film-<name>: done, …/final-gpu.mp4` and the exit code is 0.
- The film is H.264 (yuv420p, CRF 18) with AAC sound, 24 fps when it has an H3 clip.
- Its size is H3's render size for the frame (5.7), or 1920x1080 (1080x1920 tall) with map-engine shots.
- Its length is the soundtrack's; with `--duration d`, between d and d + 0.45 s.
- The run folder has no `FAILED.json` and no `maps/failed.json`; `manifest.json` `session.status` is `success`; `agent/runs/_auto/<name>.log` has the reading report with `required skipped: none` and ends with `rendered N clips in X s … on Modal → …/final-gpu.mp4`. A line `<clip> came back boxed` names a clip H3 drew with black bars on both sides.
- For comparison, the `manifest.json` `flags` of a 10-12 test film planned at high effort read `MODEL claude-sonnet-5-5`, `PLANNER claude`, `CEFFORT high`, `SKILL …/skills/h3-film/SKILL-gemini.md`, `RATIO 9:16`, `H3_BUDGET_USD 0`, `H3_CALL_LIMIT_S 1750`.

On screen, the films scored 8 to 9.5 share these: the request is understood as meant (a named format looks and sounds like its most viewed real example; a linked video's look and pace carry over); each place and character stays the same from shot to shot, and nothing that left comes back; words on screen are exact, because they come from stills or captions drawn in code; each speaker has a fitting voice and only the speaker's lips move; cuts and on-screen events land on the speech and the beat; the user's footage plays as filmed; music, voices and effects sit at one level.

What fails most, from 339 reviewer notes on the films of 10-09 (the first pass was rebuilt from them):

| Kind of failure | Notes |
|---|---|
| Things coming back after they are gone, looks drifting | about 120 |
| Shots asking more than H3 shows | about 105 |
| The place falling apart | about 40 |
| Lines and cuts at the wrong moment | about 30 |
| Footage not played as filmed | about 20 |

### 8.7 How films were judged and scored

- Each test film was one take of a run-sheet request, made unattended from the request exactly as typed, with nothing picked by hand.
- project-owner watched each film and scored it out of 10, on the batch page or in chat. Scores are in `agent/scorecard/ratings.json`, keyed `<run folder>/<film file>`, with `rating` (older entries) or `score`, `note`, `rated_at`: 431 entries, 309 with a number, 157 at 8 or more.
- A film with no mistake named scores at least 8, higher (8.5 to 9.5) with stronger praise; named mistakes put it at 7 to 7.5; barely usable films scored 4.5 to 6.5.
- A change was judged by making the same rows again and comparing each new take with the earlier takes of that row. Choices between two methods went on a separate page showing the two side by side, sometimes blind (the launch-film effort level on 10-10 was chosen this way). Takes made only to test a method stayed off the shared batch pages.
- This repo has no automatic judge. An automatic reviewer was tried and rated the same take differently from pass to pass (9.2).
- The producer uses the scores too (2.13).

### 8.8 Costs and times

**Where they are recorded:**

| What | Where |
|---|---|
| Producer's Claude cost and time | `agent/runs/_auto/claude-calls.jsonl`: `cost_usd` and `ms` per call, keyed by `run` |
| Planner's Claude cost | `<run>/transcript.jsonl`, the `result` line's `total_cost_usd`, copied to `manifest.json` `session.cost_usd` |
| Planner's time | `<run>/t0` and `t1`, `manifest.json` `session.planning_min` |
| Map stages | `<run>/maps/done.json`: `stages`, `stages_usd`, `minutes` |
| GPU time | each `<run>/render-<clip>.log`: the seconds in `(N s rendering on <GPU>)` |
| Pictures | PNGs in `<run>/storyboard/` plus the `image` tool calls in `manifest.json` `session.tools` |
| Voices, music, effects | `<run>/soundtrack/soundtrack.json`: characters of generated lines, music length when generated, each generated effect's length |
| Whole film | from the start of `auto.mjs` to the modification time of `final-gpu.mp4` |

`tools/build-batches.py` and `tools/pages/batch/build.py` combine these per film; `python3 agent/h3film/planner-cost.py <run>` prints one run's planning minutes, planner cost and GPU minutes.

**The basis (Magic Hour's):** Claude as Claude Code reports it, at list price with the 5-minute prompt cache. Pictures $0.0336 an image (Nano Banana 2.1 at 1K); voices $0.00025 a character; generated music $0.0025 a second of film; generated effects $0.002 a second each, at least 0.5 s. Render: GPU seconds from the render logs at $3.03 an hour (Modal's RTX PRO 6000 price; a B200 is $6.25), with no container start-up, idle or queue time and none of Modal's CPU and memory charges. A Claude session log repeats a message's usage on every streamed chunk: sum by unique `message.id` (or use the `result` line), or totals run 4 to 5 times high.

**The numbers:**

- The 35 newest takes of the test requests (10-10/11, 480p): 1,120 s of film, $53.63 in all. Per film, medians: producer 0.8 min and $0.14; planning 3.3 min (1.2 to 7.4) and $0.43; pictures and sound $0.16; render and join 5.7 min (0.1 to 16.2) and $0.66 (781 GPU seconds); a whole film 11.1 min (2.6 to 22.5) and $1.46 (mean $1.53, from $0.52 for a short drawn in code to $2.81 for a character swap on real footage). Medians of the parts do not add up to the median of the whole. Per second of film: 4.79 cents over all 35; the median film 4.72; the middle 80% 3.7 to 7.0. AI stayed under $1 on 32 of 35 films (over: a launch film $1.17, a lyric video $1.10, a sing-along $1.02). GPU time: about 23 GPU seconds per second of film for painted films, 51 to 63 for footage edits. The one map film measured on Sonnet stages cost $0.94 of AI, $0.58 of it the map stages.
- The latest batch (films of 15 to 60 s made on 10-12 from this repo; the `latest` rows of `batches/index.csv`, not yet rated): about 21 s of wall time per second of film on average (8 to 38: agent 14 s, rendering 8 s, with all of a film's clips rendering at once), and about $0.05 per second at 480p ($0.02 to $0.085: agent $0.025, pictures and sound $0.005, rendering $0.022 at 26 GPU seconds per second of film). Rendering grows with resolution, roughly 2.5x at 720p and 3.5x at 1080p (5.8). These are the Overview's figures.

**Caveats:** a clip that lands on a fresh GPU adds about 16 s of model loading to its logged GPU time (warm servers skip it), so compare only takes rendered in the same conditions. Several films shared the 10-GPU cap in the batches, so measured render times include queueing. Claude Code 2.1.285 prices Haiku 5.5 helper calls as Opus, so AI costs logged after 10-12 morning read high. `spend.json` and `H3_BUDGET_USD` use fal's price: a cap, not a cost.

### 8.9 The page builders (`tools/pages/`)

Each folder rebuilds one of the pages linked at the top; a builder writes only to its own `out/`, which git ignores; its README has the command, what it reads and how the page was published. The library page rebuilds from this repo alone; the others need the run folders (`RUNS`) and the test uploads, which are not in git.

| Folder | Page |
|---|---|
| `library` | [Internal library](https://claude.ai/artifact/XgUGhxuSZSPdpwDET9vcYF) |
| `gallery` | [Quick output gallery](https://claude.ai/artifact/25Neomyh8NnVyMYcPzDa33) |
| `batch` | [Tonight's Batch, 10-11](https://claude.ai/artifact/CnoJEe6hqJonBHqkkVRGdJ) |
| `costs` | [Current Film Costs, 10-10](https://claude.ai/artifact/3zYh3KzZnVYkQeBuQQF34e) |
| `round2` | [Random Inputs Round 2, 10-10](https://claude.ai/artifact/G8ZhLvZf1mZdFbKZKs8He7) |
| `review` | [Random Inputs Review, 10-10](https://claude.ai/artifact/CFcZ4ZQMtwYYE4oSnsLWpa) |
| `scorecard` | [Style Scorecard, 10-07](https://claude.ai/artifact/Y2HZ3WXFqJ28H6YX7CbFou) |

## 9. Decisions that must not be undone, and what was tried and rejected

Every setting in sections 1 to 6 is the one the best recent films were made with. This section says which choices made them, with the test behind each, so nothing proven gets undone. Dates are 2026. Test names: x01 to x28 are rows of `agent/h3film/random-inputs-v3.tsv`, m1 to m6 and u1 rows of `agent/h3film/music-inputs.tsv`, and "row bNN" the 10-10 run sheet; the films are in `batches/films/`.

### 9.1 The best recent films

| Score | Request (date) | Kind and style card | Planner effort |
|---|---|---|---|
| 9.5 | x23 (10-11): a sensory video for a 7-month-old like a linked Hey Bear video | painted, Baby Sensory, `fruit-sensory` | medium (it follows a given video) |
| 9.5 | row b17 (10-10): a cinematic film on the history of the Motherland Calls statue | painted documentary, `mannequin` | high |
| 9.5 | row b26 (10-10): a bedtime story about a dinosaur who is scared of the dark | painted explainer, `hand-drawn` | high |
| 9 | x24 (10-11): a size comparison of the biggest ships ever built, like a named channel | painted, Size Comparison, `scale-3d` | high |
| 9 | x27 (10-11): nothing but the address of Obsidian's website | launch film, `dark-product` | medium |
| 9 | row b18 (10-10): a 3D launch film for an AI haircut app | launch film, `cinematic-mockup` | high (launch films moved to medium that evening) |
| 9 | m4 (10-11): a Midnight City lyric video in the pixel-art night look of a linked video | lyric video, a look the producer studied | high (lyric videos moved to medium on 10-11) |
| 9 | x20 (10-11): a ball bouncing in a spinning ring, each bounce the next note of Für Elise | one code clip, a studied look | medium |
| 8.75 | the Excalidraw launch film (10-03) | launch film; the locked bar for launch films (planned by the Gemini planner of the time) | |
| 8.5 | x22 (10-11): in Spanish, raising a megalodon from a baby to a giant, like a linked Short | painted, Creature What-if, `raise-beast` | medium |
| 8.5 | x26 (10-11): a promo cut from three uploaded business clips | footage edit | |
| 8.5 | row b31 (10-10): a launch film for Linear | launch film, `dark-product` | high |
| 8.5 | rows b15, b19, b20, b22, b24 (10-10): Dijkstra's algorithm visualised; a mother's 60th birthday; a house listing; compound interest for a 12-year-old; a save-the-date | painted (`clean-infographic`, `watercolour-invitation`, a studied look, `2d-cartoon`, `watercolour-invitation`) | high |

Other good footage edits: x06 (a podcast clip cut as a Short, 8), x05 (the user's character doing a linked dance, 8), x15 (charts and callouts on the user's video, 8). Live-action swaps were judged side by side on 10-12, not scored (9.6). No map film reached 8 (best 7). Music films: m4 9 and m5 8; the rest 6.5 to 7.5.

What the top painted films have in common: every clip prompt opens with the card's style sentence, then a line saying the reference pictures are style only and that everything in the film, including things no reference shows, is drawn in that style; few stills, each with one job (the card's sample frames as style references, and one design still per recurring character or object: one per ship in x24; the little dinosaur and its mother in b26; the statue and a soldier in b17; x23 made no stills of its own); one composition per clip and no pins (pins carried the films that hold several shots in one clip: a fruit dating show, 8, had 15 pins in 3 clips); no reference video.

What the top launch films have in common: real screenshots turned into simplified hero stills by edits, every later state an edit of the still before; the end card as one designed lockup still; the cast components' motion clips as reference videos; Magic Hour v13 and the card's own example film pasted whole.

### 9.2 Rules for every film

Each rule, then the evidence that set it.

1. **One take per request; quality comes from the first pass.** No re-render loops, best-of-N takes or review-and-fix rounds. `auto.mjs` retries render-all only while no film exists, and render-all reuses every clip whose inputs match. Evidence (10-09): a watch-and-fix loop made one 4-clip film from 28 clip renders and another from about 60 renders over 3 films; every re-render is a new seed, and the automatic reviewer rated the same take differently from pass to pass, so the rounds never settled, and the user would pay for every round. The loop was deleted and the first pass rebuilt from its 339 notes.
2. **A bad take has a cause.** Find it in the files and fix it; re-rolls only measure how often a failure happens. Evidence (10-10): the same seeds reproduce a film (43 dB match), and new seeds give films that look alike, so take-to-take differences come from what the planner writes (nonsense text in 2 of 5 takes of one request came from its prompts).
3. **A tool failure stops the film.** A provider or account error writes `FAILED.json`; nothing renders. Evidence (10-03): ElevenLabs ran out of credit and films went out with library music and no voice.
4. **Sound comes first and is held fixed; the picture follows measured times.** One `make_soundtrack` call before any prompt; every row from the returned line times; each clip's slice held fixed inside H3 (5.3). Evidence: 0% word errors and the best lip and beat sync of the three ways tested (10-08); H3 will not speak over a track it is given (09-08); launch films that gave render seconds instead of spans ran up to 1.2 s ahead at each cut (09-28 to 10-10).
5. **Prompts go to H3 word for word; no rewriter.** Evidence: a rewriter summarised a long prompt to a paragraph a shot and dropped its framings and timings (09-17); MiniMax's own rewriter cut about 17%, mostly the consistency lines (09-08); style words added by a rewriter fixed a look but made the motion worse (09-30), so a style sentence is written into every prompt instead.
6. **Prompts say what to show, positively,** the distinctive things first (exact skin tone, hair, face, clothes), in words that cannot also fit what is there now. Evidence (10-12, a swap on real footage, same seeds and photos): prompts with "not X" or "nothing of X remains" clauses gave the same film with the same mistakes; a more exact positive word ("warm brown skin" rather than "light brown") fixed it.
7. **Every noun in a prompt can end up on screen.** Evidence (09-30): "hot spot" in a style's motion lines gave glowing orange engines; "arrows" written three times in a card put wrong-way arrows in every still; motion lines naming icons, a vehicle and rings brought trucks and gibberish labels.
8. **H3 follows framings and stills, not camera verbs.** Write what fills the frame at each time, in coarse ranges (`2.7-3.3s —`); when a description fails twice, change the still. Evidence (09-15/16, 30 takes): camera verbs and waypoints were ignored; a placeholder in the still survived 7 takes of words asking to type over it, and a glow described in words flickered for 5; changing the still fixed each in one take. Rows with no times, or with two-decimal times, were worse (09-17).
9. **Attached stills are timeless; pins fix a moment.** Text every clip sees holds only what is true all film. Evidence (10-09): a balloon in an attached still came back after it popped, and characters drawn on plain grey brought the grey into their close-ups; with pins, the film kept one studio, cut hard at every pin, and popped balloons stayed gone.
10. **Pictures of one place come from one master picture.** Evidence (10-09): seven fresh drawings of one school gate came out as five different gates.
11. **Words on screen come from stills or code, never from H3's own lettering;** at most three of anything that must be counted. Evidence: H3 garbles words it animates or invents (10-05); size words such as "large labels" worked only in some takes (10-01); 3D letters asked for with no still gave gibberish (10-10); asked for seven sailors, H3 drew eight (10-04).
12. **References outrank prompt text.** Evidence: character stills made their character the lead despite a ban line, so they are opt-in (09-12); one film's stills handed over its palette, so sample frames come from two or more films (09-12); a style reference video made H3 copy its subjects, so painted films get none except the four clip cards (10-05); a font specimen sheet sent as a reference became a scene (09-17); a reference clip's sound came back sung as a foreign voice, so every reference video goes in silent (09-28).
13. **Cut clips where the film cuts, and finish early.** A clip is at most 15 s and starts at a hard cut; every transition lives inside one clip; the last event ends at least 0.7 s before the clip does; no iris or wipe opens a clip; every clip stands alone. Evidence: H3 runs late and drops a last event that comes closer to the end (09-17); hold-to-hold seams, frame-mode bridges and crossfades all failed (09-17); clips render alone, so an iris at a clip start opened out of a reference picture, and a clip tail dimmed the seam and replayed entrances (09-30).
14. **The producer watches the real thing,** and a named format means its most viewed real example, never a tutorial about it. Evidence (10-09): with text research only, a game-show film invented its set and lines; once the producer watched a real episode, the next take had the real studio, the host's question and the twist ending. (10-11): a podcast edit modelled on a before-and-after editing demo came out plain.
15. **The brief gives facts and the point, never the look, a shot list or jokes.** Evidence (10-09): when the producer read the card, its brief became the card's shot list and the planner filmed that list; (10-10) a brief asking for gags got a pun script from a style that plays it straight.
16. **Keep what is proven; change one thing at a time.** Examples are whole approved films from real runs, pasted whole; never an invented example. Evidence (10-03): the locked launch film came from pasting two whole approved films and adding three short tool-text lines; long piles of extra rules in tool text did not help. On 09-29 the one best-evidenced change fixed the stills on its own.
17. **Fix the general layer first, and never one film's case in a shared file.** A card changes only for its own look, or to drop a line that contradicts the general rule. Evidence (10-09, 10-10): a run of fixes for one meme film's pacing broke what worked and was reverted; a clause about one take's misread stamp in the producer's shared format rule had to come out; a rule telling the planner to ignore a card's dialogue lines also threw away the card's correct ones and brought pun dialogue back.
18. **A prompt sentence before machinery; a better default before a check.** Evidence (10-04): `check_prompt` on painted films raised only false flags and planners weakened their motion to pass it (one deleted a route drawn over open sea).
19. **Effort is set by the kind of film.** Producer medium; planner medium for launch, lyric and followed-video films, high otherwise; map stages medium. Evidence (10-10): medium cut AI cost 23-47% on six films but came out worse on 4 of them and last on both edit rows; for launch films medium beat high in blind picks (2 of 3 rows against 0 of 3).
20. **Platform limits come from the source.** Magic Hour's prompt cap is 20,000 characters; Claude Code cuts MCP tool descriptions at 2,048 characters unless told otherwise. Evidence: a stale 10,000 cap made one launch planner spend four model calls and ten edits trimming a prompt (about $0.40 of a $1.93 film, 10-10); the 2,048 cut hid `user_video`'s montage template and the image tool's product-still rules from every planner (found 10-10, fixed 10-11).
21. **Film sessions never see coding-agent instructions.** The producer and planner run outside the repo, `./film` clears `CLAUDE*` variables, the map stages load no settings. Instructions for changing the code must never reach a film.

### 9.3 Launch films

The rules are in 3.8 (`SKILL-gemini.md`) and the tool descriptions (3.9). The decisions behind them:

- The launch path for every software product with a URL or screenshot, whatever its card; the card sets only the look. Evidence (10-11): a Magic Hour kinetic-type request ran painted on its card and lost the product-screen rules and the v13 example.
- Two whole approved films pasted: Magic Hour v13 and the card's own example (Orchids clips only for a card with none), at medium effort. Evidence: the locked Excalidraw film (10-03) came from pasting two whole approved films; on 10-10, blind on three launch requests, medium effort with v13 plus the card's example was best by a little, the card's example alone next, the old default (high effort, Orchids clips pasted too) last. Planners copy these examples closely: in seven launch sessions about 233 phrases came only from the card's example, 99 only from v13 and 12 only from Orchids.
- Product screens are edits of the real screenshot: one keep-list hero per screenshot (never naming a background), every later state an edit of the still before, no close-up or crop stills, never an empty screen. Evidence (09-29): with fresh drawing as the tool's default, a near-raw first still and a new diagram in every clip; a keep-list naming a background shrank the app to an island; making every product still an edit fixed both on two runs.
- The logo is never drawn, controls keep their size, and a still with a broken layout is redrawn: the three short tool lines behind the locked film (10-03). On 10-06 a planner drew its own fake wordmark, so `still` refuses a mark from anywhere but `shots/`, `agent/refs/` or `attached/`.
- Only proven components, their rows copied word for word. Evidence (09-28): weak motion came from planners translating components into rows on the fly; rows translated once, offline, by Opus rendered right the first time.
- Every arrival row cites the still that shows it. Evidence (09-29): both leaks of another product's interface sat on arrival rows with no still.
- Motion clips as reference videos, cut to their proven window, 360 rows, silent. Evidence: the same film with and without references was preferred with them (09-30); at 360 rows a launch clip on a B200 went from 13.5 to 4.9 min (10-03).
- The bar for any change to launch planning is the Excalidraw film (10-03, 8.75).

### 9.4 Painted films

The rules are in 3.8 (`PAINTED.md`, the use-case files, the cards). The decisions behind them:

- Only the painted files are pasted, with only the role lines of `SKILL-gemini.md`, and the session has six built-in tools and no shell. Evidence (10-09): the prompt went from 121 to 71 KB; a film had followed a launch rule pasted above PAINTED's clip rule and built a clip that fell into a black void; a painted planner wrote every clip through Bash.
- The style sentence and the "everything in this style" clause open every prompt. Evidence (09-30): on a topic the sample frames did not show (how a touchscreen senses a tap) the phone came out photoreal and sample content leaked in; these two lines fixed it.
- Sample frames are style only, from two or more films, never cited, never standing in for the film's things; a ban line of at most five items; a frame showing a person never goes to a film with its own characters. Evidence: character frames leaked their character and one film's frames handed over its palette (09-12); a 16-item ban list flashed on screen (10-04); people from a fruit pool were painted in as extras (10-10).
- Design stills for recurring objects and lead characters, never cited on a row; the same short look in words every time. Evidence: without one H3 drew a phone its own way (09-30); a still cited on every row made every clip restart from it (09-30); with words only, a father and son swapped looks between clips (10-04).
- Real characters keep their official pictures and the prompts keep their names. Evidence (10-11): two takes of a trailer redrew the heroes from words and lost what made them believable; the best take attached 3 to 5 designs a clip.
- Anything with writing or labelled parts is a still first; technical subjects are drawn from a real diagram. Evidence: a browser described in words came back with two address bars (10-08).
- Pins open shots, pictures of a place come from one master, and a shot across a seam is chained. Evidence: 9.2 rules 9 and 10; a phone call's wide take jumped back at both seams when its clips rendered apart (10-11). The top painted films used one composition per clip and no pins.
- The opening picture already holds everything later rows use. Evidence: a door first named at 4 s was cut into the window wall.
- A line from someone off screen is named as theirs, and the person in frame listens with lips closed. Evidence (10-11): a listening secretary's lips moved to a broker's off-screen line.
- The picture fills the frame edge to edge; "letterboxed" is dropped from any style sentence. Evidence (10-11): a trailer whose look said "letterboxed" came back boxed.
- Lyric videos (m4 9, m5 8): ids instead of words (the output filter refuses lyrics; an example's ids copied without a `lyrics.json` came out as "[L1]" painted on a road, 10-09); at most 4 lyric lines a clip (H3 slips about 0.5 s per line change; a 7-line clip ended 2.5 s late); lyric rows retimed with lead 0 (10-08); a sing-along always gets a recording sung straight through (10-11: a nursery-rhyme brief had none and the film stopped); a look taken from a video draws every still from 2-3 of its frames whose framing fits (m4 was made this way).
- Studied looks become cards that never overwrite each other (10-10: a second take rewrote the first take's card). m4, x20 and row b20 (8.5) ran on studied looks.

### 9.5 Edits of the user's footage

The rules are in 3.8 (`FOOTAGE.md`) and `user_video`'s description (3.9). The decisions behind them:

- The producer decides what each uploaded or linked video is; only footage is cut into the film (10-11: in Magic Hour's app every reference is an upload).
- Footage plays as filmed; a clean clip is no H3 call.
- One shot per clip, seams on measured beats. Evidence (10-09): one clip cutting between three videos cut off the beat and replayed a moment, and pins at cuts inside one clip landed up to 0.5 s early; one shot per clip put all 7 cuts of the same edit on the beat. Long clips of several shots used the same GPU time and put two cuts 5-9 frames early (10-10).
- A montage is one `EDIT.json` built by code: byte-identical on 87 of 87 clips, planning about a third cheaper (10-10).
- A run of fast cuts is one row with a rate in beats. Evidence (10-09): asked for 24 quarter-second cuts one row each, H3 made 2.
- Zooms and reframes are built by the renderer. Evidence (10-10): a single end pin held the shot and then snapped.
- The first frame is pinned and the footage filled only when the clip has no stills. Evidence: with the pin or the fill crop a meme lost its caption banner (10-10); a wide reference in a tall frame came back as a strip between black bars (10-09).
- Every word on footage is a code caption. Evidence (10-10): H3 painted a meme's caption at a different size and place in each clip and moved the people under it.
- Talking edits cut only for a reason and change picture at sentence starts, with inserts, a held punch-in and a push-in that carries across cuts. Evidence (10-11): a podcast edit cut its long takes into 2-3 s pieces mid-sentence, each restarting its push-in from another size.
- Promos use many short shots from each clip (10-11: three clips of 5 s each read as a slideshow); highlights tell a story (10-09: a season edit of plays in no order); a known clip is the clip people know (10-09: a remake and the raw clip without its explosion each made a worse meme film).
- Fan edits default to 16:9 (10-10: 9:16 cropped the action).

### 9.6 Changing who is in footage

- **A drawn character takes a person's place** (x01, 7.5; x05, 8): the footage is Video 1, the character's real picture an Image with a full design line in words; the person must be big in the shot; the clip's `frame` and `zoom` crop the reference video itself and the clip is never pinned to its own frames. Evidence (10-11): frames pinned from the footage brought the original player back; a close slow-motion shot became the character cleanly, wide broadcast shots did not.
- **Real people swapped into live-action footage** (the swap path, 1.3; settled 10-12 after six rounds on three dialogue scenes): the real person's photo fetched by the producer and attached to every clip that shows them; each person described at a glance on every line that names them, positively, skin tone first; the prompt in MiniMax's reference layout with the node's tags (3.10); a first frame with the swap already made (5.2 step 4d); several of the scene's shots kept in one clip. Judged side by side: better overall than photos, start frame and tags alone. Dropped: one long clip (the swapped person melted back into the filmed actor), one clip per shot (more chances to slip), negative wording (no change), Magic Hour's face swap API (deferred).
- **A movie scene remade in another look with someone new in it** (the swap path): a painted film drawn from pinned stills, cut on the movie's own cuts; the movie never sent to H3. Evidence (10-12): sent to H3 to be redrawn, the scene kept the real actors and office; drawn from pinned stills, three takes came out in the new look. A restyle where the movement is the point (a dance) stays an edit of the footage.
- **Swap work stays on the swap path** (10-12): the changes made for swaps after the batch had reached every film, and the films got worse (1.3). Changes made after the approved swap films (a photo of every real person on screen, swapped first frames only from the brief's photo list, a prompt read as a swap without its flag, a narrower remake rule) were dropped.

### 9.7 Map shots

- Moving-camera map shots go to the engine; H3 paints only still-camera map shots from a real map. Evidence: the documentaries rated 8 used H3-painted maps from real map stills; a fully H3-painted Hannibal film had territories all over the place.
- The map is timed to the film's own recorded lines, and every map plan starts as a copy of a reviewed film's states (6.3).
- One choreography session for all sections, Sonnet 5.5 at medium. Evidence (10-11): the Hannibal film's map stages went from $1.76 to $0.58.
- The map takes its card's look: toy, satellite only on the satellite-map card, as the approved Hannibal (v48) was made. Evidence: the planner's own pick of style and colours (10-11 night to 10-12) made no film that was liked, and toy looked much better than paper (10-12).

### 9.8 Sound

The mechanics are in section 4. The decisions:

- Magic Hour voices by default (since 10-07, at Magic Hour's request), a preset per on-screen character, every voice in its line's language (10-11: Hindi read by English presets came back as gibberish).
- Read tails trimmed (10-09: tails pushed a 13-line film 2.4 s late); a run of one recording cut and normalised once (10-11: 13 bites of one scene had silences and level jumps).
- One fixed gain to -16 LUFS without effects; effects at the speech's level, under lines (10-11: a final loudnorm sagged the music 2 dB; effects at one loud peak stood out; kept to the gaps they pushed lines).
- Seams into pauses inside the one call; every line counts, the user's own too (if no seam fits, only ours); a swap counts only our own lines (4.9).
- Generated music by default, the user's track when given, starting at its strongest part (10-09: edits played their song's quiet intro); no music catalogs or platform music APIs (platform APIs add music only when posting; catalogs need licensing deals).
- A video or music file with no sound gives a silent soundtrack instead of stopping the film (10-12); a file with sound is used exactly as in the batches (checked: the same soundtrack, byte for byte). A bed shorter than the film is padded on the swap path only.
- Frame-exact cuts on the film's grid (10-09: per-clip `-t` drifted 0.3-0.6 s over 28 clips); the exact length is target to target + 0.45 s, which a player shows as the target.

### 9.9 Render settings

- Magic Hour's production graph, unchanged: `res_multistep`, scheduler `simple`, 25 steps, the T8 block cache at 0.12, the pruned int8 model, the nvfp4 text encoder (5.3). H3's official settings (50 steps, full bf16, no cache) were not better and 3.5x slower (10-04); on the same seed, full bf16 and no cache looked nearly the same (10-03): the seed decides the take. This graph on our GPUs matched fal on the locked launch film (10-03).
- The two additions: sound held fixed and pins (5.5).
- No prompt enhancement of any kind (9.2 rule 5).
- Every H3 clip renders span + 0.3 s; footage at 360 rows (480 at 720p and up) with no stills; style and motion clips at 360 rows, silent.
- RTX PRO 6000 first, then B200; idle shutdown after 30 s. Why (10-06): about $0.90 a film against $1.40 on B200s.
- Text gets steadily sharper with more rows, with no threshold; the tiers are 480, 704 and 800 rows (10-01/10-02).

### 9.10 Settings that only cut cost, checked not to change films

| Setting | Where | The check |
|---|---|---|
| 5-minute prompt cache, no session-title call | `CLAUDE_CODE_PROMPT_CACHE_TTL=5m`, `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1` | billing only: a captured request was identical (10-10) |
| The producer without connector tools | `PRODUCER_LEAN` | production never has those tools (10-10) |
| `storyboard` and `make_soundtrack` calls side by side | `readOnlyHint` in `mcp.mjs` | the same outputs; one-by-one batches had outlived the cache ($2.44 over 8 films, 10-11) |
| Launch films read `CASTABLE-index.md` and skip the Orchids clips when the card has its own example | `LAUNCH_INDEX`, `LAUNCH_EXAMPLES` | blind picks, 10-10 |
| A montage is one `EDIT.json` | `build-edit.mjs` | byte-identical clips on 87 of 87 (10-10) |
| The session ends once the film is whole | `planner-stop.mjs` | it also lists every missing file (10-10) |
| Every H3 clip renders span + 0.3 s | render-all (`EDIT_TRIM`) | side by side, the same or a little better; trimmed launch films looked fine (10-10) |
| Footage with no stills at 360 rows (480 at 720p and up) | render-all `footRows` | the edits looked the same at 720p (10-10) |
| A zoom shot at H3's smallest length | render-all | 13 same-seed renders matched their footage as before (10-10) |

### 9.11 Tried and rejected

Do not bring these back without new evidence.

| Area | Tried | What happened | When |
|---|---|---|---|
| Planning | The Gemini 3.8 Flash planner (it planned every film before 10-09, the locked launch film too) | Sonnet 5.5 about as good, twice as fast, no Google Cloud; its runtime also cut prompts at 192,000 bytes without a word and dropped tool calls at 3 minutes | 10-09 |
| Planning | GPT-6.1 Sol as producer and planner | slower on every painted request (8-18 min against 3-5), not reliably cheaper; its quality was never judged in fully fair pairs | 10-10 |
| Planning | Medium thinking for painted films and edits | worse on 4 of 6 films; last on both edit rows | 10-10 |
| Planning | Re-render loops, best-of-N takes, review-and-fix rounds, a best-take picker | 28 renders for one 4-clip film; the rounds never settled | 10-09 |
| Planning | `check_prompt` on painted films | only false flags; planners weakened their motion to pass | 10-04 |
| Planning | Long rule piles in tool text | no gain | 10-03 |
| Planning | `render.json` and `NOTES.md` written in the same batch as the prompts | loses the last request, where 3 of 31 planners caught their own slips | 10-10 |
| Planning | Films built in code (HTML screens and GSAP) instead of H3 | broken beats; never beat the v13 film | 09-25 |
| Producer | Researching a format from tutorials or before-and-after demos | the film came out plain | 10-11 |
| Producer | Rules first, request last (`PRODUCER_STATIC_FIRST`) | changes what the producer reads, for about 3 cents | 10-10 |
| Producer | Telling the planner how the film is funny | a pun script | 10-10 |
| Producer | A speech-to-text cache shared across films | saves nothing: within a film only `user_video` transcribes footage | 10-10 |
| Prompts | A prompt rewriter (MiniMax's or fal's) | dropped timings and framings; worse motion | 09-08, 09-17, 09-30 |
| Prompts | "Not X" and "nothing of X remains" clauses | the same film as positive wording | 10-12 |
| Prompts | Camera verbs and waypoints | ignored | 09-15 |
| Prompts | Size words for text; "return this image unchanged except…" to enlarge text | worked only sometimes; the layout and the small text held | 10-01 |
| Stills | Character stills by default; sample frames from one film | the character became the lead; that film's palette carried over | 09-12 |
| Stills | A style reference video on painted films | H3 copied its subjects | 10-05 |
| Stills | A font specimen sheet as a reference | it became a scene | 09-17 |
| Stills | A design still cited on every row | every clip restarted from it | 09-30 |
| Stills | Fresh drawings of one place | seven drawings, five gates | 10-09 |
| Stills | Product stills drawn fresh; a keep-list naming a background | raw screens and a new diagram per clip; the app shrank to an island | 09-29 |
| Stills | One batch image call drawing every still | each still drawn with no references: three different diagrams | 09-29 |
| Stills | A 16-item ban list | flashed on screen | 10-04 |
| Clips | Hold-to-hold seams, frame-mode bridges, crossfades, override lines | broken seams; overrides ignored | 09-17 |
| Clips | The previous clip's tail as a reference; an iris or wipe at a clip start | a dimmer seam, replayed entrances; an iris opened out of a reference picture | 09-30 |
| Clips | Frame mode (exact first and last frames) | no reference audio possible: silent films; pins replaced it | 09-14 |
| Render | H3's official settings (50 steps, full bf16, no cache) | not better, 3.5x slower | 10-04 |
| Render | Upscalers (SeedVR2, Topaz) for small text | sharper edges, letters still wrong | 09-18 |
| Render | Retaking clips that came back boxed | the cause, wide footage sent uncropped, was fixed at the input; boxed clips are only logged | 10-09 |
| Footage | One H3 clip cutting between several videos; pins at cuts inside a clip; long footage clips (`FOOT_GROUP=1`) | cuts off the beat (up to 0.5 s; two cuts 5-9 frames early), repeated moments | 10-09, 10-10 |
| Footage | Holding the footage inside H3 (`H3_FOOTAGE_MODE`) | the footage stayed real, but none of the asked effects were drawn | 10-09 |
| Footage | Every short shot at H3's smallest length (`FOOT_GRID=1`); footage pre-zoomed or left out on zoom shots; an optical-flow follow crop | 0.6% less GPU for more frames off their footage; the follow crop was worse over whole films (the centre crop stays) | 10-10 |
| Footage | A first-frame pin and fill crop on a footage clip with stills | the caption was dropped | 10-10 |
| Footage | A 2 s floor on footage renders | a 0.88 s render matched its footage as well, for half the GPU | 10-09 |
| Footage | Fan edits at 9:16 | cropped the action | 10-10 |
| Footage | Dialogue bites running on past the cut | two test rows were better before | 10-11 |
| Swaps | One long clip; one clip per shot; negative wording; Magic Hour's face swap API | the person melted back; more slips; no change; deferred | 10-12 |
| Swaps | A movie scene sent to H3 to be redrawn with someone new | the real actors stayed | 10-12 |
| Sound | One loudnorm pass over the mix after the effects | music about 2 dB down | 10-11 |
| Sound | Effects kept to the gaps between lines | they pushed the lines | 10-11 |
| Sound | The sound as a reference only (`H3_AUDIO_MODE=reference`) | H3 re-spoke the voice: 59-92% word errors | 10-08 |
| Sound | A 1 s lyric lead | lead 0 was better | 10-08 |
| Sound | Music catalogs and platform music APIs; allin1 beat analysis | licensing; no audible difference from madmom | 10-08 |
| Maps | The planner picking the map's style and colours, the map leaning 35% toward them (no film made with it was liked, 10-12); the film's look as the map tint; a flat explainer map style; paper on a parchment card; an accent colour | restyled the cut-outs; looked like paper with messier text; toy preferred; hid routes | 10-11, 10-12 |
| Maps | One choreography session per section with two whole example films | $1.76 of map stages against $0.58 | 10-11 |
| Services | YouTube Data API search; Nano Banana on Vertex; B200 first | ran out at about 100 searches a day; refused every request since 10-09; dearer per film | 10-10, 10-09, 10-06 |

## 10. Quality levers

In order of how much they move the films:

1. **The library: what the planner and H3 are given to copy.** This is the biggest lever. Planners copy what they are shown (in seven launch sessions about 233 phrases came only from the card's example film), so the examples set the ceiling. The library is:
   - the style cards, `agent/web/app/styles/cards/<id>.md`: the style sentence, the job line with the "everything in this style" clause, the sample frames and the rule for picking them, design stills, the MOTION block, Storytelling, and the approved example film (`refs/<id>/example/`: its plan and every clip prompt, pasted whole; 57 cards have one). Each card was frozen at the exact text that made its example;
   - the sample frames, `refs/<id>/pool/` with a labelled sheet in `refs/<id>/sheets/`: from two or more films, no faces or text unless that is the style; four style clips (`refs/<id>/clip.mp4`) for the styles whose look is their motion;
   - the use-case files, `skills/h3-film/usecases/` (21): how each kind of film is told, its length and its frame;
   - the launch material: the Magic Hour v13 and Orchids example films (`agent/h3film/exemplars/films/`), the component rows (`agent/h3film/library/shapes/`) and their motion clips;
   - the six example runs for tutorials, event promos, logos and lyric videos (`agent/runs/`);
   - the voices (`research/h3/voices/`) and music beds (`agent/music/`);
   - the scores (`ratings.json`, `best-takes.json`) by which the producer prefers a proven style.

   How the good parts were made (10-05/10-06): one approved film per style, rated 8 or more and planned with the best setup at hand at the time (most by Opus 5.5 or the Gemini planner; production plans on Sonnet 5.5), with the card frozen at the text that made it. A genre H3 knows by name gets one sentence naming it plus 3 to 8 frames; a house look gets 12 to 24 frames from two or more films; a look that is its motion gets one clip of at most 14.5 s. The library was put together quickly. Where it is thin: no map style has a film at 8; music films are the weakest group; the animated chart section has no cards at all; sports edit, fan edit, storytime, action short, viral short and space epic have no film rated 8 or more. The internal library page (linked at the top) shows every style, example, voice and setting.
2. **The stills H3 is shown.** The still is the design: design stills for every recurring character and object, product screens as hero edits, words as type stills, pins of one place from one master picture. When a description fails twice, change the still.
3. **The producer's research.** It watches the real thing (`kit.mjs` frame sheets) and hands the planner what it saw; a named format is its most viewed real example.
4. **The soundtrack.** Made first, held fixed in H3, voices that fit who speaks, mixed as in 4.8.
5. **Planner effort by kind of film** (1.3, 9.2 rule 19).

The first experiment worth running: MiniMax's own reference-prompt layout and the node's `<Picture N>` tags (3.10) on each other kind of film, one kind at a time against our prompts (`TAGS=all` turns on the tags). Only live-action swaps use them today.

## 11. Known problems

### 11.1 Open problems for production

- **YouTube blocks server downloads.** Fan edits, sports edits, recaps, memes and lyric videos depend on yt-dlp. Give it a signed-in account's cookies and keep it updated, or use licensed media (7.2). Only `fetch.mjs get` turns the bot check into a clear stop.
- **Captions in non-Latin scripts** need fonts and text shaping off macOS (4.13). Emoji are empty boxes everywhere.
- **iPhone HDR videos** probably come out washed out: nothing converts HDR to SDR (not tried with a real iPhone clip).
- **Keys reach the model-run shells.** `.env.local` is loaded into the environment of the producer (which has a shell), launch planners (which keep a shell) and the map stages (shell), and every planner's Read tool can reach the repo folder, `.env.local` included. Run the sessions in a container, and in a rebuild give keys only to the tools (12).
- **No time limit on a planner session.** The producer is killed after 30 min and each tool call answers "call again" after 1,750 s, but a planner session can run without end; nor do the map stages have a wall-clock cap.
- **Pieces fetched at run or build time, some unpinned**: HyperFrames through npx (fixed versions, but downloaded at run time); the Modal image's KJNodes, T8 and VideoHelperSuite at their latest commit, T8 patched by text replacement that fails silently if the line changes; the Hugging Face weights at `main`; madmom as a development build; yt-dlp, which must be kept current.
- **Films write into the repo and share caches**: studied looks become cards in the shared cards folder (two films starting at the same moment could pick the same new id); launch films rewrite `CASTABLE-index.md`; downloads, kits and pictures are cached by link or by file name and size, shared by every film and never cleaned. In a service these belong with each film.
- **Disk**: caches grow without limit and nothing checks free space.
- **Linux**: the server image (7.7) made a launch film on GitHub's x86_64 Linux on 10-12; no drawn film, footage edit, swap or map film has run there yet.

### 11.2 Weak spots in the films

- **Map films.** None is rated 8 or more; the best scored 7. Two Hannibal takes failed in the map stages. The map job takes 6-13 min and adds to the film's time; any failure in it fails the whole film. On 10-08 the map scripts read like an encyclopedia next to the proven films' talk, and the 30 s default is short for the proven story shapes (60-100 s); not judged again since `map-video.md` gained its talk rules. Russia could not be painted by the engine on 10-08 (its mainland filter dropped the outline); not re-checked.
- **Music films are the weakest group**: m2 6.5, m1 7, m3 7. The sing-along's voice scored 6 to 6.5 (m6); a better one is not picked yet.
- **Swaps of real people**: still weakest in tight close-ups of very famous faces, where H3 copies the filmed face back from the footage over a few seconds; H3 changes outfits and hair before faces and skin. A face swap of the footage before H3 is the untried next step.
- **Open items from the last batch**: podcast flashes never appear; the trailer for an unreleased film (x04) fetched pictures of only two of its characters; a Peter Griffin film repeats its one 28 s source clip.
- **From the 10-10 batch**: "_ core" edits (a person's savage moments, one sound effect between clips) not understood; muted stretches in two films; a reference video's intro story missed; a parchment look for a WW2 battle; a gaming intro made without studying real ones; a pillow flips and a phone vanishes; lips moved to an off-screen speaker (a rule was added on 10-11). A bike edit with 3D lyrics is parked (5.5 and 7).
- **Older open issues**: paper collage fails on object topics; bold flat poster fails on a story about people; launch films share their moves and endings; a whiteboard does not stay the same board; dark products come out light; notepad lyrics run off the page; studied looks lean on words placed in the scene, which H3 garbles.
- **No film rated 8 or more yet** in: animated chart (no cards at all), action short, storytime, sports edit, fan edit, viral short, space epic.
- **The same request gives different films**: the planner writes something new each time and every render draws a new seed.
- **Long single shots across clip seams** render their clips one after another, so those films take longer.
- About 1 clip in 700 comes back with black bars and is only logged.

### 11.3 Gaps found in the code

None of these is known to have spoiled a rated film unless it says so.

- **`CODE_SHOTS=1` crashes the tool server at start**: `VOCAB` (and `Refuse`, `checkStates`, `mapWorkspace`, `mapLook`, `mapPage`, `openEngine`, `landCheck`) are declared inside the block around `code_clip` in `research/h3/tools-codeshot.mjs` and used after it by `map_clip` and `map_stills`. No card turns it on; painted films clear it.
- **Blanks inside a blank are not filled** (`build-edit.mjs`): the template is filled in one pass, so a `{span}` written inside a shot's `rows` stays literal. In one 10-12 test edit, 7 clip prompts went to H3 with "0.0-{span}s — …".
- **The launch write-time check needs the exact string "Software launch film"**: a launch planner that opens a prompt with its card's style sentence instead ("Airy minimal software launch film" on a 10-12 test) gets no write-time check or length report. The stop hook and render-all still check every launch clip.
- **Frame mode is described but refused**: `PAINTED.md` §6 and the `system-diagram` card describe `first`/`last` clips for a film with no narration or music; render-all refuses them. Films from `./film` always get a soundtrack, so this should not trigger.
- **A footage shot with `frame` and no stills**: its zoom pins are cropped at (x, y), but `comfy_r2v.py` centre-crops its Video 1 to the film's shape (render-all's comment says H3 gets the whole shot).
- **When one clip fails**, render-all exits, but the other `comfy_r2v.py` processes keep running and write their clips with no key file; a retry started at once can render those clips a second time.
- **Nothing checks** that `parts` add up to `duration`, or that `render.json` spans equal the returned parts (4.9).
- **Map shots in frames other than 16:9 and 9:16** get 16:9 map clips, and the join stretches the other clips to 1920x1080; H3 clips in any map film are stretched about 2.6% across (6.9). A map clip whose narration is a piece of a real recording has no `vo-<n>.mp3` of its own, and the alignment would fail.
- **Narration captions need `soundtrack.json`**, which only painted films get; launch films silently get none. A `from` line with no text would be captioned as its placeholder; use speech captions for real recordings.
- **`song` with no lyric ids starts at 0 s**, although the tool text says a song with no `song_start` starts at its strongest part. Song mode silently ignores `lines`, `effects`, `music` and `music_prompt`. Seams off the beat are reported only in song mode.
- **The producer's style scores are old**: `[proven N]` comes only from the Gemini-planned style tests of 10-05 to 10-08 (runs named `h3film-gem*`, `h3film-fgem*`, and `best-takes.json` entries with mode `gemini`), and `catalogue()` reads only `rating`, while the newest entries store `score`. Styles behind some of the best recent films (`fruit-sensory` 9.5, `scale-3d` 9, `raise-beast` 8.5) show as `[untested]`, while the prompt says to prefer proven styles.
- **The larger kits understate what was studied**: `kit.mjs` counts the seconds seen from the frames it kept for the sheets, so the kit text's first line can say "you see its first 68 s only … not the other 19 s" for a video studied whole (the cuts and words cover the whole first 150 s).
- **A lyric video with a set length other than 30 s** gets a brief that says both "duration=30" (the hard rule) and "Length: <N> s"; the tool refuses 30 and the planner calls again.
- **`--dry` and `--plan` are not what their names suggest** (2.2).
- **`watched` and `speech`** are required answers that no code reads.
- **`RESUME`** is listed in `.env.example` and recorded by `manifest.py`; nothing reads it. `@@<name>` shared blocks are understood by the hooks but never expanded before rendering.
- **Launch sessions keep Bash** while their prompt says there is none.
- **`storyboard`'s `ground` and `H3_ACCURACY=ground`** do nothing on the default fal route.
- **The render cap and `spend.json`** are priced as on fal, not as GPU time.
- **`still`'s `spot` room** paints flat (its CSS gradient is not valid). `SKILL-gemini.md` tells planners to pass `fit=bleed` for a full-frame picture, a field the tool does not have; the field that fills the frame is `room: "none"`.
- **A failed preset voice stops the film**; a failed clone falls back to ElevenLabs. Music is generated after the voices and effects, ElevenLabs reads run one by one, and each clone uploads its sample again: steps that could run side by side do not. The bed's level is set from the mean volume of the whole source file, not the window used.
- **Two 10-12 test runs ended with no film and no traced cause**: one when the tool server's connection closed during a Spanish `make_soundtrack` call, one when the session stopped mid-thinking.

- **Left out on purpose (10-12)**: fixes made after the approved films that change films that work. They stay out so every film runs exactly what made them (1.3). Each fixes a real case; add one back at a time, with its test (8.2). Their code is in this repo's history (`git show df63897`, `git show 5755047`):
  - speech and narration captions kept to their own `from` and `to` (render-all; a replay of the 12 past films with such captions: 11 the same, the 12th lost a closing song's 36 sung words drawn as speech);
  - seam sums rounded to 0.01 s (`soundtrack.mjs`; a sum of 40.12 came out as 40.120000000000005 and put a seam just inside a line);
  - a song, or a bed outside the swap path, padded when shorter than the film;
  - in edits, the footage's own speech never moving a seam (the swap path has it);
  - `language` for launch films' `make_soundtrack` (`mcp.mjs`);
  - a character picture that cannot be fetched named in the brief, and names past the 8th picture logged (`auto.mjs`).

### 11.4 Out-of-date text in code and instructions

These stay as they are because the best films were made with them; a planner-facing change needs a test.

- `auto.mjs` comments: the film "runs as run-gemini-pass.sh runs one card" (not in this repo); "the one Gemini call sorts what has no category" (the producer session does); render-all refuses `attached/` files sent to H3 (since 10-12 it sends the user's photos in live-action films; only `generate_video` still refuses them); "The producer writes the lines" (the planner writes every word); it names `agent/h3-style-claude.sh` (not in this repo).
- `claude.mjs` says the calls "ask Claude Haiku 5.5 instead of Gemini" (the producer names Sonnet 5.5).
- `tools-footage.mjs`' header says `user_video` is registered only with footage (it is always registered); `web_clip`'s description says up to 8 results (it returns all).
- `SKILL-gemini.md`'s front matter says the session renders on fal and joins (§6 forbids it), its §4 says Nano Banana only cleans captures (the image tool's rules are what planners follow), and its §5 and `references/index.md` point to `framework/components/<id>.js` (not in this repo). `still kind=screen` needs ingested screens this repo has only for Orchids.
- `PAINTED.md` §1 lists 7 use cases (21 exist). The `MINIMAL=1` note says PAINTED.md is pasted (it is not). The run lines say "NO Bash" to launch planners, who have it.
- `skills/h3-film/usecases/lyric-video.md` still says `make_soundtrack` is not called and that a user's song cannot be used (the brief's hard rule is what planners follow). `skills/h3-film/references/music.md` mentions an `agent/music/vo/` folder that does not exist. `make_soundtrack`'s text still calls the reads "ElevenLabs narration lines".
- `map_shots` says the map takes 30-50 minutes (6-13 on Sonnet). `code_clip` names the search tools by older names.
- `modal_h3.py`'s header says "B200 first" (the code asks for an RTX PRO 6000 first). `comfy_r2v.py`'s comment gives the reference-video canvas as 1280x704 (ComfyUI v0.36.0 computes 1344x768 for 16:9).
- `.env.example` lists `RESUME` (read by nothing), and among the names set by code `AGY_CLI_DISABLE_AUTO_UPDATE` and `V2_SLUG` (set by nothing). `tools/pages/README.md` says the library builder needs nothing outside the repo, but its `inventory.py` reads `RUNS`.

### 11.5 Not measured or untested

- Whether Claude Code's own default system prompt, in front of every tested planner, matters to film quality (a rebuild on the raw API would not have it).
- Lyric videos plan at medium effort since 10-11, but the two best lyric films (m4 9, m5 8) were planned at high, and every lyric take planned at medium since (all following a given video) scored 6 to 7.5. No same-request comparison exists.
- Whether the producer would do better at high effort; whether its old style scores steer picks badly; whether `watched` and `speech` change the briefs.
- `PAINTED.md`'s render.json template asks for a pin where each shot opens, but the top painted films used one composition per clip and no pins; whether pinning every one-shot clip helps or hurts is untested.
- Magic Hour voices became the default at Magic Hour's request; no side-by-side with ElevenLabs was found.
- Whether H3's text encoder truncates very long prompts (20,000 characters is Magic Hour's text-to-video cap; nothing enforces it on painted or footage prompts).
- Peak VRAM at each tier; render time at 800 rows on this graph (extrapolated); whether the nvfp4 text encoder runs (more slowly) or fails before Blackwell; SageAttention built for a B200; the commits of KJNodes and VideoHelperSuite in the deployed Modal image; whether Modal retries a preempted call; whether the same seed gives the same clip on another GPU type; whether a mono soundtrack part works.
- ElevenLabs Music's shortest and longest allowed length against the 4-120 s range; which model the sound-effect endpoint uses; what forced alignment, sound effects, speech to text and map cut-outs cost per film (not counted).
- Whether Magic Hour's uploads arrive with a reference category (as `--ref` assumes) or as plain files the producer must sort.
- How the producer behaves when its media commands are separate tools instead of shell lines.
- Whether `CLAUDE_CODE_WEB_SEARCH_FAST_ARG=0` still changes web search in newer Claude Code versions (it is not on the public settings page).
- Map pages on a Linux server without a GPU (software WebGL); whether `map_prep.py` reproduces the tracked `geo.json` exactly.
- Why `code_clip` renders at two-thirds of the full frame (likely render time); whether the HyperFrames 0.8.2 pin for stills and code clips is deliberate.

## 12. Licensing and security

**Licensing** (review all of these before this ships inside a product):

- Background removal: rembg's default model here, BRIA RMBG-2.0 (`bria-rmbg`), is for non-commercial use; commercial use needs BRIA's agreement or another model passed as a rembg session (`remove(img, session=new_session('<model>'))`; no other model has been tried for quality). It runs in the `image` tool's cut-outs and in the map cut-outs. rembg itself is MIT.
- Material from other companies and creators, sent to H3 and Nano Banana: the style sample frames (`agent/web/app/styles/refs/<id>/pool/` and their sheets) are frames of other creators' videos; the four style clips are cut from other companies' films; the launch motion clips (`ingest/<film>/run/*-ref.mp4`, `research/lab/run/*-ref.mp4`, `agent/h3film/library/proven/`, `ingest/blossom/reference.mp4`) are cut from real launch films (Orchids, Blossom, GoConfirm, beehiiv, Ghost Note, Chatbase, Framer, Wix); the product packs in `agent/refs/` hold 17 brands' logos and app screenshots; a look the producer studies copies frames of the studied video into `refs/<id>/pool/`.
- Downloads: footage, songs and frames of real videos come through yt-dlp from YouTube, TikTok, X and Instagram, under those sites' terms and their owners' copyright; synced lyrics come from LRCLIB. For production: licensed media or the user's own uploads.
- Also to review: official character pictures fetched from the web and attached to H3 as designs; photos of real people fetched for live-action swaps (likeness rights); Magic Hour's celebrity and character voice presets chosen for on-screen characters; the four clone samples (reads by ElevenLabs voices, cloned on Magic Hour); the five library music beds (archive.org sources in `agent/music/INDEX.md`, licence not recorded); map data and textures (NASA Blue Marble and Natural Earth are public domain; the Copernicus DEM needs attribution; the historical-basemaps borders, the textures and the Kenney props are marked CC0 in the code but not confirmed here); scripts loaded at render time (three.js, Tailwind and d3 are MIT or ISC; GSAP's terms were not checked); fonts (Inter and the Google Fonts families, mostly SIL Open Font License).

**Security:**

- Run films in a container. The producer, launch planners and map stages run shell commands the model chooses, with permission prompts off and no sandbox, after reading web pages. Painted planners have no shell but can read any file in the repo. Today every Claude session inherits every key in `.env.local`; in production, give keys only to the tools (the tool server already reads its own) and keep the sessions' environment free of them.
- `npm audit` on 10-12: `research/h3` 4 findings (1 critical in `proxy-addr`, 1 high in `@modelcontextprotocol/sdk`, 2 moderate), `agent` 6 (1 critical, 2 high, 3 moderate), the repo root and `research/h3/codeshot` none. Update them before shipping.
- Run folders hold users' uploads. Never commit `.env.local` or `agent/runs/`.
