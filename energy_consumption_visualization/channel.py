"""
Worker thread: wait for regularize samples on all site streams, then fetch
Timescale history and run per-site postprocess.
"""
from __future__ import annotations

import datetime
import logging
import threading

import redis

from .config import ChannelConfig
from .history import HistoryProvider, fetch_channel_histories, fetch_histories
from .io import MultiStreamSource
from .postprocess import compare, ranking


class Channel(threading.Thread):
    """
    Barriers Redis arrivals across all configured site_ids for one measurement,
    then loads Timescale history and post-processes per site.
    """

    def __init__(
            self,
            config: ChannelConfig,
            redis_pool: redis.ConnectionPool,
            history_provider: HistoryProvider,
            stop_event: threading.Event,
        ):
        super().__init__(name=f'channel-{config.name}', daemon=True)
        self._config = config
        self._history_provider = history_provider
        self._stop_event = stop_event
        self._logger = logging.getLogger(f'd2_dashboard.{config.name}')

        client = redis.Redis(connection_pool=redis_pool)
        streams_by_site = {
            site_id: config.stream_for(site_id) for site_id in config.site_ids
        }
        self._source = MultiStreamSource(
            client=client, streams_by_site=streams_by_site, logger=self._logger
        )
        self._site_ids = set(config.site_ids)

    def run(self) -> None:
        streams = [self._config.stream_for(s) for s in self._config.site_ids]
        self._logger.info(
            f'Channel started for {self._config.name}: waiting on {streams}'
        )

        arrived: set[str] = set()
        round_latest: datetime.datetime | None = None

        while not self._stop_event.is_set():
            try:
                by_site = self._source.read_blocking(block_ms=30000)
            except Exception as exc:
                self._logger.exception(f'Redis read failed: {exc}')
                self._stop_event.wait(5)
                continue

            if not by_site:
                continue

            for site_id, samples in by_site.items():
                if not samples:
                    continue
                arrived.add(site_id)
                site_max = max(s.timestamp for s in samples)
                if round_latest is None or site_max > round_latest:
                    round_latest = site_max

            missing = self._site_ids - arrived
            if missing:
                self._logger.debug(
                    f'Barrier pending for {self._config.name}: '
                    f'arrived={sorted(arrived)}, missing={sorted(missing)}'
                )
                continue

            try:
                self._process_round(round_latest)
            except Exception as exc:
                self._logger.exception(f'Processing failed for {self._config.name}: {exc}')

            arrived.clear()
            round_latest = None

        self._logger.info('Channel stopped')

    def process_once(self) -> None:
        self._process_round(datetime.datetime.now())

    def _process_round(self, end: datetime.datetime | None) -> None:
        if end is None:
            self._logger.warning(
                f'No sample timestamps for {self._config.name}; skipping round'
            )
            return

        self._logger.info(f'All sites arrived for {self._config.name} at {end.strftime("%Y-%m-%d %H:%M:%S")} - processing at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

        histories = fetch_channel_histories(
            self._config, self._history_provider, end, logger=self._logger
        )

        if self._config.ranking_config:
            ranking(self._config.name, histories, self._config.ranking_config, end)

        if self._config.compare_config:
            for site_id, samples in histories.items():
                compare_config = self._config.compare_config

                extra_histories = fetch_histories(
                    site_id,
                    self._history_provider,
                    [cc.history_provider for cc in compare_config.compare_against],
                    end,
                    self._config.history_window,
                    logger=self._logger,
                )

                compare(self._config.name, site_id, samples, extra_histories, self._config.compare_config, end)
