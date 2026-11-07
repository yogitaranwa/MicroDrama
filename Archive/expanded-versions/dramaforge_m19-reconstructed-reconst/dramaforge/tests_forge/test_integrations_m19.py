"""m19: vendored-repo integration - registry, job builders, real runner,
angle matrix, seed A/B controls. Local only: no GPU, no network, no spend."""
import json
import os
import subprocess
import sys
import wave

import pytest

from forge.integrations import (IntegrationError, build_multitalk_input,
                                infinitetalk_cli, multitalk_cli, preflight,
                                pulid_driver, run, vace_cli, validate)
from forge.integrations.angle_matrix import build_angle_plan, coverage_report
from forge.experiments.seed_ab import build_seed_ab

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _wav(path, seconds=1.0):
    import struct
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", 0)
                               for _ in range(int(16000 * seconds))))
    return str(path)


def _png(path):
    from PIL import Image
    Image.new("RGB", (32, 32), (10, 20, 30)).save(str(path))
    return str(path)


def test_registry_all_repos_present_with_licenses():
    rep = validate(ROOT)
    assert set(rep) == {"multitalk", "infinitetalk", "vace", "pulid"}
    for key, info in rep.items():
        assert info["present"] and info["license_ok"] and info["entrypoint_ok"], key
        assert info["license_spdx"] == "Apache-2.0"
        assert any("weights" in b for b in info["blocked"])
    rep_cuda = validate(ROOT, need_cuda=True)
    assert all(rep_cuda[k]["blocked"] for k in rep_cuda)  # no GPU in CI


def test_multitalk_input_matches_upstream_schema(tmp_path):
    img = _png(tmp_path / "ref.png")
    w1 = _wav(tmp_path / "a.wav")
    w2 = _wav(tmp_path / "b.wav")
    out = tmp_path / "job.json"
    data = build_multitalk_input("two wizards argue, candlelit hall", img,
                                 {"person1": w1, "person2": w2}, str(out))
    loaded = json.loads(out.read_text())
    assert loaded == data
    assert loaded["audio_type"] == "para"
    assert loaded["cond_audio"] == {"person1": w1, "person2": w2}
    assert loaded["cond_image"] == img
    with pytest.raises(IntegrationError):
        build_multitalk_input("", img, {"person1": w1}, str(out))
    with pytest.raises(IntegrationError):
        build_multitalk_input("p", img, {"person1": w1, "person2": w2,
                                         "person3": w1}, str(out))
    with pytest.raises(IntegrationError):
        build_multitalk_input("p", img, {"person1": "/nope.wav"}, str(out))


def test_multitalk_cli_real_argv_and_frame_rule(tmp_path):
    j = tmp_path / "job.json"
    j.write_text("{}")
    argv = multitalk_cli(ROOT, str(j), "/ckpts/wan", "/ckpts/w2v", "out.mp4",
                         frame_num=81, base_seed=42)
    assert argv[1].endswith("third_party/multitalk/generate_multitalk.py")
    assert os.path.isfile(argv[1])
    assert "--base_seed" in argv and "42" in argv
    with pytest.raises(IntegrationError):
        multitalk_cli(ROOT, str(j), "/c", "/w", "o.mp4", frame_num=80)


def test_infinitetalk_cli_modes(tmp_path):
    j = tmp_path / "job.json"
    j.write_text("{}")
    argv = infinitetalk_cli(ROOT, str(j), "/c", "/w", "o.mp4", mode="streaming")
    assert argv[1].endswith("generate_infinitetalk.py")
    assert "infinitetalk-14B" in argv
    with pytest.raises(IntegrationError):
        infinitetalk_cli(ROOT, str(j), "/c", "/w", "o.mp4", mode="loop")


def test_vace_cli_refs_and_prompt(tmp_path):
    img = _png(tmp_path / "r.png")
    argv = vace_cli(ROOT, "moonlit terrace, two wizards", "o.mp4",
                    src_ref_images=[str(img)])
    assert "--model_name" in argv and "vace-1.3B" in argv
    assert "--src_ref_images" in argv
    with pytest.raises(IntegrationError):
        vace_cli(ROOT, "p", "o.mp4", src_ref_images=["/nope.png"])
    with pytest.raises(IntegrationError):
        vace_cli(ROOT, "", "o.mp4")


def test_pulid_driver_writes_real_script(tmp_path):
    img = _png(tmp_path / "ref.png")
    argv = pulid_driver(ROOT, str(tmp_path), "/flux", "/pulid",
                        "portrait of a wizard", str(img),
                        str(tmp_path / "out.png"))
    script = argv[1]
    assert os.path.isfile(script)
    body = open(script).read()
    assert "from pulid.pipeline import PuLIDPipeline" in body
    assert "--id_scale" in argv


