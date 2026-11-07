"""LLM access: NVIDIA first; Claude only after a stall, hard per-run cap. Schema-validated via Instructor (MIT).

Hardened (m15):
- Clearly non-retryable NVIDIA failures (auth/permission/invalid request)
  raise immediately instead of silently burning the paid Claude fallback.
- The Claude cap is checked against spent + this call's reserve, so a run
  can never cross its approved USD budget.
"""
import os, time
import instructor
from openai import OpenAI

NVIDIA_URL = "https://integrate.api.nvidia.com/v1"

# HTTP statuses that will never succeed on retry: bad key, no permission,
# malformed request. Anything else (timeouts, 429, 5xx, parse failures)
# stays on the existing retry/fallback path.
NON_RETRYABLE_STATUS = frozenset({400, 401, 403, 404, 422})


def _status_of(exc):
    """Best-effort extraction of an HTTP status from an exception chain
    (openai APIStatusError, instructor wrappers)."""
    seen, cur = set(), exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        code = getattr(cur, "status_code", None)
        if isinstance(code, int):
            return code
        cur = (getattr(cur, "last_exception", None) or getattr(cur, "__cause__", None)
               or getattr(cur, "__context__", None))
    return None


def _retryable(exc) -> bool:
    return _status_of(exc) not in NON_RETRYABLE_STATUS


class RunCapExceeded(RuntimeError):
    pass

class Writer:
    # Conservative per-call reserve for the Claude fallback; true usage can
    # only be lower. Checked as spent + reserve > cap so the cap holds.
    CLAUDE_RESERVE_USD = 0.30

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
                if not _retryable(e):
                    raise RuntimeError(
                        f"NVIDIA request failed with a non-retryable error "
                        f"(status {_status_of(e)}); fix the key/request instead of "
                        f"falling back to paid Claude: {e}") from e
                last = e
        return self._claude(schema, prompt, last)

    def _claude(self, schema, prompt, cause):
        if not self.claude_key:
            raise RuntimeError(f"NVIDIA failed and no fallback key configured: {cause}")
        if self.spent + self.CLAUDE_RESERVE_USD > self.cap:
            raise RunCapExceeded(
                f"Claude fallback cap ${self.cap} reached "
                f"(spent ${self.spent:.2f}, next call reserves ${self.CLAUDE_RESERVE_USD:.2f})")
        import anthropic
        c = instructor.from_anthropic(anthropic.Anthropic(api_key=self.claude_key))
        self.spent += self.CLAUDE_RESERVE_USD  # conservative per-call reserve; true usage can only be lower
        return c.messages.create(model=self.claude_model, max_tokens=4096, response_model=schema,
                                 messages=[{"role": "user", "content": prompt}])
