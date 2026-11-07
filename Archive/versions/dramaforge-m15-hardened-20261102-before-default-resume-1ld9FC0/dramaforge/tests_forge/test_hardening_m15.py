"""m15 hardening regression tests: money guards, paid-API failure handling,
resumable renders, audio/pace edge cases, dialogue preservation, voice
routing, TTS response validation, caption path escaping, review validation.

Every test maps to a failure mode that cost credits or produced a bad draft:
duplicate paid renders after a mid-run crash, ledger corruption, auth errors
burning the paid fallback, silent-stretch drafts, and crashes at spend time.
"""
import asyncio
import json
import os
import sys
import types

import pytest

from forge.guard.ledger import Ledger, SpendLocked


# ---------------------------------------------------------------- ledger ---

def _live_ledger(tmp_path, monkeypatch, approved=100, spent=0):
    monkeypatch.setenv("FORGE_LIVE", "1")
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps({"approved": approved, "spent": spent}))
    return Ledger(p)


@pytest.mark.parametrize("bad", [-5, 0, -0.001, True, False, float("nan"),
                                 float("inf"), "10", None])
def test_reserve_rejects_non_positive_or_non_numeric(tmp_path, monkeypatch, bad):
    ledger = _live_ledger(tmp_path, monkeypatch)
    with pytest.raises(SpendLocked):
        ledger.reserve(bad)
    assert ledger.remaining() == 100  # untouched


def test_reserve_negative_amount_cannot_create_credit(tmp_path, monkeypatch):
    ledger = _live_ledger(tmp_path, monkeypatch)
    ledger.reserve(30)
    with pytest.raises(SpendLocked):
        ledger.reserve(-30)
    assert ledger.remaining() == 70


def test_corrupt_ledger_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_LIVE", "1")
    p = tmp_path / "ledger.json"
    p.write_text('{"approved": 100, "spe')  # crash-truncated write
    with pytest.raises(SpendLocked, match="unreadable"):
        Ledger(p).reserve(1)


@pytest.mark.parametrize("content", [
    '{"approved": "100", "spent": 0}',      # wrong type
    '{"approved": 100}',                    # missing key
    '{"approved": -5, "spent": 0}',         # negative approval
    '{"approved": 100, "spent": true}',     # bool is not a number
    '[100, 0]',                             # not an object
])
def test_malformed_ledger_fails_closed(tmp_path, monkeypatch, content):
    monkeypatch.setenv("FORGE_LIVE", "1")
    p = tmp_path / "ledger.json"
    p.write_text(content)
    with pytest.raises(SpendLocked, match="malformed"):
        Ledger(p).reserve(1)


