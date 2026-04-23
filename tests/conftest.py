"""Shared pytest fixtures and CLI options for the test suite."""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run tests that make real LLM API calls (requires API keys and Ollama).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: marks tests that call real LLM APIs — skipped unless --live is passed",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    if not config.getoption("--live"):
        skip = pytest.mark.skip(reason="pass --live to run real-LLM tests")
        for item in items:
            if item.get_closest_marker("live"):
                item.add_marker(skip)
