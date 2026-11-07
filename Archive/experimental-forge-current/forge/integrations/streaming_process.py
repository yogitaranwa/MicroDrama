"""Stream real subprocess progress to disk with bounded process-group cleanup.

No cloud operations or model execution occur on import. Call only in an
approved host workflow. Logs may contain task input; keep them private.
"""
import json
import os
import selectors
import signal
import subprocess
import time
from pathlib import Path


def run_step(argv, *, log_path, status_path, timeout_s, cwd=None, emit=print, env_extra=None):
    if timeout_s <= 0:
        raise ValueError('timeout must be positive')
    log_path, status_path = Path(log_path), Path(status_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    env = dict(os.environ, PYTHONUNBUFFERED='1')
    if env_extra: env.update(env_extra)
    record = {'argv': [str(a) for a in argv], 'status': 'starting',
              'log': str(log_path), 'timeout_s': timeout_s}
    def save(**values):
        record.update(values)
        status_path.write_text(json.dumps(record, indent=2))
    save()
    proc = subprocess.Popen(record['argv'], cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    save(status='running', pid=proc.pid)
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    timed_out = False
    try:
        with log_path.open('wb') as log:
            while sel.get_map():
                remaining = timeout_s - (time.monotonic() - started)
                if remaining <= 0:
                    timed_out = True
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                    # Children can outlive a wrapper that already exited.
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    break
                for key, _ in sel.select(min(1.0, remaining)):
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        sel.unregister(key.fileobj)
                        continue
                    log.write(data)
                    log.flush()
                    emit(data.decode('utf-8', errors='replace'), end='', flush=True)
            code = proc.wait(timeout=10)
        save(status='timed_out' if timed_out else ('passed' if code == 0 else 'failed'),
             returncode=code, seconds=round(time.monotonic()-started, 2))
    except BaseException as exc:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=10)
        save(status='interrupted', error=type(exc).__name__)
        raise
    finally:
        sel.close()
        proc.stdout.close()
    return record
