import json, tempfile
from microdrama.schema import Script, Brief, Character
from microdrama.pipeline import run_episode
from microdrama.backend import MagicHourBackend, LockedError
from microdrama.governor import CostGovernor, BudgetExceeded
from microdrama.config import llm_settings, check_distinct

script = Script.from_dict(json.load(open("E1_script.json")))
brief = Brief("Second Period E1", [Character("Mina"), Character("Jun-ho"), Character("Ari")], "hidden_identity", 60, "en", episode_number=1)
d = tempfile.mkdtemp()
r = run_episode(None, brief, d, script=script)
assert r["status"] == "awaiting_approval" and r["output"] is None and r["est_credits"] == 1224, r["est_credits"]
r2 = run_episode(None, brief, d, script=script, approved=True)
assert r2["status"] == "done"
try:
    MagicHourBackend(api_key="x")
    raise SystemExit("should be locked")
except LockedError:
    pass
g = CostGovernor(20000, 3000)
g.approve(1224)
try:
    g.approve(20000)
    raise SystemExit("should exceed")
except BudgetExceeded:
    pass
assert check_distinct(llm_settings())
print("ok", r["est_credits"])