def test_ledger_write_is_atomic(tmp_path, monkeypatch):
    ledger = _live_ledger(tmp_path, monkeypatch)
    ledger.reserve(10)
    leftovers = [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
    assert leftovers == []
    assert json.loads((tmp_path / "ledger.json").read_text())["spent"] == 10


def test_concurrent_reserves_never_overspend(tmp_path, monkeypatch):
    import threading
    ledger = _live_ledger(tmp_path, monkeypatch, approved=100)
    errors = []

    def spend():
        try:
            ledger.reserve(10)
        except SpendLocked:
            pass
        except Exception as e:  # pragma: no cover - must never happen
            errors.append(e)

    threads = [threading.Thread(target=spend) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    state = json.loads((tmp_path / "ledger.json").read_text())
    assert state["spent"] <= 100
    assert state["spent"] == 100  # exactly ten reserves got through


def test_missing_ledger_means_zero_approved(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_LIVE", "1")
    ledger = Ledger(tmp_path / "nope.json")
    assert ledger.remaining() == 0
    with pytest.raises(SpendLocked):
        ledger.reserve(1)


# ----------------------------------------------------------------- llm -----

class _FakeHttpError(Exception):
    def __init__(self, status_code):
        super().__init__(f"http {status_code}")
        self.status_code = status_code


def _writer(monkeypatch, **kw):
    from forge.llm import Writer
    w = Writer(nvidia_key="test", claude_key="test-claude", **kw)
    return w


def test_non_retryable_nvidia_error_never_touches_paid_fallback(monkeypatch):
    w = _writer(monkeypatch)

    def fail(**kw):
        raise _FakeHttpError(401)
    monkeypatch.setattr(w.nv.chat.completions, "create", fail)
    called = []
    monkeypatch.setattr(type(w), "_claude", lambda self, s, p, c: called.append(c))
    with pytest.raises(RuntimeError, match="non-retryable"):
        w.structured(object, "prompt", retries=2)
    assert called == []          # no paid fallback
    assert w.spent == 0.0        # no money reserved


def test_retryable_nvidia_error_still_falls_back(monkeypatch):
    w = _writer(monkeypatch)

    def fail(**kw):
        raise _FakeHttpError(500)
    monkeypatch.setattr(w.nv.chat.completions, "create", fail)
    seen = []
    monkeypatch.setattr(type(w), "_claude",
                        lambda self, s, p, c: seen.append((s, p)) or "fallback-result")
    assert w.structured(object, "prompt", retries=1) == "fallback-result"
    assert len(seen) == 1


def test_claude_cap_counts_the_next_calls_reserve(monkeypatch):
    from forge.llm import RunCapExceeded
    w = _writer(monkeypatch, claude_cap_usd=2.30)
    w.spent = 2.10  # 2.10 + 0.30 reserve > 2.30 cap: old check allowed this
    with pytest.raises(RunCapExceeded):
        w._claude(object, "prompt", cause="nvidia stalled")


def test_claude_call_within_cap_reserves_and_calls(monkeypatch):
    import forge.llm as llm
    w = _writer(monkeypatch, claude_cap_usd=2.30)
    w.spent = 1.90
    fake_mod = types.ModuleType("anthropic")

    class FakeAnthropic:
        def __init__(self, api_key=None):
            self.api_key = api_key
    fake_mod.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake_mod)

    class FakeMessages:
        @staticmethod
        def create(**kw):
            return {"created": True}
    fake_client = types.SimpleNamespace(messages=FakeMessages())
    monkeypatch.setattr(llm.instructor, "from_anthropic", lambda c: fake_client)
    assert w._claude(object, "prompt", cause="x") == {"created": True}
    assert w.spent == pytest.approx(2.20)


# ---------------------------------------------------------- gates common ---

def test_gate_state_write_is_atomic(tmp_path):
    from forge.gates.common import write_json, read_json
    target = tmp_path / "state.json"
    write_json(target, {"a": 1})
    assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []
    assert read_json(target) == {"a": 1}


def test_corrupt_gate_state_fails_closed(tmp_path):
    from forge.gates.common import read_json, GateLocked
    target = tmp_path / "review_signoff.json"
    target.write_text('{"episode": "x', )
    with pytest.raises(GateLocked, match="unreadable"):
        read_json(target)
    assert read_json(tmp_path / "absent.json") is None  # missing is still fine


# ------------------------------------------------------- magichour poll ----

def _generator(tmp_path):
    from tools.video_generator_magichour_api import VideoGeneratorMagicHourAPI
    g = VideoGeneratorMagicHourAPI("k", ledger_path=str(tmp_path / "ledger.json"))
    g.POLL_INTERVAL_S = 0  # no real sleeps in tests
    return g


class _Resp:
    def __init__(self, payload=None, json_error=False, status=200):
        self._payload = payload
        self._json_error = json_error
        self.status_code = status

    def raise_for_status(self):
        import requests
        if self.status_code >= 400:
            raise requests.HTTPError(f"http {self.status_code}", response=self)

    def json(self):
        if self._json_error:
            raise ValueError("not json")
        return self._payload


def test_poll_tolerates_transient_errors_then_completes(tmp_path, monkeypatch):
    import tools.video_generator_magichour_api as mh
    g = _generator(tmp_path)
    get_calls = {"n": 0}

    def fake_get(url, headers, timeout):
        get_calls["n"] += 1
        if get_calls["n"] == 1:
            import requests
            raise requests.ConnectionError("blip")
        if get_calls["n"] == 2:
            return _Resp(status=502)
        if get_calls["n"] == 3:
            return _Resp(json_error=True)
        return _Resp({"status": "complete", "downloads": [{"url": "http://clip"}]})
    monkeypatch.setattr(mh.requests, "get", fake_get)
    assert g._poll("job-1", {}) == "http://clip"


def test_poll_gives_up_after_error_budget(tmp_path, monkeypatch):
    import tools.video_generator_magichour_api as mh
    g = _generator(tmp_path)
    monkeypatch.setattr(mh.requests, "get",
                        lambda *a, **k: _Resp(json_error=True))
    with pytest.raises(RuntimeError, match="job-9"):
        g._poll("job-9", {})


def test_poll_terminal_status_names_job(tmp_path, monkeypatch):
    import tools.video_generator_magichour_api as mh
    g = _generator(tmp_path)
    monkeypatch.setattr(mh.requests, "get",
                        lambda *a, **k: _Resp({"status": "error"}))
    with pytest.raises(RuntimeError, match="job-3 error"):
        g._poll("job-3", {})


def test_poll_complete_without_download_is_a_clear_error(tmp_path, monkeypatch):
    import tools.video_generator_magichour_api as mh
    g = _generator(tmp_path)
    monkeypatch.setattr(mh.requests, "get",
                        lambda *a, **k: _Resp({"status": "complete", "downloads": []}))
    with pytest.raises(RuntimeError, match="no download URL"):
        g._poll("job-4", {})


def test_submit_requires_a_job_id(tmp_path, monkeypatch):
    import tools.video_generator_magichour_api as mh
    g = _generator(tmp_path)
    monkeypatch.setattr(mh.requests, "post", lambda *a, **k: _Resp({"nope": 1}))
    with pytest.raises(RuntimeError, match="no job id"):
        g._submit("prompt", None, 5)
    monkeypatch.setattr(mh.requests, "post", lambda *a, **k: _Resp(json_error=True))
    with pytest.raises(RuntimeError, match="non-JSON"):
        g._submit("prompt", None, 5)


def test_poll_malformed_payload_counts_as_transient(tmp_path, monkeypatch):
    import tools.video_generator_magichour_api as mh
    g = _generator(tmp_path)
    payloads = iter([["not", "a", "dict"],
                     {"status": 42},
                     {"status": "complete", "downloads": [{"url": "u"}]}])
    monkeypatch.setattr(mh.requests, "get",
                        lambda *a, **k: _Resp(next(payloads)))
    assert g._poll("job-5", {}) == "u"


# ------------------------------------------------------------ resume -------

def _img(path):
    from PIL import Image
    Image.new("RGB", (32, 32), (9, 9, 9)).save(path)
    return str(path)


def _project(tmp_path):
    from forge.script_run import write_plan_and_lint
    from forge.gates import lock_stills
    from forge.render_plan import build_render_jobs
    shots = [{"n": 1, "location": "hall", "camera": "wide", "action": "she turns",
              "seconds": 8,
              "lines": [{"speaker": "Harry", "text": "You knew about this?"},
                         {"speaker": "Draconia", "text": "I suspected it before you did."}]}]
    write_plan_and_lint(shots, outdir=tmp_path / "out")
    jobs = build_render_jobs(tmp_path)
    stills = {}
    for j in jobs:
        if j["reference_still"]:
            stills[j["reference_still"]] = _img(tmp_path / (j["reference_still"].replace(":", "_") + ".png"))
        if j["location_still"]:
            stills[j["location_still"]] = _img(tmp_path / (j["location_still"].replace(":", "_") + ".png"))
    lock_stills(tmp_path, stills)
    return jobs


class _Gen:
    def __init__(self, fail_at_call=None):
        self.calls = []
        self.fail_at_call = fail_at_call

    async def generate_single_video(self, prompt, refs, **kw):
        self.calls.append(kw)
        if self.fail_at_call is not None and len(self.calls) == self.fail_at_call:
            raise RuntimeError("provider exploded mid-render")
        return types.SimpleNamespace(data=f"https://provider.test/clip-{len(self.calls)}-of-this-run.mp4")


def test_resume_skips_already_paid_clips(tmp_path):
    from forge.render_plan import execute_plan
    jobs = _project(tmp_path)
    n = len(jobs)
    gen = _Gen(fail_at_call=2)
    with pytest.raises(RuntimeError, match="provider exploded"):
        asyncio.run(execute_plan(tmp_path, gen, resume=True))
    state = json.loads((tmp_path / ".forge" / "render_execution.json").read_text())
    assert state["jobs"]["1"]["status"] == "done"
    assert state["jobs"]["2"]["status"] == "failed"

    gen2 = _Gen()  # fixed provider; rerun the same plan
    urls = asyncio.run(execute_plan(tmp_path, gen2, resume=True))
    assert len(urls) == n
    assert len(gen2.calls) == n - 1      # clip 1 was NOT paid for again
    assert urls[0] == "https://provider.test/clip-1-of-this-run.mp4"  # recorded output reused


def test_no_resume_keeps_old_behavior_and_writes_no_state(tmp_path):
    from forge.render_plan import execute_plan
    _project(tmp_path)
    gen = _Gen(fail_at_call=2)
    with pytest.raises(RuntimeError):
        asyncio.run(execute_plan(tmp_path, gen))
    assert not (tmp_path / ".forge" / "render_execution.json").exists()


def test_corrupt_execution_record_fails_closed(tmp_path):
    from forge.render_plan import execute_plan, EXECUTION_NAME
    from forge.gates import GateLocked
    from forge.gates.common import state_dir
    _project(tmp_path)
    state_dir(tmp_path).mkdir(parents=True, exist_ok=True)
    (state_dir(tmp_path) / EXECUTION_NAME).write_text("{broken")
    with pytest.raises(GateLocked):
        asyncio.run(execute_plan(tmp_path, _Gen(), resume=True))


# ----------------------------------------------------------------- pace ----

def test_phrase_wpm_empty_and_zero_duration():
    from forge.audio.pace import phrase_wpm
    assert phrase_wpm([]) == 0.0
    words = [{"word": w, "start": 1.0, "end": 1.0} for w in "one two three four five".split()]
    assert phrase_wpm(words) == 0.0  # zero-duration phrases skipped, no crash


def test_join_lines_rejects_empty_and_rate_mismatch(tmp_path):
    import numpy as np
    import soundfile as sf
    from forge.audio.pace import join_lines
    with pytest.raises(ValueError, match="no wavs"):
        join_lines([], str(tmp_path / "x.wav"))
    sf.write(str(tmp_path / "a.wav"), np.zeros(800), 8000)
    sf.write(str(tmp_path / "b.wav"), np.zeros(1600), 16000)
    with pytest.raises(ValueError, match="sample rates"):
        join_lines([str(tmp_path / "a.wav"), str(tmp_path / "b.wav")],
                   str(tmp_path / "x.wav"))


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg unavailable")
def test_stretch_and_trim_silence_produce_real_audio(tmp_path):
    import numpy as np
    import soundfile as sf
    from forge.audio.pace import stretch, trim_silence
    sr = 24000
    t = np.arange(sr) / sr
    tone = 0.2 * np.sin(2 * np.pi * 220 * t)
    padded = np.concatenate([np.zeros(sr), tone, np.zeros(sr)])
    src = str(tmp_path / "line.wav")
    sf.write(src, padded, sr)
    stretched = stretch(src, str(tmp_path / "s.wav"), tempo=1.4)
    d, _ = sf.read(stretched)
    assert len(d) == pytest.approx(len(padded) / 1.4, rel=0.05)
    trimmed = trim_silence(src, str(tmp_path / "t.wav"))
    d2, _ = sf.read(trimmed)
    assert len(d2) < len(padded) * 0.6  # both silent seconds gone


# ------------------------------------------------------------- dialogue ----

SCRIPT = [
    {"n": 1, "location": "hall", "camera": "wide", "action": "she turns", "seconds": 10,
     "lines": [{"speaker": "Harry", "text": "You knew about this?"},
                {"speaker": "Draconia", "text": "I suspected it before you did."}]},
    {"n": 2, "location": "hall", "camera": "wide", "action": "he waits", "seconds": 8,
     "lines": [{"speaker": "Harry", "text": "Then say it plainly."}]},
]


def test_dialogue_preserved_on_real_expansion():
    from forge.dialogue_shots import expand_episode, verify_dialogue_preserved
    planned = expand_episode(SCRIPT)
    check = verify_dialogue_preserved(SCRIPT, planned)
    assert check["ok"], check


def test_dialogue_check_detects_missing_line():
    from forge.dialogue_shots import expand_episode, verify_dialogue_preserved
    planned = expand_episode(SCRIPT)
    planned = [p for p in planned if not (p.get("line") or {}).get("text", "").startswith("Then say it")]
    check = verify_dialogue_preserved(SCRIPT, planned)
    assert not check["ok"] and check["missing"]


def test_dialogue_check_detects_duplicated_line():
    from forge.dialogue_shots import expand_episode, verify_dialogue_preserved
    planned = expand_episode(SCRIPT)
    planned.append(dict(planned[0]))
    check = verify_dialogue_preserved(SCRIPT, planned)
    assert not check["ok"] and check["duplicated"]


def test_dialogue_check_detects_reordering():
    from forge.dialogue_shots import expand_episode, verify_dialogue_preserved
    planned = expand_episode(SCRIPT)
    speaker_clips = [p for p in planned if p.get("line")]
    first, last = speaker_clips[0], speaker_clips[-1]
    planned.remove(last)
    planned.insert(planned.index(first), last)
    check = verify_dialogue_preserved(SCRIPT, planned)
    assert not check["ok"] and check["order_broken"]


def test_plan_summary_flags_hand_made_multi_line_clip():
    from forge.dialogue_shots import expand_episode, plan_summary
    planned = expand_episode(SCRIPT)
    assert plan_summary(planned)["multi_speaker_clips"] == []
    planned[0]["line"] = [{"speaker": "A", "text": "x"}, {"speaker": "B", "text": "y"}]
    summary = plan_summary(planned)
    assert summary["multi_speaker_clips"] == [planned[0]["plan_n"]]
    assert summary["total_seconds"] >= sum(
        p["seconds"] for p in planned[1:])


def test_lint_output_includes_dialogue_check(tmp_path):
    from forge.script_run import write_plan_and_lint
    res = write_plan_and_lint(SCRIPT, outdir=tmp_path / "out")
    assert res["lint"]["dialogue_check"]["ok"]


# -------------------------------------------------------------- casting ----

def test_unknown_speaker_fails_loud_with_guidance():
    from forge.audio.casting import settings
    with pytest.raises(ValueError, match="no voice cast"):
        settings("Voldemort", "rage")
    with pytest.raises(ValueError, match="Harry Potter"):
        settings("Harry", "calm")  # close match is suggested


# ------------------------------------------------------------------ tts ----

class _FakeTTSResp:
    def __init__(self, body, ctype):
        self.content = body
        self.headers = {"content-type": ctype}

    def raise_for_status(self):
        pass


def _final(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_LIVE", "1")
    char_ledger = tmp_path / "chars.json"
    char_ledger.write_text(json.dumps({"approved": 1000, "spent": 0}))
    from forge.audio.tts import ElevenLabsFinal
    from forge.guard.ledger import Ledger
    return ElevenLabsFinal("k", "voice-1", char_ledger=Ledger(char_ledger))


def test_elevenlabs_json_error_body_is_not_saved_as_audio(tmp_path, monkeypatch):
    import requests
    f = _final(tmp_path, monkeypatch)
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: _FakeTTSResp(b'{"detail":"quota"}', "application/json"))
    out = tmp_path / "line.mp3"
    with pytest.raises(RuntimeError, match="non-audio"):
        f.say("hello there", str(out))
    assert not out.exists()


def test_elevenlabs_audio_bytes_are_saved(tmp_path, monkeypatch):
    import requests
    f = _final(tmp_path, monkeypatch)
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: _FakeTTSResp(b"ID3\x04\x00\x00\x00\x00\x00\x21", "audio/mpeg"))
    out = f.say("hello there", str(tmp_path / "line.mp3"))
    assert os.path.getsize(out) > 0


def test_elevenlabs_empty_text_refused_before_any_call(tmp_path, monkeypatch):
    import requests
    f = _final(tmp_path, monkeypatch)
    called = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: called.append(1))
    with pytest.raises(ValueError):
        f.say("   ", str(tmp_path / "x.mp3"))
    assert called == []


