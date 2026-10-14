"""Configuration and environment management for MicroDrama generator."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JOURNAL_FILE = OUTPUT_DIR / "jobs.json"
UPLOADS_CACHE_FILE = OUTPUT_DIR / "uploads.json"

# API Keys
MAGIC_HOUR_API_KEY = os.getenv("MAGIC_HOUR_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Video Specs
DEFAULT_ASPECT_RATIO = "9:16"
DEFAULT_RESOLUTION = "480p"  # 480p, 720p, 1080p
DEFAULT_MODEL = "ltx-2.5"
SUPPORTED_RESOLUTIONS = ("480p", "720p", "1080p")
SUPPORTED_ASPECT_RATIOS = ("9:16", "16:9")

# Vertical 9:16 Framing System Instruction
VERTICAL_FRAMING_INSTRUCTION = (
    "Vertical 9:16 phone framing: portrait composition, subject centered with headroom, "
    "dynamic medium shots and close-ups, tall depth of field, key dramatic action inside "
    "the central safe area, slow deliberate vertical pans or rapid push-ins, strictly no wide "
    "letterboxed landscape composition."
)
