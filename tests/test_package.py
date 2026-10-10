from __future__ import annotations

import importlib

import pytest

MODULES = [
    "config",
    "exceptions",
    "plotting",
    "data",
    "spread",
    "signal",
    "backtest",
    "metrics",
    "stability",
    "short_interest",
    "simulation",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name: str) -> None:
    module = importlib.import_module(f"pairs.{name}")
    assert module.__doc__, f"pairs.{name} has no module docstring"
