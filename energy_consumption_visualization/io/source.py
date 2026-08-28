"""
Multi-stream Redis source for regularize output streams (one stream per site).
"""
from __future__ import annotations

import datetime
import json
import logging
import typing

import redis

from ..sample import Sample


class MultiStreamSource:
    """
    Reads samples from multiple Redis streams (one per site_id).

    Each stream cursor starts at the current tip so historical backlog is not
    replayed. Blocking multi-key XREAD waits for new entries across all streams.
    """

    def __init__(
            self,
            client: redis.Redis,
            streams_by_site: dict[str, str],
            logger: logging.Logger,
        ):
        self._client = client
        self._streams_by_site = dict(streams_by_site)
        self._site_by_stream = {stream: site for site, stream in streams_by_site.items()}
        self._logger = logger
        self._last_ids = {
            stream: self._stream_tip_id(stream) for stream in streams_by_site.values()
        }

    def read_blocking(
            self, block_ms: int = 30000, count: int = 100
        ) -> dict[str, list[Sample]]:
        """
        Blocking XREAD across all site streams. Returns site_id -> new samples
        (empty dict on timeout / no data).
        """
        response = self._client.xread(
            streams=self._last_ids, block=block_ms, count=count
        )
        if not response:
            return {}

        by_site: dict[str, list[Sample]] = {}
        for stream_name, entries in response:
            site_id = self._site_by_stream.get(stream_name)
            if site_id is None:
                continue
            for entry_id, fields in entries:
                self._last_ids[stream_name] = entry_id
                try:
                    samples = self._parse_entry(fields)
                    by_site.setdefault(site_id, []).extend(samples)
                except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
                    self._logger.warning(
                        f'Skipping malformed entry {entry_id} on {stream_name}: {exc}'
                    )
        return by_site

    def _stream_tip_id(self, stream: str) -> str:
        try:
            entries = self._client.xrevrange(stream, count=1)
        except redis.ResponseError:
            return '0-0'
        if not entries:
            return '0-0'
        return entries[0][0]

    @staticmethod
    def _parse_entry(fields: dict) -> list[Sample]:
        times = json.loads(fields['valid_time'])
        values = json.loads(fields['value'])
        qualities = json.loads(fields.get('quality', '[]'))

        if not isinstance(times, list):
            times = [times]
        if not isinstance(values, list):
            values = [values]
        if not isinstance(qualities, list):
            qualities = [qualities]

        if len(times) != len(values):
            raise ValueError(
                f'valid_time/value length mismatch: {len(times)} vs {len(values)}'
            )

        samples = []
        for i, (raw_time, raw_value) in enumerate(zip(times, values)):
            timestamp = datetime.datetime.fromisoformat(raw_time)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
            else:
                timestamp = timestamp.astimezone(datetime.timezone.utc)
            quality = qualities[i] if i < len(qualities) else 'measured'
            samples.append(
                Sample(timestamp=timestamp, value=float(raw_value), quality=quality)
            )
        return samples
