"""Tests for Channel.process_once and _process_round with mocked I/O."""
import threading
from unittest.mock import MagicMock, patch

from energy_consumption_visualization.channel import Channel
from test.helpers import make_channel_config, make_samples


def _make_channel(config, provider) -> Channel:
    with (
        patch('energy_consumption_visualization.channel.redis.Redis'),
        patch('energy_consumption_visualization.channel.MultiStreamSource'),
    ):
        return Channel(
            config=config,
            redis_pool=MagicMock(),
            history_provider=provider,
            stop_event=threading.Event(),
        )


def test_process_once_calls_ranking_when_configured(fake_provider, ranking_config, start_time):
    config = make_channel_config(ranking_config=ranking_config)
    channel = _make_channel(config, fake_provider)
    histories = {
        'site_a': make_samples(start_time, [1.0]),
        'site_b': make_samples(start_time, [2.0]),
    }
    with (
        patch(
            'energy_consumption_visualization.channel.fetch_channel_histories',
            return_value=histories,
        ) as fetch,
        patch('energy_consumption_visualization.channel.ranking') as ranking_fn,
        patch('energy_consumption_visualization.channel.compare') as compare_fn,
    ):
        channel.process_once()

    fetch.assert_called_once()
    ranking_fn.assert_called_once_with('heat', histories, ranking_config, fetch.call_args[0][2])
    compare_fn.assert_not_called()


def test_process_once_calls_compare_per_site(fake_provider, compare_config, start_time):
    config = make_channel_config(compare_config=compare_config)
    channel = _make_channel(config, fake_provider)
    histories = {
        'site_a': make_samples(start_time, [1.0]),
        'site_b': make_samples(start_time, [2.0]),
    }
    extra = {'outdoor_temp': make_samples(start_time, [0.0])}
    with (
        patch(
            'energy_consumption_visualization.channel.fetch_channel_histories',
            return_value=histories,
        ),
        patch(
            'energy_consumption_visualization.channel.fetch_histories',
            return_value=extra,
        ) as fetch_extra,
        patch('energy_consumption_visualization.channel.ranking') as ranking_fn,
        patch('energy_consumption_visualization.channel.compare') as compare_fn,
    ):
        channel.process_once()

    ranking_fn.assert_not_called()
    assert fetch_extra.call_count == 2
    assert compare_fn.call_count == 2
    compared_sites = {call.args[1] for call in compare_fn.call_args_list}
    assert compared_sites == {'site_a', 'site_b'}


def test_process_once_skips_postprocess_when_configs_none(fake_provider):
    channel = _make_channel(make_channel_config(), fake_provider)
    with (
        patch(
            'energy_consumption_visualization.channel.fetch_channel_histories',
            return_value={'site_a': []},
        ),
        patch('energy_consumption_visualization.channel.ranking') as ranking_fn,
        patch('energy_consumption_visualization.channel.compare') as compare_fn,
        patch('energy_consumption_visualization.channel.fetch_histories') as fetch_extra,
    ):
        channel.process_once()

    ranking_fn.assert_not_called()
    compare_fn.assert_not_called()
    fetch_extra.assert_not_called()


def test_process_round_none_skips_fetch(fake_provider):
    channel = _make_channel(make_channel_config(), fake_provider)
    channel._logger = MagicMock()
    with patch('energy_consumption_visualization.channel.fetch_channel_histories') as fetch:
        channel._process_round(None)

    fetch.assert_not_called()
    channel._logger.warning.assert_called_once()
    assert 'skipping round' in channel._logger.warning.call_args[0][0]
