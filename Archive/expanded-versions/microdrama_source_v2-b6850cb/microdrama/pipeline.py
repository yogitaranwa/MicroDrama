import os
from .storyteller import write_script
from .backend import DryRunBackend
from .governor import plan_episode

def run_episode(llm, brief, out_dir, backend=None, log=print, approved=False, script=None):
    os.makedirs(out_dir, exist_ok=True)
    issues = []
    if script is None:
        script, issues = write_script(llm, brief, log=log)
    open(os.path.join(out_dir, "script.json"), "w").write(script.to_json())
    plan, total = plan_episode(script)
    open(os.path.join(out_dir, "render_plan.txt"), "w").write("\n".join(f"shot {p['shot']}: {p['mode']} {p['est_credits']} credits" for p in plan) + f"\ntotal {total} credits (estimate)\n")
    if not approved:
        return {"script": script, "issues": issues, "plan": plan, "est_credits": total, "output": None, "status": "awaiting_approval"}
    backend = backend or DryRunBackend()
    paths = [backend.generate_shot(s, brief, os.path.join(out_dir, "shots")) for s in script.shots]
    final = backend.assemble(paths, os.path.join(out_dir, "episode.out"))
    return {"script": script, "issues": issues, "plan": plan, "est_credits": total, "output": final, "status": "done"}