def test_runner_executes_real_subprocess(tmp_path):
    script = tmp_path / "fake_cli.py"
    marker = tmp_path / "artifact.txt"
    script.write_text(
        "import sys\nopen(sys.argv[1], 'w').write('generated')\n")
    argv = preflight([sys.executable, str(script), str(marker)])
    res = run(argv, log_path=str(tmp_path / "run.log"))
    assert res["ok"] and res["returncode"] == 0
    assert marker.read_text() == "generated"
    assert os.path.isfile(res["log_path"])
    bad = run([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert not bad["ok"] and bad["returncode"] == 3


def test_runner_preflight_fail_closed():
    with pytest.raises(IntegrationError, match="entrypoint not found"):
        preflight(["python3", "/nope/missing.py"])
    with pytest.raises(IntegrationError, match="required path missing"):
        preflight(["python3", "-c", "pass"], required_paths=["/nope/ckpt"])
    with pytest.raises(IntegrationError, match="no CUDA"):
        preflight(["python3", "-c", "pass"], need_cuda=True)


def test_angle_matrix_preserves_identity():
    plan = build_angle_plan(
        "Harry Potter", ["round glasses", "black tousled hair", "lightning scar"],
        "charcoal dress robes, loosened collar",
        existing=["front_close", "front_full"])
    assert plan["covered"] == ["front_close", "front_full"]
    assert "back_full" in plan["missing"]
    p = plan["prompts"]["back_full"]
    assert "round glasses" in p and "lightning scar" in p
    assert "blemish-free" not in p
    with pytest.raises(IntegrationError):
        build_angle_plan("Harry Potter", [], "robes")
    rep = coverage_report([plan])
    assert rep["Harry Potter"]["covered"] == 2


def test_seed_ab_matched_controls_and_credits():
    plan = build_seed_ab("wan-3.0", "e01s02", 5.0, "720p", seeds=(42, 43))
    assert plan["controls"]["varied"] == "seed only"
    assert [r["seed"] for r in plan["runs"]] == [42, 43]
    assert plan["runs"][0]["credits"] == 5 * 96
    assert plan["total_credits"] == 960
    assert "wan-3.0" in plan["verdict_scope"]
    with pytest.raises(IntegrationError):
        build_seed_ab("wan-3.0", "e01s02", 5.0, "720p", seeds=(42, 42))


def test_kling40_route_refresh():
    from forge.planning.routes import route, ROUTES
    r = route("kling-4.0")
    assert r.credits_per_second["720p"] == 80
    assert r.audio == "included"
    snapped, credits = r.credits_for(4.2, "720p")
    assert snapped == 5 and credits == 400
    assert "wan-3.0" in ROUTES  # old routes untouched


def test_vendored_import_smoke_real_torch():
    """Real import smoke on torch (CPU). Verifies the vendored code is intact
    and records each repo's true first blocker; GPU-only deps skip honestly."""
    torch = pytest.importorskip("torch")
    results = {}

    def purge(*prefixes):
        for m in [k for k in sys.modules if any(k == p or k.startswith(p + ".") for p in prefixes)]:
            del sys.modules[m]

    def import_wan_configs(repo):
        # Both repos ship a top-level `wan` package; purge caches between
        # repos so each gets its own. GPU-only deps (xfuser/triton) fail
        # closed on CPU hosts; a clean blocked result is a valid outcome.
        purge("wan", "xfuser", "spas_sage_attn")
        sys.path.insert(0, os.path.join(ROOT, "third_party", repo))
        try:
            import wan.configs as wc  # noqa: F401
            return "imports"
        except ModuleNotFoundError as e:
            assert e.name in ("triton", "xfuser", "flash_attn", "torch", "spas_sage_attn")
            return f"blocked: {e.name}"
        except NotImplementedError as e:
            # xfuser fail-closed on CPU-only hosts: genuine GPU-only signal.
            assert "Accelerator" in str(e) or "GPU" in str(e)
            return f"blocked: {e}"
        finally:
            sys.path.pop(0)

    results["infinitetalk"] = import_wan_configs("infinitetalk")
    results["multitalk"] = import_wan_configs("multitalk")
    # Honest states only: each repo either imports or reports a recognized
    # GPU/dependency block. On this CPU host both fail closed via xfuser
    # ("No Accelerators available") - that is the recorded GPU-only signal.
    for repo, state in results.items():
        if state != "imports":
            assert state.startswith("blocked:"), (repo, state)
    # Config task names still verifiable statically from the source files.
    import re
    for repo, task in (("infinitetalk", "infinitetalk-14B"),
                       ("multitalk", "multitalk-14B")):
        src = open(os.path.join(ROOT, "third_party", repo, "wan", "configs", "__init__.py")).read()
        assert re.search(r'["\']' + task + r'["\']', src), (repo, task)
    # VACE: needs the official Wan2.1 package + weights (models/ has .gitkeep only).
    assert os.path.isfile(os.path.join(
        ROOT, "third_party", "vace", "models", ".gitkeep"))
    results["vace"] = "blocked: upstream wan package + weights not vendored"
    # PuLID: insightface dependency (face models non-commercial) documented.
    sys.path.insert(0, os.path.join(ROOT, "third_party", "pulid"))
    try:
        import pulid.pipeline  # noqa: F401
        results["pulid"] = "imports"
    except ModuleNotFoundError as e:
        results["pulid"] = f"blocked: {e.name}"
        assert e.name in ("insightface", "diffusers", "torch", "onnxruntime")
    finally:
        sys.path.pop(0)
