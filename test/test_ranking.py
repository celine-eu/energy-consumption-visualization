"""Tests for ranking series logic, emoticons, and SVG/PNG smoke render."""
from datetime import timedelta
from math import ceil

import pandas as pd
import pytest

from energy_consumption_visualization.postprocess.ranking import (
    _EMOJI_DIR,
    _build_ranking_table,
    _build_resampled_series,
    _median_across_sites,
    _rank_sites,
    _samples_to_series,
    _select_emoticon,
    ranking,
)
from test.helpers import make_samples


def test_samples_to_series_resamples_sum(start_time):
    samples = make_samples(start_time, [10.0, 20.0, 30.0], step=timedelta(hours=1))
    series = _samples_to_series(samples, timedelta(hours=1))
    assert list(series.values) == pytest.approx([10.0, 20.0, 30.0])


def test_build_resampled_series_weights_by_apartments_and_skips_empty(
        ranking_config, start_time,
    ):
    histories = {
        'site_a': make_samples(start_time, [10.0, 20.0]),
        'site_b': [],
        'site_c': make_samples(start_time, [5.0, 5.0]),
    }
    series_by_site = _build_resampled_series('heat', histories, ranking_config)
    assert set(series_by_site) == {'site_a', 'site_c'}
    assert list(series_by_site['site_a'].values) == pytest.approx([1.0, 2.0])
    assert list(series_by_site['site_c'].values) == pytest.approx([1.0, 1.0])


def test_rank_sites_lowest_sum_first(start_time):
    index = pd.date_range(start_time, periods=2, freq='h')
    series_by_site = {
        'site_high': pd.Series([10.0, 10.0], index=index),
        'site_low': pd.Series([1.0, 1.0], index=index),
        'site_mid': pd.Series([5.0, 5.0], index=index),
    }
    ranked = _rank_sites(series_by_site)
    assert list(ranked.keys()) == ['site_low', 'site_mid', 'site_high']


def test_median_across_sites(start_time):
    index = pd.date_range(start_time, periods=2, freq='h')
    series_by_site = {
        'a': pd.Series([1.0, 10.0], index=index),
        'b': pd.Series([3.0, 20.0], index=index),
        'c': pd.Series([5.0, 30.0], index=index),
    }
    median = _median_across_sites(series_by_site)
    assert list(median.values) == pytest.approx([3.0, 20.0])


def test_build_ranking_table_headers_values_and_highlights(ranking_config, start_time):
    index = pd.date_range(start_time, periods=1, freq='h')
    series_by_site = {
        'site_a': pd.Series([2.0], index=index),
        'site_b': pd.Series([4.0], index=index),
        'site_c': pd.Series([20.0], index=index),
    }
    headers, rows, highlights = _build_ranking_table(series_by_site, ranking_config)
    assert headers == ['Rank', 'Address', 'Heat']
    assert rows[0][0] == 1
    assert rows[0][1] == 'A Street'
    assert rows[0][2] == '2 kWh'
    assert highlights['site_a'] == 0
    assert highlights['site_b'] == 1
    assert highlights['site_c'] == 2
    assert rows[2][1] == 'C Street'


def test_select_emoticon_rank_bands():
    assert _select_emoticon(1, 6) == _EMOJI_DIR / 'party_popper.svg'
    assert _select_emoticon(6, 6) == _EMOJI_DIR / 'face_with_crossed_out_eyes.svg'
    assert _select_emoticon(2, 6) == _EMOJI_DIR / 'slightly_smiling_face.svg'
    assert _select_emoticon(3, 6) == _EMOJI_DIR / 'neutral_face.svg'
    assert _select_emoticon(4, 6) == _EMOJI_DIR / 'neutral_face.svg'
    assert _select_emoticon(5, 6) == _EMOJI_DIR / 'slightly_frowning_face.svg'
    for name in (
        'party_popper.svg',
        'face_with_crossed_out_eyes.svg',
        'slightly_smiling_face.svg',
        'neutral_face.svg',
        'slightly_frowning_face.svg',
    ):
        assert (_EMOJI_DIR / name).is_file()
    assert ceil(6 / 3) == 2


def test_ranking_smoke_writes_svg_and_png(ranking_config, start_time, tmp_path):
    histories = {
        'site_a': make_samples(start_time, [10.0, 12.0, 8.0, 9.0]),
        'site_b': make_samples(start_time, [40.0, 42.0, 38.0, 41.0]),
        'site_c': make_samples(start_time, [50.0, 55.0, 52.0, 51.0]),
    }
    ranking('heat', histories, ranking_config, start_time)

    date_dir = start_time.strftime(ranking_config.output_date_format)
    for site_id, label in ranking_config.site_map.items():
        svg_path = tmp_path / date_dir / site_id / 'heat-ranking.svg'
        png_path = tmp_path / date_dir / site_id / 'heat-ranking.png'
        assert svg_path.is_file()
        assert png_path.is_file()
        svg_text = svg_path.read_text(encoding='utf-8')
        assert label in svg_text
        assert png_path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
