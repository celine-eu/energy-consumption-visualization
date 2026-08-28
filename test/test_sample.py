"""Tests for Sample.to_dict."""
from datetime import datetime, timezone

from energy_consumption_visualization.sample import Sample


def test_to_dict_includes_quality_by_default():
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    sample = Sample(timestamp=ts, value=1.5, quality='imputed')
    assert Sample.to_dict(sample) == {
        'timestamp': ts,
        'value': 1.5,
        'quality': 'imputed',
    }


def test_to_dict_omits_quality():
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    sample = Sample(timestamp=ts, value=1.5, quality='forecast')
    assert Sample.to_dict(sample, include_quality=False) == {
        'timestamp': ts,
        'value': 1.5,
    }


def test_to_dict_isoformat_timestamp():
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    sample = Sample(timestamp=ts, value=2.0)
    result = Sample.to_dict(sample, convert_timestamp=True)
    assert result['timestamp'] == ts.isoformat()
    assert result['quality'] == 'measured'
