"""Tests for util helpers."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from energy_consumption_visualization.config import OutputConfig
from energy_consumption_visualization.render.colors import DEEP_TEAL, MIDNIGHT_INK
from energy_consumption_visualization.util import (
    get_as_list,
    get_color,
    get_output_paths,
    parse_duration,
    parse_sites,
)


def test_parse_duration_unit_strings():
    assert parse_duration('30s') == timedelta(seconds=30)
    assert parse_duration('1m') == timedelta(minutes=1)
    assert parse_duration('15m') == timedelta(minutes=15)
    assert parse_duration('12h') == timedelta(hours=12)
    assert parse_duration('1d') == timedelta(days=1)
    assert parse_duration('1w') == timedelta(weeks=1)
    assert parse_duration('1.5h') == timedelta(hours=1.5)


def test_parse_duration_bare_numbers_and_timedelta():
    assert parse_duration(30) == timedelta(seconds=30)
    assert parse_duration(1.5) == timedelta(seconds=1.5)
    delta = timedelta(minutes=5)
    assert parse_duration(delta) is delta


def test_parse_duration_invalid():
    with pytest.raises(ValueError, match='Invalid duration'):
        parse_duration('bogus')
    with pytest.raises(ValueError, match='Invalid duration'):
        parse_duration(None)


def test_parse_sites_happy_path():
    site_map, apartments = parse_sites([
        {'id': 'site_a', 'label': 'A Street', 'n_apartments': 10},
        {'id': 'site_b', 'label': 'B Street', 'n_apartments': 20},
    ])
    assert site_map == {'site_a': 'A Street', 'site_b': 'B Street'}
    assert apartments == {'site_a': 10, 'site_b': 20}


def test_parse_sites_empty():
    with pytest.raises(RuntimeError, match='non-empty'):
        parse_sites([])


def test_parse_sites_missing_keys():
    with pytest.raises(RuntimeError, match='id and label'):
        parse_sites([{'id': 'site_a'}])


def test_parse_sites_invalid_apartments():
    with pytest.raises(RuntimeError, match='positive int n_apartments'):
        parse_sites([{'id': 'site_a', 'label': 'A', 'n_apartments': 'x'}])
    with pytest.raises(RuntimeError, match='must be positive'):
        parse_sites([{'id': 'site_a', 'label': 'A', 'n_apartments': 0}])
    with pytest.raises(RuntimeError, match='must be positive'):
        parse_sites([{'id': 'site_a', 'label': 'A', 'n_apartments': -1}])


def test_get_color():
    assert get_color('deep teal') == DEEP_TEAL
    assert get_color('midnight ink') == MIDNIGHT_INK
    with pytest.raises(KeyError):
        get_color('not a color')


def test_get_as_list():
    assert get_as_list('foo') == ['foo']
    assert get_as_list(['a', 'b']) == ['a', 'b']
    with pytest.raises(ValueError, match='Invalid value'):
        get_as_list(('a', 'b'))


def test_get_output_paths_creates_parents_and_formats(tmp_path: Path):
    config = OutputConfig(
        output_path=[
            str(tmp_path / '{date}' / '{site_id}'),
            str(tmp_path / 'latest' / '{site_id}'),
        ],
        output_file_name='{measurement}-ranking.{ext}',
        output_date_format='%Y%m%d-%H%M',
    )
    processing_date = datetime(2026, 1, 15, 12, 30, tzinfo=timezone.utc)
    out_svg, out_png = get_output_paths(config, 'site_a', 'heat', processing_date)

    assert len(out_svg) == 2
    assert len(out_png) == 2
    assert out_svg[0].name == 'heat-ranking.svg'
    assert out_png[0].name == 'heat-ranking.png'
    assert '20260115-1230' in str(out_svg[0])
    assert 'site_a' in str(out_svg[0])
    assert (tmp_path / '20260115-1230' / 'site_a').is_dir()
    assert (tmp_path / 'latest' / 'site_a').is_dir()
    assert out_svg[1].parent == tmp_path / 'latest' / 'site_a'
