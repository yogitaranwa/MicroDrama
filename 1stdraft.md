# MicroDrama script generator - 1st draft plan

Date: 13 Oct 2026. Status: research and plan only. No notebook changes and no API calls were made for this document.

## 0. How to read this

- "Read" means I opened the file or page. "Run" means executed. I ran nothing.
- For the three repos you named I read the file list, the license, the README and the specific source files listed in section 3. I did not read every file.
- Other repos: README only. Papers: abstract only. What a method achieves is the authors' claim, not tested by us.
- The earlier plan.txt is outside evidence. Its claims on hook libraries, credits and prices were not re-checked here.
- Nothing below is a promise of error-free scripts. Our live tests so far have no accepted episode.

## 1. Where we are

- One Colab notebook, edited in place (v9) with a README, in the MicroDrama Drive folder.
- On your NVIDIA key and route, the only model we have called is nvidia/nemotron-3-super-120b-a12b. Its API calls returned responses (13 generation calls in testing), but no episode has passed the full checks, so this is evidence the route answers, not that the writing is good.
- The first bible and outline changed your story (ending, phone mother, early reveal). They were kept as rejected files and are not reused.
- v9 adds: error-specific retries, offscreen phone voices, faithful vs seed mode, original-quote checks across the series, and an outline review before episodes are generated.
- 500 DramaBench rows saved, split 350/99/51. Retrieval is off. No fine-tuning.
- Live testing is paused on one question: is your NVIDIA key on the free build trial or a paid account?

## 2. The main finding

REA (morluto/rea) is a reverse-engineering tool for binaries, apps and websites. It is not a story tool. It shows client-side code and network calls, not a service's hidden prompts or model weights.

What you meant is better: study a working open-source system and build on its approach. Of the three repos you gave:

| Repo | What it really is | Fit for our generator |
|---|---|---|
| yoligehude14753/dramaker | Idea to bible, characters, episode outline, scenes and dialogue, then video | Closest. Borrow the scene-by-scene writing structure |
| Forget-C/Jellyfish | Takes an existing script and breaks it into shots, entities, consistency checks, generation tasks | Borrow the entity model, JSON repair, consistency check. It does not write scripts |
| IIIIQIIII/DramaBench | Evaluation prompts, dataset pointer, demo site | Borrow as a judge and test set. It does not write scripts |

None ships trained model weights that I could find in the file lists. dramaker and Jellyfish contain real code that their authors describe as running pipelines. I did not run either, so I cannot say they work end to end. Both are server applications (see 3.1 and 3.2), so running one whole is a separate setup from our Colab notebook. DramaBench is prompts, data and a demo. For our notebook the realistic route is selective adaptation of prompts and design, not running their stacks. Whether to run one of the stacks as a trial is a separate option, not tried.

## 3. What I actually read

### 3.1 dramaker (https://github.com/yoligehude14753/dramaker)
- Read: file list, README, pyproject.toml, src/agents/script_writer.py, src/agents/quality_checker.py, test file names and test_model_quality.py names.
- Stack: Python 3.10+, FastAPI, Celery, Redis, FFmpeg, React frontend, Docker. Marked Alpha, one release (v0.1.0, 27 Mar 2026).
- License: I found no LICENSE file in the repo's file list. pyproject.toml declares `license = { text = "MIT" }`. A declaration without the license text is weak. Adapting ideas is safe; copying code verbatim should wait for a LICENSE file or the author's confirmation. If MIT is confirmed, keep the copyright notice and license text with any copied code.
- Entry points (from the README run commands): `uvicorn src.main:app`, `celery -A src.worker worker`, a React frontend, or `docker compose up`. Needs Python 3.10+, Redis, FFmpeg, Node 18+.
- Dependencies (requirements.txt): fastapi, uvicorn, pydantic, celery, redis, requests, httpx, python-docx, Pillow, ddgs, trafilatura. Text model is configured through OpenAI-compatible `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL` in .env.example (so an NVIDIA OpenAI-style endpoint could in principle be pointed at; not tried).
- Source: https://raw.githubusercontent.com/yoligehude14753/dramaker/main/src/agents/script_writer.py
- Script writing, as coded: one call plans 3 to 12 scenes for an episode from the episode synopsis, hook and cliffhanger. Then one call per scene writes lines. Each line has character, emotion, background, dialogue, action, camera and a duration hint. The prompt asks for short spoken lines, 20 characters max, and an emotional change every 2-3 lines.
- Prompts are in Chinese.
- Not seen: any check that the output keeps a user's story, any quote check, any running canon across episodes. Its tests check tags, line counts and non-empty fields, not story quality.
- Not read: world_builder.py, deep_researcher.py, video and assembly engines. Authors claim full MP4 output; I did not verify it.
- QC file is an image checker (vision model on generated images), not a script checker.

