import os, json, asyncio, pytest
from forge.guard.ledger import Ledger, SpendLocked
from tools import VideoGeneratorMagicHourAPI

def test_locked_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("FORGE_LIVE", raising=False)
    with pytest.raises(SpendLocked):
        Ledger(tmp_path/"l.json").reserve(1)

def test_cap_enforced(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_LIVE", "1")
    p = tmp_path/"l.json"; p.write_text(json.dumps({"approved": 100, "spent": 0}))
    l = Ledger(p); l.reserve(60)
    with pytest.raises(SpendLocked):
        l.reserve(60)
    assert l.remaining() == 40

def test_video_backend_refuses_without_approval(tmp_path, monkeypatch):
    monkeypatch.delenv("FORGE_LIVE", raising=False)
    g = VideoGeneratorMagicHourAPI("k", ledger_path=str(tmp_path/"l.json"))
    with pytest.raises(SpendLocked):
        asyncio.run(g.generate_single_video("x", []))
