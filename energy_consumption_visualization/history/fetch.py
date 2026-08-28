"""Shared helpers for fetching Timescale history for a channel."""
from __future__ import annotations

import datetime
import logging

from .provider import HistoryProvider
from ..config import ChannelConfig, HistoryProviderConfig
from ..sample import Sample

LOGGER = logging.getLogger('energy_consumption_visualization.history')


def fetch_channel_histories(
        channel: ChannelConfig,
        provider: HistoryProvider,
        end: datetime.datetime,
        logger: logging.Logger | None = None,
    ) -> dict[str, list[Sample]]:
    """
    Fetch history for every site_id on the channel over
    [end - history_window, end].
    """
    log = logger or LOGGER
    start = end - channel.history_window
    hp = channel.history_provider
    log.info(
        f'Retrieving history for {channel.name} '
        f'[{start.isoformat()} .. {end.isoformat()}]'
    )

    histories: dict[str, list[Sample]] = {}
    for site_id in channel.site_ids:
        samples = provider.get_history(
            dp_name=hp.dp_name,
            start=start,
            end=end,
            dp_location_code=site_id,
            dp_device_id=hp.dp_device_id,
            dp_data_provider=hp.dp_data_provider,
            dp_unit=hp.dp_unit,
        )
        histories[site_id] = samples
        log.info(
            f'Retrieved {len(samples)} samples for {channel.name}/{site_id}'
        )
    return histories

def fetch_histories(
        site_id: str,
        provider: HistoryProvider,
        provider_configs: list[HistoryProviderConfig],
        end: datetime.datetime,
        history_window: datetime.timedelta,
        logger: logging.Logger | None = None,
    ) -> dict[str, list[Sample]]:
    """
    Fetch history over [end - history_window, end].
    """
    log = logger or LOGGER
    start = end - history_window

    histories: dict[str, list[Sample]] = {}
    for provider_config in provider_configs:
        samples = provider.get_history(
            start=start,
            end=end,
            dp_name=provider_config.dp_name,
            dp_location_code=provider_config.dp_location_code if provider_config.dp_location_code else site_id,
            dp_device_id=provider_config.dp_device_id,
            dp_data_provider=provider_config.dp_data_provider,
            dp_unit=provider_config.dp_unit,
        )
        log.info(
            f'Retrieved {len(samples)} samples for {provider_config.dp_name!r}/{provider_config.dp_location_code!r}'
        )
        histories[provider_config.dp_name] = samples

    return histories
