Layout: ViMax tree at root (agents/pipelines), plus forge/ (guard, llm, audio, assemble) and tools/*magichour*.
Config: configs/nvidia_magichour.yaml. Paid calls are locked: they need FORGE_LIVE=1 and an approved cap in .forge/ledger.json.
Tests: python -m pytest tests_forge
