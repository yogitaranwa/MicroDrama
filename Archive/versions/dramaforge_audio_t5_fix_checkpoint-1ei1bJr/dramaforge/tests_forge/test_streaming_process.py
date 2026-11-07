"""Real tiny subprocess tests, no model or network."""
import importlib.util
import json
import sys
from pathlib import Path

P=Path(__file__).resolve().parents[1]/'gpu_tests/streaming_process.py'
spec=importlib.util.spec_from_file_location('streaming_process',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_progress_written_before_process_exits(tmp_path):
    log=tmp_path/'step.log';state=tmp_path/'status.json';observed=[]
    def emit(text,**kwargs):
        observed.append((text, log.read_text(), json.loads(state.read_text())['status']))
    r=m.run_step([sys.executable,'-c',"import time; print('MODEL_LOADING',flush=True); time.sleep(.05); print('DONE',flush=True)"],
        log_path=log,status_path=state,timeout_s=5,emit=emit)
    assert r['status']=='passed'
    assert any('MODEL_LOADING' in text and 'MODEL_LOADING' in disk and status=='running'
               for text,disk,status in observed)
    assert 'DONE' in log.read_text()


def test_timeout_stops_process_and_preserves_progress(tmp_path):
    log=tmp_path/'step.log';state=tmp_path/'status.json'
    r=m.run_step([sys.executable,'-c',"import time; print('START',flush=True); time.sleep(30)"],
        log_path=log,status_path=state,timeout_s=.2,emit=lambda *a,**k:None)
    assert r['status']=='timed_out' and r['seconds'] < 10
    assert 'START' in log.read_text()
    assert json.loads(state.read_text())['status']=='timed_out'


def test_real_failure_not_reported_as_pass(tmp_path):
    r=m.run_step([sys.executable,'-c',"raise RuntimeError('fixture failure')"],
        log_path=tmp_path/'log',status_path=tmp_path/'status',timeout_s=5,emit=lambda *a,**k:None)
    assert r['status']=='failed' and r['returncode']!=0
