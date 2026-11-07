import json, os, urllib.request, re

class LLM:
    def complete(self, system, user, temperature=0.8):
        raise NotImplementedError

class OpenAICompatLLM(LLM):
    def __init__(self, base_url, model, api_key=None, timeout=120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.timeout = timeout

    def complete(self, system, user, temperature=0.8):
        body = json.dumps({"model": self.model, "temperature": temperature,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(self.base_url + "/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]

def extract_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < 0:
        raise ValueError("no json object in model output")
    return json.loads(text[a:b + 1])
