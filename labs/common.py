"""Shared helpers for the process-mining course laboratories."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[1]
VARIANT_LAB_PATH = REPO_ROOT / "labs/01-variant-pareto/variant_pareto_lab.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_variant_lab() -> ModuleType:
    return load_module("variant_pareto_lab", VARIANT_LAB_PATH)
