"""The fixture app source, for tests that must not depend on the network or the release."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import release_source

FIXTURE_APP = Path(__file__).parent / "fixtures" / "app_source"


@pytest.fixture
def fixture_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """tests/fixtures/app_source instead of the latest release (OW_APP_SOURCE), for one test."""
    monkeypatch.setenv("OW_APP_SOURCE", str(FIXTURE_APP))
    release_source.root.cache_clear()
    yield FIXTURE_APP
    release_source.root.cache_clear()  # the next test reads the release again