# -------------------------------------------------------------- compose ----

def test_ass_filter_path_escapes_colab_style_paths():
    from forge.assemble.compose import _escape_filter_path
    p = _escape_filter_path("/content/drive/My Drive/proj/out.captions.ass")
    assert p.startswith("'") and p.endswith("'")
    assert "My Drive" in p


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg unavailable")
def test_burn_captions_works_in_a_path_with_spaces(tmp_path):
    import subprocess
    from forge.assemble.compose import burn_captions
    work = tmp_path / "My Drive"
    work.mkdir()
    video = work / "in.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=black:s=64x64:d=1:r=10", "-pix_fmt", "yuv420p",
                    str(video)], check=True)
    ass = work / "cap.ass"
    ass.write_text(
        "[Script Info]\nPlayResX: 64\nPlayResY: 64\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, Alignment, MarginV\n"
        "Style: Default,DejaVu Sans,12,&H00FFFFFF,2,2\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:00.90,Default,hi\n")
    out = burn_captions(str(video), str(ass), str(work / "out.mp4"))
    assert os.path.getsize(out) > 0


# -------------------------------------------------------------- review -----

def test_review_flags_invalid_shot_durations(tmp_path):
    ep = tmp_path / "ep.mp4"
    ep.write_bytes(b"fake")
    from forge.gates.review import review_episode
    report = review_episode(tmp_path, str(ep),
                            [("a", 5.0), ("b", -2.0), ("c", float("nan"))])
    assert any("invalid shot durations" in i for i in report["issues"])
    assert report["status"] == "issues"


