"""Tests for channel / ranking / compare config loading."""
from datetime import timedelta
from pathlib import Path

import pytest

from energy_consumption_visualization.config import ChannelConfig
from test.helpers import TEMPLATE_SVG


def _sites():
    return [
        {'id': 'site_a', 'label': 'A Street', 'n_apartments': 10},
        {'id': 'site_b', 'label': 'B Street', 'n_apartments': 20},
    ]


def _ranking_dict(template_path: Path, **overrides) -> dict:
    data = {
        'template_path': str(template_path),
        'ranking_slot': 'slot2',
        'ranking_include_emoticon': True,
        'ranking_avg_label': 'average',
        'ranking_avg_color': 'golden amber',
        'ranking_highlight_color': 'terracotta',
        'chart_slot': 'slot1',
        'chart_time_zone': 'FI',
        'chart_label': 'Heat',
        'chart_unit': 'kWh',
        'chart_resample_bin_width': '1h',
        'title_slot': 'title',
        'title_label': 'Ranking',
        'title_font_size': 40,
        'title_color': 'deep teal',
    }
    data.update(overrides)
    return data


def _compare_against_dict(**overrides) -> dict:
    data = {
        'chart_slot': 'slot3',
        'chart_title': 'Outdoor',
        'chart_label': 'Temp',
        'chart_unit': 'C',
        'chart_resample_bin_width': '3h',
        'chart_resample_method': 'mean',
        'chart_time_zone': 'FI',
        'chart_dpi': 110,
        'chart_text_color': 'midnight ink',
        'history_provider': {'dp_name': 'outdoor_temp'},
    }
    data.update(overrides)
    return data


def _compare_dict(template_path: Path, **overrides) -> dict:
    data = {
        'template_path': str(template_path),
        'against': [_compare_against_dict()],
        'chart_slot': 'slot1',
        'chart_time_zone': 'FI',
        'chart_title': 'Site heat',
        'chart_label': 'Heat',
        'chart_unit': 'kWh',
        'chart_resample_bin_width': '1h',
        'chart_resample_method': 'sum',
        'title_label': 'Compare {site_label}',
        'title_font_size': 40,
        'title_color': 'deep teal',
    }
    data.update(overrides)
    return data


def _channel_entry(template_path: Path, **overrides) -> dict:
    data = {
        'sites': _sites(),
        'stream_template': 'reg:{site_id}:heat',
        'history_window': '1w',
        'history_provider': {
            'dp_name': 'heat_kwh',
            'dp_data_provider': 'data_provider',
        },
        'ranking': _ranking_dict(template_path),
        'compare': _compare_dict(template_path),
    }
    data.update(overrides)
    return data


def test_load_channel_configs_production_shape():
    configs = ChannelConfig.load_channel_configs({
        'heat': _channel_entry(TEMPLATE_SVG),
    })
    assert len(configs) == 1
    config = configs[0]
    assert config.name == 'heat'
    assert config.site_ids == ['site_a', 'site_b']
    assert config.history_window == timedelta(weeks=1)
    assert config.history_provider.dp_name == 'heat_kwh'
    assert config.ranking_config is not None
    assert config.ranking_config.chart_resample_bin_width == timedelta(hours=1)
    assert config.ranking_config.apartments_by_site['site_a'] == 10
    assert config.compare_config is not None
    assert len(config.compare_config.compare_against) == 1
    assert config.compare_config.compare_against[0].history_provider.dp_name == 'outdoor_temp'
    assert config.history_provider.retry_n == 0
    assert config.history_provider.retry_wait_s == 5
    assert config.compare_config.compare_against[0].history_provider.retry_n == 0
    assert config.compare_config.compare_against[0].history_provider.retry_wait_s == 5


def test_history_provider_retry_from_config():
    entry = _channel_entry(TEMPLATE_SVG)
    entry['history_provider'] = {
        **entry['history_provider'],
        'retry_n': 3,
        'retry_wait_s': 2.5,
    }
    config = ChannelConfig.load_channel_configs({'heat': entry})[0]
    assert config.history_provider.retry_n == 3
    assert config.history_provider.retry_wait_s == 2.5


def test_stream_for_fills_site_id():
    config = ChannelConfig.load_channel_configs({
        'heat': _channel_entry(TEMPLATE_SVG),
    })[0]
    assert config.stream_for('site_a') == 'reg:site_a:heat'
    assert config.stream_for('site_b') == 'reg:site_b:heat'


def test_empty_channels_raises():
    with pytest.raises(RuntimeError, match='empty'):
        ChannelConfig.load_channel_configs({})
    with pytest.raises(RuntimeError, match='empty'):
        ChannelConfig.load_channel_configs(None)


def test_missing_channel_field_raises():
    entry = _channel_entry(TEMPLATE_SVG)
    del entry['stream_template']
    with pytest.raises(RuntimeError, match='Missing config field for channel heat'):
        ChannelConfig.load_channel_configs({'heat': entry})


def test_ranking_null_and_omitted_compare():
    entry = _channel_entry(TEMPLATE_SVG, ranking=None)
    del entry['compare']
    config = ChannelConfig.load_channel_configs({'heat': entry})[0]
    assert config.ranking_config is None
    assert config.compare_config is None


def test_ranking_value_decimals_negative():
    entry = _channel_entry(
        TEMPLATE_SVG,
        ranking=_ranking_dict(TEMPLATE_SVG, ranking_value_decimals=-1),
    )
    with pytest.raises(RuntimeError, match='Invalid rating config'):
        ChannelConfig.load_channel_configs({'heat': entry})


def test_ranking_load_requires_existing_template(tmp_path: Path):
    missing = tmp_path / 'missing.svg'
    entry = _channel_entry(
        TEMPLATE_SVG,
        ranking=_ranking_dict(missing),
        compare=None,
    )
    with pytest.raises(FileNotFoundError):
        ChannelConfig.load_channel_configs({'heat': entry})