### 3.2 Jellyfish (https://github.com/Forget-C/Jellyfish)
- Read: file tree, README, backend/app/chains/agents/consistency_checker_agent.py, script_divider_agent.py (size and role), base.py (JSON handling).
- License: Apache-2.0 (LICENSE file present in the repo). If we copy or adapt code: keep the license and copyright notices, mark files we changed, and keep any NOTICE file if present (I did not check for one).
- Entry point: backend/app/main.py (FastAPI), managed with uv, Python 3.11+. Dependencies (backend/pyproject.toml): fastapi, uvicorn, langchain, langchain-core, langgraph, sqlalchemy (async, SQLite default per its backend README), celery[redis], httpx, boto3, pydantic-settings and others. A separate web front end and Docker images exist.
- Sources: https://raw.githubusercontent.com/Forget-C/Jellyfish/main/backend/app/chains/agents/base.py , https://raw.githubusercontent.com/Forget-C/Jellyfish/main/backend/app/chains/agents/consistency_checker_agent.py , https://raw.githubusercontent.com/Forget-C/Jellyfish/main/backend/app/chains/agents/script_divider_agent.py
- Stack: Python backend with LangChain-style agents, database, Docker images, web front end. Heavier than a notebook, so reusing it directly would be a separate setup (not tried).
- What it does: input is an existing script. Agents split it into shots, extract characters, scenes, props and costumes, simplify or optimize text, and check consistency. Then image and video tasks run through a task queue.
- Useful for us: (a) the entity model of characters, scenes, props, costumes shared across shots; (b) base.py repairs messy model JSON (removes code fences, quotes bare keys, removes trailing commas, falls back to Python-literal parsing) before validating against a schema; (c) a consistency agent that flags one character given different identities in a script.
- It does not generate scripts. Prompts are Chinese.

### 3.3 DramaBench (https://github.com/IIIIQIIII/DramaBench, dataset https://huggingface.co/datasets/FutureMa/DramaBench)
- Read: file tree, README, prompts/README.md, prompts/character_consistency_prompt.txt, the demo continuation prompt template, scripts/load_dataset.py (head).
- License: MIT (LICENSE shown by the repo page; the dataset card also says MIT). If we copy prompt text, keep the MIT notice and credit.
- Entry points: `start_demo.sh` and `web/demo.html` for the demo site; `scripts/load_dataset.py` loads the dataset from Hugging Face (needs the `datasets` library).
- Sources: https://raw.githubusercontent.com/IIIIQIIII/DramaBench/main/prompts/character_consistency_prompt.txt , https://raw.githubusercontent.com/IIIIQIIII/DramaBench/main/web/data/demo/drama_continuation_prompt_template.txt
- In the repo: six LLM scoring prompt files (narrative efficiency, character consistency, emotional depth, logic consistency, conflict handling, dialogue quality), a continuation prompt template, a dataset loader, a demo web page, leaderboard data, case studies.
- Not in the repo: the scoring pipeline itself, and the rule-based format checker (the prompts README says it is not included). Leaderboard numbers are the authors' results.
- The task is continuing an existing screenplay, not writing connected episodes of a series.

