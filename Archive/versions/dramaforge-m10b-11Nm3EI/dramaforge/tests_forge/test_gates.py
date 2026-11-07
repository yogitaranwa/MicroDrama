"""Gate tests: stills-first, proof scene, continuity, review. Stdlib + PIL only."""
import json
import pytest
from pathlib import Path

from forge.gates import (GateLocked, lock_stills, require_still_lock,
                         record_proof, signoff_proof, require_proof,
                         review_episode, signoff, require_signoff,
                         frame_features, drift_score)
from forge.gates.deliver import deliver
from forge.gates.review import silent_stretches
from forge.gates.continuity import histogram_intersection, grid_l1


def _img(path, colour):
    from PIL import Image
    Image.new("RGB", (64, 64), colour).save(path)
    return str(path)


@pytest.fixture
def still(tmp_path):
    return _img(tmp_path / "harry.png", (120, 60, 40))


# --- gate 1: stills first -------------------------------------------------

def test_render_blocked_without_still_lock(tmp_path):
    with pytest.raises(GateLocked, match="stills"):
        require_still_lock(tmp_path)

def test_lock_then_pass(tmp_path, still):
    lock_stills(tmp_path, {"character:harry": still})
    assert require_still_lock(tmp_path, needed=["character:harry"])["locked"]

def test_lock_detects_edited_still(tmp_path, still):
    lock_stills(tmp_path, {"character:harry": still})
    _img(tmp_path / "harry.png", (1, 2, 3))  # wardrobe "fixed" mid-production
    with pytest.raises(GateLocked, match="changed after locking"):
        require_still_lock(tmp_path)

def test_needed_still_missing(tmp_path, still):
    lock_stills(tmp_path, {"character:harry": still})
    with pytest.raises(GateLocked, match="missing required stills"):
        require_still_lock(tmp_path, needed=["location:hall"])

# --- gate 2: proof scene ---------------------------------------------------

def _video(tmp_path, name="proof.mp4"):
    p = tmp_path / name
    p.write_bytes(b"fake-video-bytes")
    return str(p)

def test_episode_blocked_without_proof(tmp_path, still):
    lock_stills(tmp_path, {"character:harry": still})
    with pytest.raises(GateLocked, match="proof scene"):
        require_proof(tmp_path)

def test_proof_must_stay_small(tmp_path, still):
    lock_stills(tmp_path, {"character:harry": still})
    v = _video(tmp_path)
    with pytest.raises(GateLocked, match="too big"):
        record_proof(tmp_path, v, n_shots=9, seconds=95, locations=["hall"])
    with pytest.raises(GateLocked, match="one room"):
        record_proof(tmp_path, v, n_shots=3, seconds=19, locations=["hall", "yard"])

def test_proof_signoff_flow(tmp_path, still):
    lock_stills(tmp_path, {"character:harry": still})
    v = _video(tmp_path)
    record_proof(tmp_path, v, n_shots=3, seconds=19, locations=["kitchen"])
    with pytest.raises(GateLocked, match="not human-approved"):
        require_proof(tmp_path)
    signoff_proof(tmp_path, "reviewer-a", video_path=v)
    assert require_proof(tmp_path)["status"] == "approved"

def test_proof_signoff_rejects_different_file(tmp_path, still):
    lock_stills(tmp_path, {"character:harry": still})
    _video(tmp_path)
    record_proof(tmp_path, str(tmp_path / "proof.mp4"), 3, 19, ["kitchen"])
    other = _video(tmp_path, "other.mp4")
    from pathlib import Path as _P
    _P(other).write_bytes(b"different-bytes")
    with pytest.raises(GateLocked, match="differs"):
        signoff_proof(tmp_path, "reviewer-a", video_path=other)

# --- continuity metrics ----------------------------------------------------