# ----------------------------------------------- resume safety edges -------

def test_resume_fingerprint_binds_plan_and_route(tmp_path):
    from forge.render_plan import execute_plan
    from forge.gates import GateLocked
    _project(tmp_path)
    gen = _Gen(fail_at_call=2)
    with pytest.raises(RuntimeError):
        asyncio.run(execute_plan(tmp_path, gen, resume=True))

    # same plan, but a different audio setting: recorded clips must not apply
    class RouteGen(_Gen):
        model = "ltx-2.5"
        resolution = "720p"
        supports_audio_request = True

        def estimate(self, seconds, audio=False):
            return int(seconds * 48)  # ltx-2.5 720p, audio included

    with pytest.raises(GateLocked, match="different plan/route"):
        asyncio.run(execute_plan(tmp_path, RouteGen(), resume=True,
                                 route_name="ltx-2.5", audio=True))

    # changed plan content: also fails closed
    from forge.script_run import write_plan_and_lint
    shots = [{"n": 1, "location": "hall", "camera": "wide", "action": "DIFFERENT",
              "seconds": 8,
              "lines": [{"speaker": "Harry", "text": "A completely new line."},
                         {"speaker": "Draconia", "text": "And another new answer."}]}]
    write_plan_and_lint(shots, outdir=tmp_path / "out")
    with pytest.raises(GateLocked, match="different plan/route"):
        asyncio.run(execute_plan(tmp_path, _Gen(), resume=True))