### 3.4 REA (https://github.com/morluto/rea)
- Read: README, LICENSE (MIT), project site. Not run. Needs Node 22+.
- Best case: inspect how a public app's front end calls its services. Cannot recover hidden prompts or weights. Terms-of-service and copyright risk on commercial apps. Low value for this project.

### 3.5 Other sources (README or abstract level only)
- 0xsline/short-drama (MIT): markdown skill files with five hook types, a pacing curve, a 1-10 scoring sheet. Opened SKILL.md and hook-design.md. No program code. Chinese. Quality unaudited.
- One Sentence, One Drama (arXiv 2605.22144): debate-based story agents, reviewer loops. Abstract only.
- Decomposed screenwriting (arXiv 2510.23163): separate prose drafting from screenplay formatting. Abstract only.
- DOC (arXiv 2212.10077, repo MIT) and Re3 (arXiv 2210.06774): outline control and revise loops for long stories. GPT-3 era code.
- SkyScript-100M (arXiv 2408.09333): large short-drama script data built from collected web videos. We have no access. Do not plan around it.

## 4. Model facts (checked 13 Oct 2026)

- nvidia/nemotron-3-super-120b-a12b: the only model called so far on your key (13 generation calls; responses returned, no accepted episode). It is the current setting, not a decision that it is best. Choosing the best writer and judge needs a comparison on our test briefs, which has not been done.
- meta/llama-3.3-70b-instruct: text model, but build.nvidia.com lists its free endpoint as Deprecated, and a NVIDIA forum post (22 Sep 2026) reports HTTP 410 and end of life on 26 Aug 2026. Not usable on the free route as far as we can tell.
- meta/llama-3.2-11b-vision-instruct: image-understanding model, free endpoint listed available, visible in your key's model list. Weak fit for long strict-JSON writing. Possible later use: check generated character images against the bible.
- nvidia/llama-nemotron-embed-vl-1b-v2: embeddings only. Cannot write or judge. Only useful if we turn on retrieval, and for plain-text scripts a text embedding model is simpler.
- I did not rank models on quality: no comparison has been run. Treat any claim that one writes better as unverified until tested on our briefs.

## 5. Plan: how we do the work

Principle: keep the notebook, borrow structure, test on a fixed set. Do not rebuild.

### Step 0 - Unblock (you)
1. Answer: is the NVIDIA key from the free build.nvidia.com trial or a paid account? No further live calls until that is clear.
2. Confirm which key goes into Colab Secrets (NVIDIA_API_KEY). The notebook reads it from there.

### Step 1 - Freeze a test set (no cost)
1. Three briefs: your Maya letter and time-loop story, plus two example briefs in other genres that I will propose (you can swap them).
2. For Maya, write down the must-keep facts: letter text, phone mother's line, door open, struck at base of skull, disembodied witness, older Maya from the coat closet, final line.
3. One fixed score sheet (section 6). Same sheet every run.

### Step 2 - Bounded live test (needs Step 0)
1. Run bible and outline only. Read them yourself against the source story in the review step. Approve only if nothing changed.
2. Generate one episode. Record: calls used, failures by type, result.
3. Stop after the bounded number of attempts. Do not loop on patches.
4. Model choice: with the above test set, compare the models your key can actually call, using the same briefs and score sheet, before settling the writer and judge.

### Step 3 - Add borrowed structure, one at a time, each tested on the same briefs
| Change | Borrowed from | Why |
|---|---|---|
| Scene plan first, then per-scene writing, with hook and cliffhanger carried into each prompt | dramaker script_writer | More control over a 60 s episode than one big call |
| Shared entity records: character, location, prop, costume, with fixed descriptions | Jellyfish | Same object reused in every shot prompt later |
| Character-confusion check on the finished script | Jellyfish consistency agent | Catches identity mix-ups |
| JSON clean-up before validation (code fences, trailing commas, bare keys) | Jellyfish base.py | Fewer wasted retries |
| Hook-type and pacing checks | 0xsline/short-drama | Short-drama specific rules |
| Judge prompts for character consistency and narrative efficiency | DramaBench prompts | Repeatable scoring |

