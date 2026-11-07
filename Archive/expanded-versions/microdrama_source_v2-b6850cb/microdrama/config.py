import os

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
PLACEHOLDER_WRITER = "meta/llama-3.3-70b-instruct"
PLACEHOLDER_JUDGE = "meta/llama-3.3-70b-instruct"

def llm_settings():
    return {
        "base_url": os.environ.get("NVIDIA_BASE_URL", DEFAULT_BASE_URL),
        "writer_model": os.environ.get("MD_WRITER_MODEL", PLACEHOLDER_WRITER),
        "judge_model": os.environ.get("MD_JUDGE_MODEL", PLACEHOLDER_JUDGE),
        "api_key": os.environ.get("NVIDIA_API_KEY", ""),
    }

def check_distinct(settings):
    if settings["writer_model"] == settings["judge_model"]:
        return "writer and judge are the same model; set MD_WRITER_MODEL and MD_JUDGE_MODEL to two different NVIDIA-hosted models before a real benchmark"
    return ""