def test_resume_fingerprint_binds_locked_still_bytes(tmp_path):
    from forge.render_plan import execute_plan
    from forge.gates import GateLocked, lock_stills
    from forge.render_plan import build_render_jobs
    jobs = _project(tmp_path)
    with pytest.raises(RuntimeError):
        asyncio.run(execute_plan(tmp_path, _Gen(fail_at_call=2), resume=True))
    # deliberate re-lock with different still bytes -> fingerprint changes
    stills = {}
    for j in jobs:
        if j["reference_still"]:
            stills[j["reference_still"]] = _img(tmp_path / "new_still.png")
        if j["location_still"]:
            stills[j["location_still"]] = _img(tmp_path / "new_loc.png")
    lock_stills(tmp_path, stills)
    with pytest.raises(GateLocked, match="different plan/route"):
        asyncio.run(execute_plan(tmp_path, _Gen(), resume=True))


def test_resume_refuses_missing_recorded_output(tmp_path):
    from forge.render_plan import execute_plan
    from forge.gates import GateLocked
    _project(tmp_path)
    local_clip = tmp_path / "clip1.mp4"
    local_clip.write_bytes(b"mp4")

    class LocalGen(_Gen):
        async def generate_single_video(self, prompt, refs, **kw):
            self.calls.append(kw)
            if len(self.calls) == 1:
                return types.SimpleNamespace(data=str(local_clip))
            if len(self.calls) == 2:
                raise RuntimeError("boom")
            return types.SimpleNamespace(data="https://provider.test/x.mp4")

    with pytest.raises(RuntimeError):
        asyncio.run(execute_plan(tmp_path, LocalGen(), resume=True))
    local_clip.unlink()  # the paid clip's file is gone
    with pytest.raises(GateLocked, match="missing/empty"):
        asyncio.run(execute_plan(tmp_path, _Gen(), resume=True))


