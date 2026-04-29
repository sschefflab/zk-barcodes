"""
pytest configuration and shared fixtures.

Utility functions live in helpers.py; this file only contains pytest hooks
and fixtures so that conftest stays importable the normal pytest way.
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--no-setup",
        action="store_true",
        default=False,
        help="Skip CirC compile+setup (assume prover/verifier keys already exist).",
    )
