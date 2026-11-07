"""LLM access: NVIDIA first; Claude only after a stall, hard per-run cap. Schema-validated via Instructor (MIT)."""
import os, time
import instructor
from openai import OpenAI

NVIDIA_URL = "https://integrate.api.nvidia.com/v1"

class RunCapExceeded(RuntimeError):
    pass

class Writer:
    def __init__(self, nvidia_key=None, claude_key=None, model="nvidia/nemotron-3-ultra-550b-a55b",
                 stall_s=60, claude_cap_usd=2.30, claude_model="claude-sonnet-4-5"):
        self.nv = instructor.from_openai(OpenAI(base_url=NVIDIA_URL, api_key=nvidia_key or os.environ.get("NVIDIA_API_KEY"),
                                                timeout=stall_s, max_retries=0), mode=instructor.Mode.JSON)
        self.model, self.claude_key, self.claude_model = model, claude_key, claude_model
        self.cap, self.spent = claude_cap_usd, 0.0

    def structured(self, schema, prompt, retries=2):
        last = None
        for _ in range(retries + 1):
            try:
                return self.nv.chat.completions.create(model=self.model, response_model=schema,
                       messages=[{"role": "user", "content": prompt}], max_retries=3,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
            except Exception as e:  # timeout/stall or invalid JSON
                last = e
        return self._claude(schema, prompt, last)

    def _claude(self, schema, prompt, cause):
        if not self.claude_key:
            raise RuntimeError(f"NVIDIA failed and no fallback key configured: {cause}")
        if self.spent >= self.cap:
            raise RunCapExceeded(f"Claude fallback cap ${self.cap} reached")
        import anthropic
        c = instructor.from_anthropic(anthropic.Anthropic(api_key=self.claude_key))
        self.spent += 0.30  # conservative per-call reserve; true usage can only be lower
        return c.messages.create(model=self.claude_model, max_tokens=4096, response_model=schema,
                                 messages=[{"role": "user", "content": prompt}])