def test_resume_recovers_submitted_job_instead_of_resubmitting(tmp_path):
    from forge.render_plan import execute_plan
    from tools.video_generator_magichour_api import RenderJobError
    jobs = _project(tmp_path)

    class CrashAfterSubmit(_Gen):
        async def generate_single_video(self, prompt, refs, **kw):
            self.calls.append(kw)
            if len(self.calls) == 1:
                return types.SimpleNamespace(data="https://provider.test/first.mp4")
            raise RenderJobError("poll died", job_id="job-77")

    with pytest.raises(RenderJobError):
        asyncio.run(execute_plan(tmp_path, CrashAfterSubmit(), resume=True))
    state = json.loads((tmp_path / ".forge" / "render_execution.json").read_text())
    assert state["jobs"]["2"]["status"] == "submitted"
    assert state["jobs"]["2"]["job_id"] == "job-77"

    class RecoveringGen(_Gen):
        def __init__(self):
            super().__init__()
            self.recovered = []

        def recover_job(self, job_id):
            self.recovered.append(job_id)
            return f"https://provider.test/recovered-{job_id}.mp4"

    gen2 = RecoveringGen()
    urls = asyncio.run(execute_plan(tmp_path, gen2, resume=True))
    assert gen2.recovered == ["job-77"]           # polled the existing job
    assert len(gen2.calls) == len(jobs) - 2       # only never-submitted clips render
    assert "https://provider.test/recovered-job-77.mp4" in urls


