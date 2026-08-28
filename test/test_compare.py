"""Tests for compare series logic and SVG/PNG smoke render."""
from datetime import timedelta

import pandas as pd
import pytest

from energy_consumption_visualization.postprocess.compare import (
    _build_extra_series,
    _build_measurement_series,
    compare,
)
from test.helpers import make_samples


def test_build_measurement_series_empty_samples(compare_config, start_time):
    series = _build_measurement_series('heat', 'site_a', [], compare_config)
    assert isinstance(series, pd.Series)
    assert series.empty


def test_build_measurement_series_resamples(compare_config, start_time):
    samples = make_samples(start_time, [1.0, 2.0, 3.0], step=timedelta(hours=1))
    series = _build_measurement_series('heat', 'site_a', samples, compare_config)
    assert list(series.values) == pytest.approx([1.0, 2.0, 3.0])


def test_build_extra_series_keyed_by_dp_name(compare_config, start_time):
    extra_configs = {a.history_provider.dp_name: a for a in compare_config.compare_against}
    histories = {
        'outdoor_temp': make_samples(start_time, [5.0, 6.0]),
        'missing': [],
    }
    extra_configs['missing'] = extra_configs['outdoor_temp']
    series = _build_extra_series(histories, extra_configs)
    assert set(series) == {'outdoor_temp'}
    assert list(series['outdoor_temp'].values) == pytest.approx([5.0, 6.0])


def test_compare_smoke_writes_svg_and_png(compare_config, start_time, tmp_path):
    samples = make_samples(start_time, [10.0, 12.0, 8.0, 9.0])
    extra = {'outdoor_temp': make_samples(start_time, [-2.0, -1.0, 0.0, 1.0])}
    compare('heat', 'site_a', samples, extra, compare_config, start_time)

    date_dir = start_time.strftime(compare_config.output_date_format)
    svg_path = tmp_path / date_dir / 'site_a' / 'heat-compare.svg'
    png_path = tmp_path / date_dir / 'site_a' / 'heat-compare.png'
    assert svg_path.is_file()
    assert png_path.is_file()
    svg_text = svg_path.read_text(encoding='utf-8')
    assert 'A Street' in svg_text
    assert png_path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