Rules for each change: keep our faithful-mode quote check, keep the outline review, change one thing per test, and keep the previous version to compare.

### Step 4 - Judge calibration
1. Run the judge on 5 scripts you have already read and rated.
2. Only trust a judge dimension if it agrees with you most of the time. If not, keep that dimension for human review.

### Step 5 - Later, separate from script work
- Retrieval from reference scripts: only after a test shows examples improve output, and only with licensed text. DramaBench rows are single-script continuation, not linked seasons.
- Fine-tuning: not possible on the hosted NVIDIA route. Would need open weights, GPUs and a licensed series dataset. Out of scope now.
- Video: separate stage, uses the final script. Paid Magic Hour generation stays behind its existing review, rights and code gates.

## 6. Score sheet (start here, edit after your first read)

Score each 1-5, one episode at a time:
1. Fidelity: every must-keep fact present, nothing invented that changes the story.
2. Hook: first shot or line creates a question.
3. Escalation: stakes rise at least once before the end.
4. Ending: lands on the cliffhanger or reveal that was planned.
5. Character voice: each speaker sounds different; no one acts out of character.
6. Continuity: names, places, who is alive, who knows what.
7. Shootability: one action per shot, cast and locations within limits, about 60 s.
8. Format: schema passes with no manual repair.

Pass rule suggestion: fidelity must be 5, and no other dimension below 3.

## 7. Cost and limits

- Text calls on the NVIDIA route: count every call; testing so far used 13 generation calls and 1 model-list call.
- Multi-agent debate would multiply calls per episode. Do not add until single-pass quality is measured.
- No source here shows a method that guarantees consistency; papers describe long-form consistency as still hard.
- Licensing summary, from the repo pages and files: Jellyfish Apache-2.0 (LICENSE present); DramaBench, REA and 0xsline/short-drama MIT (LICENSE shown); dramaker has no LICENSE file in its file list, only an MIT line in pyproject.toml. I did not check the others for NOTICE files. Keep attribution if any code or prompt text is adapted.

## 8. What I need from you

1. Free trial or paid NVIDIA account? (Blocks all live tests.)
2. Which key goes into Colab Secrets.

Everything else (extra test briefs, translating and crediting prompt ideas from the Chinese-language repos) I will prepare as part of the research and show you for review.

## 9. Links

- https://raw.githubusercontent.com/yoligehude14753/dramaker/main/src/agents/script_writer.py
- https://raw.githubusercontent.com/yoligehude14753/dramaker/main/src/agents/quality_checker.py
- https://raw.githubusercontent.com/yoligehude14753/dramaker/main/pyproject.toml
- https://github.com/yoligehude14753/dramaker (repo root)
- https://raw.githubusercontent.com/Forget-C/Jellyfish/main/backend/app/chains/agents/base.py
- https://raw.githubusercontent.com/Forget-C/Jellyfish/main/backend/app/chains/agents/consistency_checker_agent.py
- https://raw.githubusercontent.com/Forget-C/Jellyfish/main/backend/pyproject.toml
- https://github.com/Forget-C/Jellyfish (repo root)
- https://raw.githubusercontent.com/IIIIQIIII/DramaBench/main/prompts/character_consistency_prompt.txt
- https://github.com/IIIIQIIII/DramaBench (repo root)
- https://huggingface.co/datasets/FutureMa/DramaBench
- https://github.com/morluto/rea
- https://github.com/0xsline/short-drama
- https://arxiv.org/abs/2605.22144
- https://arxiv.org/abs/2510.23163
- https://arxiv.org/abs/2212.10077
- https://arxiv.org/abs/2210.06774
- https://arxiv.org/abs/2408.09333
- https://build.nvidia.com/meta/llama-3_3-70b-instruct
- https://forums.developer.nvidia.com/t/nvidia-nim-model-retirements-what-a-410-gone-does-to-a-fallback-chain-and-how-we-survive-it-now/383950
- Research page (private): https://files.instinct.com/cc58dbgrgmv3-script-generator-what-to-reuse
