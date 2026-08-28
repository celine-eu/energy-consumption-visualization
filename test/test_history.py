"""Tests for history quality parsing and fetch helpers."""
from datetime import datetime, timedelta, timezone

from energy_consumption_visualization.config import HistoryProviderConfig
from energy_consumption_visualization.history.fetch import (
    fetch_channel_histories,
    fetch_histories,
)
from energy_consumption_visualization.history.provider import HistoryProvider
from test.helpers import FakeHistoryProvider, make_channel_config, make_samples


def _uninitialized_provider() -> HistoryProvider:
    return HistoryProvider.__new__(HistoryProvider)


def test_parse_quality_bare_label():
    assert HistoryProvider._parse_quality('measured') == 'measured'
    assert HistoryProvider._parse_quality('imputed') == 'imputed'
    assert HistoryProvider._parse_quality('forecast') == 'forecast'


def test_parse_quality_json_object():
    assert HistoryProvider._parse_quality('{"quality": "imputed"}') == 'imputed'


def test_parse_quality_bytes():
    assert HistoryProvider._parse_quality(b'measured') == 'measured'
    assert HistoryProvider._parse_quality(b'{"quality": "forecast"}') == 'forecast'


def test_parse_quality_invalid_and_none():
    assert HistoryProvider._parse_quality(None) is None
    assert HistoryProvider._parse_quality('nope') is None
    assert HistoryProvider._parse_quality('{"quality": "nope"}') is None
    assert HistoryProvider._parse_quality(123) is None


def test_get_history_retry_n_zero_does_not_sleep(monkeypatch, start_time):
    provider = _uninitialized_provider()
    fetches = []

    def fake_fetch(*args, **kwargs):
        fetches.append(1)
        return []

    monkeypatch.setattr(provider, '_fetch_history', fake_fetch)
    slept = []
    monkeypatch.setattr(
        'energy_consumption_visualization.history.provider.time.sleep',
        slept.append,
    )

    samples = provider.get_history('heat', start_time, start_time, retry_n=0)

    assert samples == []
    assert len(fetches) == 1
    assert slept == []


def test_get_history_retries_until_nonempty(monkeypatch, start_time):
    provider = _uninitialized_provider()
    result = make_samples(start_time, [1.0])
    queue = [[], [], result]

    monkeypatch.setattr(provider, '_fetch_history', lambda *a, **k: queue.pop(0))
    slept = []
    monkeypatch.setattr(
        'energy_consumption_visualization.history.provider.time.sleep',
        slept.append,
    )

    samples = provider.get_history(
        'heat', start_time, start_time, retry_n=5, retry_wait_s=2,
    )

    assert samples == result
    assert slept == [2, 2]
    assert queue == []


def test_get_history_returns_empty_after_retries(monkeypatch, start_time):
    provider = _uninitialized_provider()
    fetches = []

    def fake_fetch(*args, **kwargs):
        fetches.append(1)
        return []

    monkeypatch.setattr(provider, '_fetch_history', fake_fetch)
    slept = []
    monkeypatch.setattr(
        'energy_consumption_visualization.history.provider.time.sleep',
        slept.append,
    )

    samples = provider.get_history(
        'heat', start_time, start_time, retry_n=3, retry_wait_s=1.5,
    )

    assert samples == []
    assert len(fetches) == 4
    assert slept == [1.5, 1.5, 1.5]


def test_fetch_channel_histories_window_and_site_keys(start_time):
    end = start_time + timedelta(days=7)
    samples_a = make_samples(start_time, [1.0, 2.0])
    samples_b = make_samples(start_time, [3.0])
    provider = FakeHistoryProvider({
        ('heat_kwh', 'site_a'): samples_a,
        ('heat_kwh', 'site_b'): samples_b,
    })
    channel = make_channel_config()

    histories = fetch_channel_histories(channel, provider, end)

    assert set(histories) == {'site_a', 'site_b'}
    assert histories['site_a'] == samples_a
    assert histories['site_b'] == samples_b
    assert len(provider.calls) == 2
    for call in provider.calls:
        assert call['start'] == end - channel.history_window
        assert call['end'] == end
        assert call['dp_name'] == 'heat_kwh'
        assert call['dp_location_code'] in {'site_a', 'site_b'}
        assert call['retry_n'] == 0
        assert call['retry_wait_s'] == 5


def test_fetch_histories_uses_site_id_when_location_omitted(start_time):
    end = datetime(2026, 1, 8, tzinfo=timezone.utc)
    window = timedelta(days=7)
    samples = make_samples(start_time, [1.0])
    provider = FakeHistoryProvider({('outdoor_temp', 'site_a'): samples})
    configs = [HistoryProviderConfig(dp_name='outdoor_temp')]

    histories = fetch_histories('site_a', provider, configs, end, window)

    assert list(histories) == ['outdoor_temp']
    assert histories['outdoor_temp'] == samples
    assert provider.calls[0]['dp_location_code'] == 'site_a'
    assert provider.calls[0]['start'] == end - window
    assert provider.calls[0]['end'] == end
    assert provider.calls[0]['retry_n'] == 0
    assert provider.calls[0]['retry_wait_s'] == 5


def test_fetch_histories_prefers_configured_location(start_time):
    end = datetime(2026, 1, 8, tzinfo=timezone.utc)
    samples = make_samples(start_time, [9.0])
    provider = FakeHistoryProvider({('outdoor_temp', 'weather_station'): samples})
    configs = [
        HistoryProviderConfig(dp_name='outdoor_temp', dp_location_code='weather_station'),
    ]

    histories = fetch_histories('site_a', provider, configs, end, timedelta(days=1))

    assert histories['outdoor_temp'] == samples
    assert provider.calls[0]['dp_location_code'] == 'weather_station'


def test_fetch_forwards_retry_settings(start_time):
    end = start_time + timedelta(days=1)
    samples = make_samples(start_time, [1.0])
    provider = FakeHistoryProvider({
        ('heat_kwh', 'site_a'): samples,
        ('heat_kwh', 'site_b'): samples,
        ('outdoor_temp', 'site_a'): samples,
    })
    hp = HistoryProviderConfig(dp_name='heat_kwh', retry_n=3, retry_wait_s=2.5)
    channel = make_channel_config(history_provider=hp)

    fetch_channel_histories(channel, provider, end)
    fetch_histories('site_a', provider, [hp], end, timedelta(days=1))

    assert all(call['retry_n'] == 3 for call in provider.calls)
    assert all(call['retry_wait_s'] == 2.5 for call in provider.calls)