def test_metrics_sane():
    assert histogram_intersection([0.5, 0.5], [0.5, 0.5]) == 1.0
    assert histogram_intersection([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert grid_l1([0.0, 1.0], [1.0, 0.0]) == 1.0

def test_drift_score_identical_vs_different(tmp_path):
    a = frame_features(_img(tmp_path / "a.png", (120, 60, 40)))
    b = frame_features(_img(tmp_path / "b.png", (120, 60, 40)))
    c = frame_features(_img(tmp_path / "c.png", (10, 200, 30)))
    assert drift_score(a, b) < 0.01
    assert drift_score(a, c) > 0.35

# --- gate 3: review + delivery ----------------------------------------------

def test_silent_stretch_detection():
    samples = [(t, -20.0) for t in range(0, 10)] + [(t, -60.0) for t in range(10, 20)] + [(20.0, -20.0)]
    assert silent_stretches(samples, max_silent_s=3.0) == [(10.0, 19.0)]
    assert silent_stretches(samples, max_silent_s=30.0) == []

def _episode(tmp_path):
    p = tmp_path / "ep.mp4"
    p.write_bytes(b"episode-bytes")
    return str(p)

def test_review_flags_unfinished_lipsync_and_silence(tmp_path):
    ep = _episode(tmp_path)
    rep = review_episode(tmp_path, ep, [("s1", 10.0), ("s2", 10.0)],
                         loudness_samples=[(t, -60.0) for t in range(0, 20)],
                         lip_sync_done=False)
    assert rep["status"] == "issues"
    assert any("lip-sync" in i for i in rep["issues"])
    assert any("silent stretch" in i for i in rep["issues"])

def test_delivery_blocked_until_human_signoff(tmp_path):
    ep = _episode(tmp_path)
    with pytest.raises(GateLocked):
        deliver(tmp_path, ep, tmp_path / "out")
    review_episode(tmp_path, ep, [("s1", 19.0)],
                   loudness_samples=[(t / 2, -20.0) for t in range(0, 40)],
                   lip_sync_done=True)
    with pytest.raises(GateLocked):
        deliver(tmp_path, ep, tmp_path / "out")  # reviewed but not signed
    signoff(tmp_path, "reviewer-a")
    out = deliver(tmp_path, ep, tmp_path / "out")
    assert Path(out).read_bytes() == b"episode-bytes"

def test_signoff_invalidated_by_new_cut(tmp_path):
    ep = _episode(tmp_path)
    review_episode(tmp_path, ep, [("s1", 19.0)], lip_sync_done=True)
    signoff(tmp_path, "reviewer-a")
    Path(ep).write_bytes(b"episode-bytes-v2")  # new cut after signoff
    with pytest.raises(GateLocked, match="changed after signoff"):
        require_signoff(tmp_path, ep)


def _load_generator():
    """Load the MagicHour video generator by path with interfaces stubbed,
    so gate wiring is tested without the heavy tools/ dependency chain."""
    import importlib.util, sys, types
    vo = types.ModuleType("interfaces.video_output")
    class VideoOutput:
        def __init__(self, **kw): self.__dict__.update(kw)
    vo.VideoOutput = VideoOutput
    pkg = types.ModuleType("interfaces"); pkg.video_output = vo
    sys.modules.setdefault("interfaces", pkg)
    sys.modules["interfaces.video_output"] = vo
    spec = importlib.util.spec_from_file_location(
        "vh_under_test", "tools/video_generator_magichour_api.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.VideoGeneratorMagicHourAPI

# --- render chokepoint wiring ------------------------------------------------

def test_generator_refuses_episode_render_without_gates(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_LIVE", "1")
    (tmp_path / "ledger.json").write_text(json.dumps({"approved": 1000, "spent": 0}))
    VideoGeneratorMagicHourAPI = _load_generator()
    g = VideoGeneratorMagicHourAPI("k", ledger_path=str(tmp_path / "ledger.json"))
    with pytest.raises(GateLocked):  # GateLocked is a SpendLocked
        import asyncio
        asyncio.run(g.generate_single_video("p", []))

def test_generator_proof_mode_needs_stills_only(tmp_path, monkeypatch, still):
    monkeypatch.setenv("FORGE_LIVE", "1")
    monkeypatch.delenv("FORGE_GATES", raising=False)
    (tmp_path / "ledger.json").write_text(json.dumps({"approved": 1000, "spent": 0}))
    lock_stills(tmp_path, {"character:harry": still})
    VideoGeneratorMagicHourAPI = _load_generator()
    g = VideoGeneratorMagicHourAPI("k", ledger_path=str(tmp_path / "ledger.json"),
                                   render_mode="proof", project_dir=str(tmp_path))
    # gates pass; the paid call itself must fail (no network/key), proving the
    # gate ran BEFORE the request and did not block it
    import asyncio
    with pytest.raises(Exception) as exc:
        asyncio.run(g.generate_single_video("p", []))
    assert not isinstance(exc.value, GateLocked)

def test_generator_render_mode_env_override(tmp_path, monkeypatch, still):
    monkeypatch.setenv("FORGE_LIVE", "1")
    monkeypatch.setenv("FORGE_RENDER_MODE", "proof")
    (tmp_path / "ledger.json").write_text(json.dumps({"approved": 1000, "spent": 0}))
    lock_stills(tmp_path, {"character:harry": still})
    g = _load_generator()("k", ledger_path=str(tmp_path / "ledger.json"),
                          project_dir=str(tmp_path))
    assert g.render_mode == "proof"  # config default 'episode' overridden

def test_gates_bypass_never_touches_spend_guard(tmp_path, monkeypatch):
    # FORGE_GATES=0 skips process gates, but the credit ledger still refuses
    monkeypatch.setenv("FORGE_GATES", "0")
    monkeypatch.delenv("FORGE_LIVE", raising=False)
    g = _load_generator()("k", ledger_path=str(tmp_path / "ledger.json"))
    from forge.guard.ledger import SpendLocked
    import asyncio
    with pytest.raises(SpendLocked):  # SpendLocked, not GateLocked: ledger did it
        asyncio.run(g.generate_single_video("p", []))
    assert json.loads((tmp_path / "ledger.json").read_text() if (tmp_path / "ledger.json").exists() else '{"spent": 0}')["spent"] == 0
