import os
from .storyteller import write_script
from .backend import DryRunBackend

def run_episode(llm, brief, out_dir, backend=None, log=print):
    os.makedirs(out_dir, exist_ok=True)
    script, issues = write_script(llm, brief, log=log)
    open(os.path.join(out_dir, "script.json"), "w").write(script.to_json())
    backend = backend or DryRunBackend()
    paths = [backend.generate_shot(s, brief, os.path.join(out_dir, "shots")) for s in script.shots]
    final = backend.assemble(paths, os.path.join(out_dir, "episode.out"))
    return {"script": script, "issues": issues, "output": final}