def test_resume_without_recover_support_fails_closed(tmp_path):
    from forge.render_plan import execute_plan
    from forge.gates import GateLocked
    from tools.video_generator_magichour_api import RenderJobError
    _project(tmp_path)

    class CrashAfterSubmit(_Gen):
        async def generate_single_video(self, prompt, refs, **kw):
            raise RenderJobError("poll died", job_id="job-88")

    with pytest.raises(RenderJobError):
        asyncio.run(execute_plan(tmp_path, CrashAfterSubmit(), resume=True))
    with pytest.raises(GateLocked, match="cannot recover"):
        asyncio.run(execute_plan(tmp_path, _Gen(), resume=True))


def test_resume_unknown_submit_outcome_never_blindly_resubmits(tmp_path):
    from forge.render_plan import execute_plan
    from forge.gates import GateLocked
    from tools.video_generator_magichour_api import RenderJobError
    _project(tmp_path)

    class CrashNoJobId(_Gen):
        async def generate_single_video(self, prompt, refs, **kw):
            raise RenderJobError("submit response lost", job_id=None)

    with pytest.raises(RenderJobError):
        asyncio.run(execute_plan(tmp_path, CrashNoJobId(), resume=True))
    state = json.loads((tmp_path / ".forge" / "render_execution.json").read_text())
    assert state["jobs"]["1"]["status"] == "unknown_outcome"
    gen2 = _Gen()
    with pytest.raises(GateLocked, match="reconcile"):
        asyncio.run(execute_plan(tmp_path, gen2, resume=True))
    assert gen2.calls == []                        # nothing resubmitted


# --------------------------------------------- render error type -----------

