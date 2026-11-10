"""Testes de arquitetura: rodam os contratos do import-linter (.importlinter)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_import_contracts_hold():
    result = subprocess.run(
        [sys.executable, "-m", "importlinter.cli", "--config", str(ROOT / ".importlinter")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_feature_slice_has_a_handler():
    slices = [p for p in (ROOT / "app" / "application").iterdir() if p.is_dir() and not p.name.startswith("_")]
    assert slices
    for folder in slices:
        assert (folder / "handler.py").exists(), f"{folder.name} sem handler.py"
