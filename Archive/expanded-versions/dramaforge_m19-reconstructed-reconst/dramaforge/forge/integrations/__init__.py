"""m19: vendored open-source model integration (additive; nothing removed).

Real execution paths into third_party/ copies of MultiTalk, InfiniteTalk,
VACE and PuLID. Everything here is fail-closed: a job that cannot run on
this host says exactly why (weights, CUDA, inputs) instead of pretending."""
from .registry import REPOS, VendoredRepo, IntegrationError, validate
from .jobs import (build_multitalk_input, multitalk_cli, infinitetalk_cli,
                   vace_cli, pulid_driver)
from .runner import preflight, run

__all__ = ["REPOS", "VendoredRepo", "IntegrationError", "validate",
           "build_multitalk_input", "multitalk_cli", "infinitetalk_cli",
           "vace_cli", "pulid_driver", "preflight", "run"]