def test_generate_single_video_error_carries_job_id(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_LIVE", "1")
    (tmp_path / "ledger.json").write_text(json.dumps({"approved": 500, "spent": 0}))
    from tools.video_generator_magichour_api import (VideoGeneratorMagicHourAPI,
                                                     RenderJobError)
    g = VideoGeneratorMagicHourAPI("k", ledger_path=str(tmp_path / "ledger.json"),
                                   enforce_gates=False)
    monkeypatch.setattr(g, "_submit", lambda *a: ("job-abc", {}))

    def dead_poll(job_id, headers):
        raise RuntimeError("poll exploded")
    monkeypatch.setattr(g, "_poll", dead_poll)
    with pytest.raises(RenderJobError) as ei:
        asyncio.run(g.generate_single_video("p", []))
    assert ei.value.job_id == "job-abc"
    assert "do NOT resubmit blindly" in str(ei.value)


def test_recover_job_polls_without_resubmitting(tmp_path, monkeypatch):
    from tools.video_generator_magichour_api import VideoGeneratorMagicHourAPI
    g = VideoGeneratorMagicHourAPI("k", ledger_path=str(tmp_path / "l.json"))
    seen = []
    monkeypatch.setattr(g, "_poll", lambda job_id, headers: seen.append(job_id) or "url")
    assert g.recover_job("job-1") == "url"
    assert seen == ["job-1"]
    with pytest.raises(ValueError):
        g.recover_job("")


# --------------------------------- process and crash safety ----------------

def test_crash_mid_write_preserves_prior_ledger(tmp_path, monkeypatch):
    ledger = _live_ledger(tmp_path, monkeypatch)
    ledger.reserve(30)
    import forge.guard.ledger as ledger_mod
    real_replace = os.replace
    monkeypatch.setattr(ledger_mod.os, "replace",
                        lambda *a: (_ for _ in ()).throw(OSError("simulated crash")))
    with pytest.raises(OSError):
        ledger.reserve(10)
    monkeypatch.setattr(ledger_mod.os, "replace", real_replace)
    assert json.loads((tmp_path / "ledger.json").read_text())["spent"] == 30
    assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []
    ledger.reserve(10)  # ledger still usable
    assert ledger.remaining() == 60


def test_crash_mid_write_preserves_gate_state(tmp_path, monkeypatch):
    from forge.gates.common import write_json, read_json
    target = tmp_path / "still_lock.json"
    write_json(target, {"locked": True, "stills": {"a": 1}})
    import forge.gates.common as common
    monkeypatch.setattr(common.os, "replace",
                        lambda *a: (_ for _ in ()).throw(OSError("simulated crash")))
    with pytest.raises(OSError):
        write_json(target, {"locked": False})
    assert read_json(target) == {"locked": True, "stills": {"a": 1}}
    assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []


def test_ledger_works_without_fcntl(tmp_path, monkeypatch):
    """Windows-style fallback: no fcntl -> thread lock + atomic writes only."""
    monkeypatch.setitem(sys.modules, "fcntl", None)
    ledger = _live_ledger(tmp_path, monkeypatch)
    ledger.reserve(40)
    assert ledger.remaining() == 60


@pytest.mark.skipif(sys.platform.startswith("win"), reason="fcntl POSIX-only")
def test_concurrent_processes_never_overspend(tmp_path):
    """Real cross-process proof: separate Python processes racing on one
    ledger cannot spend past the approval."""
    import subprocess
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"approved": 100, "spent": 0}))
    worker = (
        "import sys; sys.path.insert(0, '.');"
        "from forge.guard.ledger import Ledger, SpendLocked;"
        "l = Ledger(sys.argv[1]);"
        "ok = 0\n"
        "for _ in range(8):\n"
        "    try: l.reserve(10); ok += 1\n"
        "    except SpendLocked: break\n"
        "print(ok)"
    )
    env = dict(os.environ, FORGE_LIVE="1")
    procs = [subprocess.Popen([sys.executable, "-c", worker, str(ledger)],
                              cwd=os.getcwd(), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
             for _ in range(8)]
    reserved = 0
    for p in procs:
        out, err = p.communicate(timeout=60)
        assert p.returncode == 0, err.decode()
        reserved += int(out.decode().strip())
    state = json.loads(ledger.read_text())
    assert state["spent"] <= 100
    assert reserved == 10        # exactly 100 credits got out the door
    assert state["spent"] == 100
