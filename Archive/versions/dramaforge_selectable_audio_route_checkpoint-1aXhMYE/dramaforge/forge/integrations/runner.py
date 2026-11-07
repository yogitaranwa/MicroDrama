"""Execute vendored-repo CLIs for real (m19).

Fail-closed preflight, then a genuine subprocess run with a captured log.
No shell=True anywhere. A job that cannot run says exactly why."""
from __future__ import annotations

import os
import subprocess
import time

from .registry import IntegrationError


def preflight(argv: list, required_paths=(), need_cuda: bool = False) -> list:
    """Validate an argv before running. Returns argv; raises IntegrationError
    naming every blocking problem found."""
    problems = []
    if not argv or not isinstance(argv, (list, tuple)):
        raise IntegrationError("argv must be a non-empty list")
    script = argv[1] if len(argv) > 1 and os.path.basename(str(argv[0])).startswith("python") else argv[0]
    if script.endswith(".py") and not os.path.isfile(script):
        problems.append(f"entrypoint not found: {script}")
    for p in required_paths:
        if not os.path.exists(p):
            problems.append(f"required path missing: {p}")
    if need_cuda:
        # A driver utility on PATH is not evidence that a usable GPU exists.
        try:
            import torch
            if not torch.cuda.is_available():
                problems.append("no CUDA GPU visible (torch.cuda.is_available() is False)")
        except Exception:
            problems.append("no CUDA GPU visible (torch unavailable or CUDA check failed)")
    if problems:
        raise IntegrationError("preflight blocked: " + "; ".join(problems))
    return list(argv)


def run(argv: list, cwd: str = None, log_path: str = None,
        timeout_s: int = 3600, env_extra: dict = None) -> dict:
    """Run argv as a real subprocess. Returns {ok, returncode, seconds, log,
    log_path}. Nonzero exits are reported, not hidden."""
    if not argv:
        raise IntegrationError("argv must be a non-empty list")
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    started = time.time()
    proc = subprocess.run([str(a) for a in argv], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=timeout_s)
    log = (proc.stdout or "") + ("\n--- stderr ---\n" + proc.stderr if proc.stderr else "")
    if log_path:
        with open(log_path, "w", encoding="utf-8") as fh:
            fh.write(log)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode,
            "seconds": round(time.time() - started, 2),
            "log": log[-4000:], "log_path": log_path}


def run_streamed(argv, cwd=None, log_path=None, timeout_s=3600, env_extra=None):
    """Production subprocess path: streamed log and process-group timeout cleanup.
    Legacy run is retained; this route does not hold a whole model log in RAM.
    """
    from pathlib import Path
    from .streaming_process import run_step
    if not log_path:
        raise IntegrationError('streamed model execution requires a private log path')
    result = run_step(argv, cwd=cwd, log_path=log_path,
        status_path=str(log_path)+'.status.json', timeout_s=timeout_s,
        env_extra=env_extra)
    with open(log_path, 'rb') as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell()-4000))
        tail = f.read().decode('utf-8',errors='replace')
    return {'ok':result['status']=='passed', 'returncode':result['returncode'],
            'seconds':result['seconds'], 'log':tail, 'log_path':str(log_path),
            'status':result['status'], 'status_path':str(log_path)+'.status.json'}
