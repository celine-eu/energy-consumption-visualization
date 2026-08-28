"""Retrieval of raw historic samples from TimescaleDB."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from peewee import PostgresqlDatabase, Query, SQL
from typing import List, TypeAlias

from ..sample import Quality, Sample
from .timescaledb import (
    DB_PROXY,
    DataPoint,
    UnitemporalDoubleDetails,
    UnitemporalJsonbDetails,
)

LOGGER = logging.getLogger('energy_consumption_visualization.history')
_VALID_QUALITIES = frozenset({'measured', 'imputed', 'forecast'})
DetailsModel: TypeAlias = type[UnitemporalDoubleDetails] | type[UnitemporalJsonbDetails]


class HistoryProvider:
    """
    Retrieves historic samples from TimescaleDB.
    """

    def __init__(self, timescale_config: dict):
        self.db_ = PostgresqlDatabase(
            timescale_config['db'],
            host=timescale_config['host'],
            port=timescale_config['port'],
            user=timescale_config['user'],
            password=timescale_config['password'],
        )
        DB_PROXY.initialize(self.db_)

    def get_history(
            self, dp_name: str,
            start: datetime, end: datetime,
            dp_location_code: str | None = None,
            dp_device_id: str | None = None,
            dp_data_provider: str | None = None,
            dp_unit: str | None = None,
            retry_n: int = 0,
            retry_wait_s: float = 5,
        ) -> List[Sample]:
        """
        Retrieve the history of samples for the given datapoint, start, and end.

        Quality is joined from the companion ``{dp_name}_quality`` jsonb series
        when present; otherwise samples default to ``measured``.

        If the query returns no samples, retry up to ``retry_n`` times
        (``retry_n=0`` disables retries), waiting ``retry_wait_s`` seconds
        between attempts.
        """
        samples = self._fetch_history(
            dp_name,
            start,
            end,
            dp_location_code,
            dp_device_id,
            dp_data_provider,
            dp_unit,
        )
        for remaining in range(retry_n, 0, -1):
            if samples:
                break
            LOGGER.info(
                'Empty history for dp_name %s, dp_location_code %s; '
                'retrying in %ss (%s attempt(s) left)',
                dp_name, dp_location_code, retry_wait_s, remaining,
            )
            time.sleep(retry_wait_s)
            samples = self._fetch_history(
                dp_name,
                start,
                end,
                dp_location_code,
                dp_device_id,
                dp_data_provider,
                dp_unit,
            )
        return samples

    def _fetch_history(
            self,
            dp_name: str,
            start: datetime,
            end: datetime,
            dp_location_code: str | None = None,
            dp_device_id: str | None = None,
            dp_data_provider: str | None = None,
            dp_unit: str | None = None,
        ) -> List[Sample]:
        try:
            value_query = self._get_query(
                UnitemporalDoubleDetails,
                dp_name,
                dp_location_code,
                dp_device_id,
                dp_data_provider,
                dp_unit,
                start,
                end,
            )
            quality_query = self._get_quality_query(
                f'{dp_name}_quality',
                dp_location_code,
                dp_device_id,
                dp_data_provider,
                dp_unit,
                start,
                end,
            )
            with self.db_:
                qualities = self._fetch_qualities(quality_query)
                return [
                    Sample(
                        timestamp=valid_time,
                        value=value,
                        quality=qualities.get(valid_time, 'measured'),
                    )
                    for valid_time, value in value_query.tuples()
                ]
        except Exception as e:
            raise ValueError(
                f"Failed to retrieve history for dp_name {dp_name}, "
                f"dp_location_code {dp_location_code}, dp_data_provider {dp_data_provider}, "
                f"start {start}, end {end}: {e}"
            )

    def _get_query(
            self,
            details_model: DetailsModel,
            dp_name: str,
            dp_location_code: str | None = None,
            dp_device_id: str | None = None,
            dp_data_provider: str | None = None,
            dp_unit: str | None = None,
            start: datetime | None = None,
            end: datetime | None = None,
        ) -> Query:
        """
        Create a query for the given details model and datapoint identity.
        """
        dp_conditions = [DataPoint.name == dp_name]
        if dp_location_code is not None:
            dp_conditions.append(DataPoint.location_code == dp_location_code)
        if dp_device_id is not None:
            dp_conditions.append(DataPoint.device_id == dp_device_id)
        if dp_data_provider is not None:
            dp_conditions.append(DataPoint.data_provider == dp_data_provider)
        if dp_unit is not None:
            dp_conditions.append(DataPoint.unit == dp_unit)

        dp_subquery = DataPoint.select(DataPoint.id).where(*dp_conditions)

        query = details_model.select(
            details_model.valid_time,
            details_model.value,
        ).where(details_model.dp_id.in_(dp_subquery))

        if start is not None:
            query = query.where(details_model.valid_time >= start)

        if end is not None:
            query = query.where(details_model.valid_time <= end)

        return query

    def _get_quality_query(
            self,
            dp_name: str,
            dp_location_code: str | None = None,
            dp_device_id: str | None = None,
            dp_data_provider: str | None = None,
            dp_unit: str | None = None,
            start: datetime | None = None,
            end: datetime | None = None,
        ) -> Query:
        """
        Query the companion quality series, projecting ``value->>'quality'`` as text.
        """
        dp_conditions = [DataPoint.name == dp_name]
        if dp_location_code is not None:
            dp_conditions.append(DataPoint.location_code == dp_location_code)
        if dp_device_id is not None:
            dp_conditions.append(DataPoint.device_id == dp_device_id)
        if dp_data_provider is not None:
            dp_conditions.append(DataPoint.data_provider == dp_data_provider)
        if dp_unit is not None:
            dp_conditions.append(DataPoint.unit == dp_unit)

        dp_subquery = DataPoint.select(DataPoint.id).where(*dp_conditions)

        query = UnitemporalJsonbDetails.select(
            UnitemporalJsonbDetails.valid_time,
            SQL("value->>'quality'"),
        ).where(UnitemporalJsonbDetails.dp_id.in_(dp_subquery))

        if start is not None:
            query = query.where(UnitemporalJsonbDetails.valid_time >= start)

        if end is not None:
            query = query.where(UnitemporalJsonbDetails.valid_time <= end)

        return query

    def _fetch_qualities(self, query: Query) -> dict[datetime, Quality]:
        """
        Fetch quality labels keyed by valid_time. Missing/invalid entries are skipped.
        """
        qualities: dict[datetime, Quality] = {}
        for valid_time, raw_value in query.tuples():
            quality = self._parse_quality(raw_value)
            if quality is not None:
                qualities[valid_time] = quality
        return qualities

    @staticmethod
    def _parse_quality(raw_value) -> Quality | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, (bytes, bytearray, memoryview)):
            raw_value = bytes(raw_value).decode('utf-8')
        if isinstance(raw_value, str):
            try:
                raw_value = json.loads(raw_value)
            except json.JSONDecodeError:
                # Already a bare quality label (e.g. from value->>'quality').
                if raw_value in _VALID_QUALITIES:
                    return raw_value  # type: ignore[return-value]
                return None
        if not isinstance(raw_value, dict):
            return None
        quality = raw_value.get('quality')
        if quality in _VALID_QUALITIES:
            return quality  # type: ignore[return-value]
        return None
