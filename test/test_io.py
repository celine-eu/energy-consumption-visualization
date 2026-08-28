"""Tests for MultiStreamSource with a fake Redis client."""
import json
import logging
from datetime import datetime, timezone

import pytest
import redis

from energy_consumption_visualization.io.source import MultiStreamSource
from energy_consumption_visualization.sample import Sample


class FakeRedis:
    def __init__(
            self,
            tips: dict[str, list] | None = None,
            xread_response=None,
            xrevrange_error: bool = False,
        ):
        self.tips = tips or {}
        self.xread_response = xread_response
        self.xrevrange_error = xrevrange_error
        self.xread_calls = []

    def xrevrange(self, stream, count=1):
        if self.xrevrange_error:
            raise redis.ResponseError('no such key')
        return self.tips.get(stream, [])

    def xread(self, streams, block, count):
        self.xread_calls.append({'streams': dict(streams), 'block': block, 'count': count})
        return self.xread_response


def _source(client: FakeRedis, logger: logging.Logger | None = None) -> MultiStreamSource:
    return MultiStreamSource(
        client=client,
        streams_by_site={'site_a': 'stream:a', 'site_b': 'stream:b'},
        logger=logger or logging.getLogger('test.io'),
    )


def test_stream_tip_id_from_xrevrange():
    client = FakeRedis(tips={'stream:a': [('5-0', {})], 'stream:b': []})
    source = _source(client)
    assert source._last_ids['stream:a'] == '5-0'
    assert source._last_ids['stream:b'] == '0-0'


def test_stream_tip_id_on_response_error():
    source = _source(FakeRedis(xrevrange_error=True))
    assert source._last_ids['stream:a'] == '0-0'
    assert source._last_ids['stream:b'] == '0-0'


def test_parse_entry_list_values():
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    samples = MultiStreamSource._parse_entry({
        'valid_time': json.dumps([ts.isoformat()]),
        'value': json.dumps([1.5]),
        'quality': json.dumps(['imputed']),
    })
    assert len(samples) == 1
    assert samples[0] == Sample(timestamp=ts, value=1.5, quality='imputed')


def test_parse_entry_scalars_naive_timestamp_and_default_quality():
    samples = MultiStreamSource._parse_entry({
        'valid_time': json.dumps('2026-01-01T12:00:00'),
        'value': json.dumps(2.0),
    })
    assert len(samples) == 1
    assert samples[0].timestamp == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert samples[0].value == 2.0
    assert samples[0].quality == 'measured'


def test_parse_entry_aware_timestamp_converted_to_utc():
    samples = MultiStreamSource._parse_entry({
        'valid_time': json.dumps('2026-01-01T14:00:00+02:00'),
        'value': json.dumps(3.0),
    })
    assert samples[0].timestamp == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_parse_entry_length_mismatch():
    with pytest.raises(ValueError, match='length mismatch'):
        MultiStreamSource._parse_entry({
            'valid_time': json.dumps(['2026-01-01T12:00:00']),
            'value': json.dumps([1.0, 2.0]),
        })


def test_read_blocking_timeout_returns_empty():
    source = _source(FakeRedis(xread_response=None))
    assert source.read_blocking() == {}
    source = _source(FakeRedis(xread_response=[]))
    assert source.read_blocking() == {}


def test_read_blocking_parses_entries_and_advances_cursor():
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    client = FakeRedis(xread_response=[
        ['stream:a', [(
            '10-0',
            {
                'valid_time': json.dumps([ts.isoformat()]),
                'value': json.dumps([4.0]),
                'quality': json.dumps(['measured']),
            },
        )]],
    ])
    source = _source(client)
    by_site = source.read_blocking(block_ms=1000, count=10)
    assert list(by_site) == ['site_a']
    assert by_site['site_a'][0].value == 4.0
    assert source._last_ids['stream:a'] == '10-0'
    assert client.xread_calls[0]['block'] == 1000


def test_read_blocking_skips_malformed_entry(caplog):
    client = FakeRedis(xread_response=[
        ['stream:a', [(
            '11-0',
            {
                'valid_time': json.dumps(['2026-01-01T12:00:00']),
                'value': json.dumps([1.0, 2.0]),
            },
        )]],
    ])
    logger = logging.getLogger('test.io.malformed')
    source = _source(client, logger)
    with caplog.at_level(logging.WARNING, logger='test.io.malformed'):
        assert source.read_blocking() == {}
    assert 'Skipping malformed entry' in caplog.text
