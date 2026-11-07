"""Builder script to generate MicroDrama_Studio.ipynb notebook."""

import json
from pathlib import Path

notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "colab": {
            "provenance": [],
            "gpuType": "T4"
        },
        "kernelspec": {
            "display_name": "Python 3",
            "name": "python3"
        },
        "language_info": {
            "name": "python"
        },
        "accelerator": "GPU"
    },
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {"id": "title-0"},
            "source": [
                "# 🎬 AI Micro Drama Generator Studio\n",
                "Generate viral vertical (9:16) microdrama episodes with **character reference images**, **dramatic genre templates**, and **Magic Hour API**.\n",
                "\n",
                "### Microdrama Features:\n",
                "- **3-Second Visual Hook:** Explosive opening in media res.\n",
                "- **Character Consistency:** Upload reference images for actors/faces linked via Magic Hour's `references` parameter.\n",
                "- **Trope Templates:** Hidden Billionaire, Revenge & Stolen Identity, Contract Marriage, Alpha Werewolf/Mafia, and Psychological Doppelgänger.\n",
                "- **Sub-12 Word Dialogue:** Razor-sharp, punchy mobile dialogue pacing.\n",
                "- **Cliffhanger Ending:** Unresolved dilemma or shock unmasking.\n",
                "- **Zero-Cost Storyboard Preview:** Review the visual cards & subtitles before spending any video credits.\n",
                "\n",
                "---"
            ]
        },
        {
            "cell_type": "code",
            "metadata": {"cellView": "form", "id": "cell-1"},
            "source": [
                "#@title 1. Install Dependencies & Setup Environment\n",
                "import sys, subprocess, shutil\n",
                "print('Installing Magic Hour SDK and dependencies...')\n",
                "subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'magic-hour>=0.87.0', 'pydantic>=2.0', 'pillow>=10.0', 'jsonschema>=4.20', 'requests>=2.30', 'python-dotenv'], check=True)\n",
                "if shutil.which('apt-get') and (not shutil.which('ffmpeg') or not shutil.which('ffprobe')):\n",
                "    subprocess.run(['apt-get', 'update', '-qq'], check=True)\n",
                "    subprocess.run(['apt-get', 'install', '-y', '-qq', 'ffmpeg'], check=True)\n",
                "print('✅ Environment ready. FFmpeg and Magic Hour SDK installed.')"
            ],
            "execution_count": None,
            "outputs": []
        },
        {
            "cell_type": "code",
            "metadata": {"cellView": "form", "id": "cell-2"},
            "source": [
                "#@title 2. Load MicroDrama Pipeline Engine\n",
                "import os, json, hashlib, time, textwrap, re, requests\n",
                "from pathlib import Path\n",
                "from typing import List, Dict, Optional, Any\n",
                "from PIL import Image, ImageDraw, ImageFont\n",
                "from IPython.display import display, Video, HTML, Image as IPImage\n",
                "from magic_hour import Client\n",
                "\n",
                "ROOT = Path('/content/microdrama_project')\n",
                "ROOT.mkdir(parents=True, exist_ok=True)\n",
                "(ROOT / 'storyboard').mkdir(exist_ok=True)\n",
                "(ROOT / 'clips').mkdir(exist_ok=True)\n",
                "JOURNAL_FILE = ROOT / 'jobs.json'\n",
                "\n",
                "print('✅ MicroDrama Engine helpers loaded.')"
            ],
            "execution_count": None,
            "outputs": []
        },
        {
            "cell_type": "code",
            "metadata": {"cellView": "form", "id": "cell-3"},
            "source": [
                "#@title 3. Choose Template & Configure Episode\n",
                "genre_template = \"Psychological Doppelganger (Do Not Open The Door)\" #@param [\"Hidden Billionaire (Secret Tycoon)\", \"Revenge of the Stolen Identity\", \"The Cold CEO's Contract Bride\", \"The Alpha's Claim (Mafia Don)\", \"Psychological Doppelganger (Do Not Open The Door)\", \"Custom Story\"]\n",
                "story_prompt = \"Sprawled on the entryway mat was a single, unmarked envelope. Maya opened it: 'DO NOT OPEN THE DOOR. The intruder outside is dangerous. They will kill you. - M.' Then the violent knocking began, rattling the deadbolt...\" #@param {type:\"string\"}\n",
                "specific_scenes = \"1. Maya reads the letter; 2. Thunderous knocking rattles the deadbolt; 3. Front door is wide open; 4. Out-of-body twist revealing older Maya with the iron weapon.\" #@param {type:\"string\"}\n",
                "character_reference_image = \"\" #@param {type:\"string\"}\n",
                "# Optional local path to reference image for protagonist (e.g. /content/maya.png). Upload via Colab sidebar if desired.\n",
                "character_name = \"Maya\" #@param {type:\"string\"}\n",
                "number_of_shots = 8 #@param [6, 8, 10, 12] {type:\"raw\"}\n",
                "seconds_per_shot = 8 #@param [5, 6, 8, 10] {type:\"raw\"}\n",
                "video_model = \"ltx-2.5\" #@param [\"ltx-2.5\", \"kling-2.6\", \"kling-3.0\", \"wan-2.2\", \"seedance-2.0\"]\n",
                "video_resolution = \"480p\" #@param [\"480p\", \"720p\", \"1080p\"]\n",
                "\n",
                "print(f\"Episode configured: {genre_template} | {number_of_shots} shots x {seconds_per_shot}s (~{number_of_shots * seconds_per_shot}s) | Model: {video_model}\")\n",
                "if character_reference_image and Path(character_reference_image).is_file():\n",
                "    print(f\"📸 Character reference attached for {character_name}: {character_reference_image}\")\n",
                "else:\n",
                "    print(\"ℹ️ No reference image provided; characters will follow prompt style bible.\")"
            ],
            "execution_count": None,
            "outputs": []
        },
        {
            "cell_type": "code",
            "metadata": {"cellView": "form", "id": "cell-4"},
            "source": [
                "#@title 4. Generate Screenplay & Quality Scoring\n",
                "use_llm = False #@param {type:\"boolean\"}\n",
                "llm_provider = \"Gemini\" #@param [\"Gemini\", \"OpenAI\"]\n",
                "gemini_secret_name = \"GEMINI_API_KEY\" #@param {type:\"string\"}\n",
                "\n",
                "# If use_llm is False, the built-in microdrama template generator is used (instant, zero cost).\n",
                "from src.microdrama.narrative import Screenwriter, MicrodramaJudge\n",
                "from src.microdrama.templates import get_template, list_templates\n",
                "\n",
                "template_map = {\n",
                "    \"Hidden Billionaire (Secret Tycoon)\": \"hidden_billionaire\",\n",
                "    \"Revenge of the Stolen Identity\": \"revenge_comeback\",\n",
                "    \"The Cold CEO's Contract Bride\": \"contract_marriage\",\n",
                "    \"The Alpha's Claim (Mafia Don)\": \"werewolf_mafia\",\n",
                "    \"Psychological Doppelganger (Do Not Open The Door)\": \"thriller_loop\",\n",
                "}\n",
                "tid = template_map.get(genre_template)\n",
                "template = get_template(tid) if tid else None\n",
                "\n",
                "api_key = None\n",
                "if use_llm:\n",
                "    try:\n",
                "        from google.colab import userdata\n",
                "        api_key = userdata.get(gemini_secret_name)\n",
                "    except Exception:\n",
                "        api_key = os.getenv('GEMINI_API_KEY')\n",
                "\n",
                "writer = Screenwriter(provider='gemini' if (use_llm and api_key) else 'mock', api_key=api_key)\n",
                "scenes_list = [s.strip() for s in specific_scenes.split(';') if s.strip()] if specific_scenes else None\n",
                "\n",
                "screenplay = writer.generate_screenplay(\n",
                "    story_idea=story_prompt,\n",
                "    template=template,\n",
                "    shot_count=number_of_shots,\n",
                "    seconds_per_shot=seconds_per_shot,\n",
                "    specific_scenes=scenes_list,\n",
                ")\n",
                "\n",
                "score = MicrodramaJudge.evaluate(screenplay)\n",
                "print(f\"\\n🎭 SCREENPLAY: {screenplay.title}\")\n",
                "print(f\"Hook: {screenplay.hook}\")\n",
                "print(f\"Cliffhanger: {screenplay.cliffhanger}\")\n",
                "print(f\"DramaBench Quality Gate: Hook={score.hook_score}/5 | Cliffhanger={score.cliffhanger_score}/5 | Dialogue={score.dialogue_score}/5 | Approved={score.is_approved}\")\n",
                "print(\"-\" * 60)\n",
                "for s in screenplay.shots:\n",
                "    print(f\"[{s.id}] {s.duration}s | {s.speaker or 'Action'}: {s.dialogue or '(no line)'}\")\n",
                "    print(f\"     Visual: {s.visual}\")\n",
                "    print(f\"     Action: {s.action}\")"
            ],
            "execution_count": None,
            "outputs": []
        },
        {
            "cell_type": "code",
            "metadata": {"cellView": "form", "id": "cell-5"},
            "source": [
                "#@title 5. Free Zero-Cost 9:16 Storyboard Preview (No Video Credits)\n",
                "from src.microdrama.postprod import StoryboardGenerator, SubtitleGenerator\n",
                "storyboard_gen = StoryboardGenerator(output_dir=ROOT / 'storyboard')\n",
                "cards = storyboard_gen.render_full_storyboard(screenplay)\n",
                "srt_file = ROOT / 'episode.srt'\n",
                "SubtitleGenerator.generate_srt(screenplay, srt_file)\n",
                "\n",
                "print(f\"✅ Generated {len(cards)} vertical storyboard cards and subtitles ({srt_file.name})\")\n",
                "print(\"Displaying opening hook and cliffhanger cards below:\")\n",
                "display(IPImage(filename=str(cards[0]), width=270))\n",
                "if len(cards) > 1:\n",
                "    display(IPImage(filename=str(cards[-1]), width=270))"
            ],
            "execution_count": None,
            "outputs": []
        },
        {
            "cell_type": "code",
            "metadata": {"cellView": "form", "id": "cell-6"},
            "source": [
                "#@title 6. Video Generation via Magic Hour API (Explicit Paid Approval)\n",
                "approve_generation = False #@param {type:\"boolean\"}\n",
                "magic_hour_secret_name = \"MAGIC_HOUR_API_KEY\" #@param {type:\"string\"}\n",
                "generation_scope = \"First shot only (Test)\" #@param [\"First shot only (Test)\", \"Full Episode\"]\n",
                "\n",
                "if not approve_generation:\n",
                "    print('⚠️ Generation not approved. Tick approve_generation to spend Magic Hour credits, then run this cell.')\n",
                "else:\n",
                "    try:\n",
                "        from google.colab import userdata\n",
                "        mkey = userdata.get(magic_hour_secret_name)\n",
                "    except Exception:\n",
                "        mkey = os.getenv('MAGIC_HOUR_API_KEY')\n",
                "    if not mkey:\n",
                "        raise RuntimeError('Missing Magic Hour API key. Add it to Colab Secrets under MAGIC_HOUR_API_KEY.')\n",
                "    \n",
                "    from src.microdrama.client import MagicHourGenerator, JobJournal\n",
                "    gen = MagicHourGenerator(api_key=mkey, journal=JobJournal(ROOT / 'jobs.json'))\n",
                "    if character_reference_image and Path(character_reference_image).is_file():\n",
                "        for c in screenplay.cast:\n",
                "            if c.name.lower() == character_name.lower():\n",
                "                c.reference_image_path = character_reference_image\n",
                "    \n",
                "    manifest = gen.build_shot_manifest(screenplay, model=video_model, resolution=video_resolution, audio=True)\n",
                "    if generation_scope == \"First shot only (Test)\":\n",
                "        manifest = manifest[:1]\n",
                "    \n",
                "    print(f\"🚀 Generating {len(manifest)} shot(s) on Magic Hour...\")\n",
                "    clip_paths = []\n",
                "    for item in manifest:\n",
                "        print(f\"Submitting/Polling {item['shot_id']}...\")\n",
                "        clip = gen.run_shot(item)\n",
                "        clip_paths.append(clip)\n",
                "        print(f\"✅ Downloaded: {clip.name}\")\n",
                "    print('🎉 Video generation complete!')"
            ],
            "execution_count": None,
            "outputs": []
        },
        {
            "cell_type": "code",
            "metadata": {"cellView": "form", "id": "cell-7"},
            "source": [
                "#@title 7. Stitch Full Episode & Playback\n",
                "from src.microdrama.postprod import EpisodeAssembler\n",
                "assembler = EpisodeAssembler(output_dir=ROOT)\n",
                "available_clips = sorted((ROOT / 'clips').glob('*.mp4'))\n",
                "\n",
                "if not available_clips:\n",
                "    print('No generated video clips found yet. Run cell 6 first.')\n",
                "else:\n",
                "    # Match available clips to screenplay shot count\n",
                "    target_screenplay = screenplay.model_copy()\n",
                "    target_screenplay.shots = target_screenplay.shots[:len(available_clips)]\n",
                "    master_file = assembler.assemble(\n",
                "        screenplay=target_screenplay,\n",
                "        clip_paths=available_clips,\n",
                "        out_filename='microdrama_episode_master.mp4',\n",
                "    )\n",
                "    print(f'🎬 Master Episode Assembled: {master_file.name}')\n",
                "    display(Video(str(master_file), embed=True, width=320))"
            ],
            "execution_count": None,
            "outputs": []
        },
        {
            "cell_type": "code",
            "metadata": {"cellView": "form", "id": "cell-8"},
            "source": [
                "#@title 8. Download Project Bundle (ZIP)\n",
                "import zipfile\n",
                "zip_path = ROOT.parent / 'microdrama_project.zip'\n",
                "with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:\n",
                "    for p in ROOT.rglob('*'):\n",
                "        if p.is_file() and p.suffix not in ('.part', '.tmp'):\n",
                "            z.write(p, p.relative_to(ROOT))\n",
                "\n",
                "print(f'📦 Project archived to {zip_path.name}')\n",
                "try:\n",
                "    from google.colab import files\n",
                "    files.download(str(zip_path))\n",
                "    print('Download started in browser.')\n",
                "except Exception:\n",
                "    print(f'Local environment: Archive ready at {zip_path.resolve()}')"
            ],
            "execution_count": None,
            "outputs": []
        }
    ]
}

target = Path("MicroDrama_Studio.ipynb")
target.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
print(f"Successfully generated {target.name} ({len(notebook['cells'])} cells)")
