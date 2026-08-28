"""Shared fixtures for energy-consumption-visualization unit tests."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest

from energy_consumption_visualization.config import (
    ChannelConfig,
    CompareConfig,
    RankingConfig,
)
from test.helpers import (
    TEMPLATE_SVG,
    FakeHistoryProvider,
    make_channel_config,
    make_compare_config,
    make_ranking_config,
)


@pytest.fixture
def template_path() -> Path:
    return TEMPLATE_SVG


@pytest.fixture
def start_time() -> datetime:
    return datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def ranking_config(template_path: Path, tmp_path: Path) -> RankingConfig:
    return make_ranking_config(template_path, tmp_path)


@pytest.fixture
def compare_config(template_path: Path, tmp_path: Path) -> CompareConfig:
    return make_compare_config(template_path, tmp_path)


@pytest.fixture
def channel_config() -> ChannelConfig:
    return make_channel_config()


@pytest.fixture
def fake_provider() -> FakeHistoryProvider:
    return FakeHistoryProvider()


@pytest.fixture
def logger() -> logging.Logger:
    return logging.getLogger('energy_consumption_visualization.test')
