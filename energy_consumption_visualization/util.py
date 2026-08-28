from __future__ import annotations

import datetime
import re
import redis
import typing
import pathlib

from .logger import LOGGER
from .render.colors import *

if typing.TYPE_CHECKING:
    from .config import OutputConfig

__DURATION_UNITS = {
    'ms': datetime.timedelta(milliseconds=1),
    's': datetime.timedelta(seconds=1),
    'm': datetime.timedelta(minutes=1),
    'h': datetime.timedelta(hours=1),
    'd': datetime.timedelta(days=1),
    'w': datetime.timedelta(weeks=1),
}

__DURATION_PATTERN = re.compile(
    r'^\s*(\d+(?:\.\d+)?)\s*('
    + '|'.join(sorted(__DURATION_UNITS, key=len, reverse=True))
    + r')\s*$'
)

def parse_duration(value: typing.Any) -> datetime.timedelta:
    """
    Converts duration strings ('30s', '1m', '15m', '12h') to timedelta.
    Bare numbers are interpreted as seconds.
    Timedeltas are returned unchanged.
    """
    if isinstance(value, str):
        match = __DURATION_PATTERN.match(value)
        if match:
            amount, unit = match.groups()
            return float(amount) * __DURATION_UNITS[unit]
        raise ValueError(f'Invalid duration: {value!r}')
    if isinstance(value, (int, float)):
        return datetime.timedelta(seconds=value)
    if isinstance(value, datetime.timedelta):
        return value

    raise ValueError(f'Invalid duration: {value!r}')


def parse_sites(
        sites: typing.Sequence[dict]
    ) -> tuple[dict[str, str], dict[str, int]]:
    """Derive site map and apartment counts from site entries.

    Each entry must have ``id``, ``label``, and a positive integer ``n_apartments``.
    """
    if not sites:
        raise RuntimeError('sites must be non-empty')
    site_map: dict[str, str] = {}
    apartments_by_site: dict[str, int] = {}

    for entry in sites:
        try:
            site_id = entry['id']
            label = entry['label']
        except (KeyError, TypeError) as exc:
            raise RuntimeError(
                f'Invalid site entry {entry!r}: expected keys id and label'
            ) from exc
        site_map[site_id] = label
        try:
            n_apartments = int(entry['n_apartments'])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                f'Invalid site entry {entry!r}: expected positive int n_apartments'
            ) from exc
        if n_apartments <= 0:
            raise RuntimeError(
                f'Invalid site entry {entry!r}: n_apartments must be positive'
            )
        apartments_by_site[site_id] = n_apartments

    return site_map, apartments_by_site


def get_color(color_name: str) -> str:
    """Get a color by name."""
    return globals()[color_name.replace(' ', '_').upper()]


def get_as_list(value: str | typing.Sequence[str] | typing.Any) -> list[str]:
    """Get the output path as a list of strings."""
    if isinstance(value, str):
        return [value]
    elif isinstance(value, list):
        return list(value)
    else:
        raise ValueError(f'Invalid value: {value!r}')

def get_output_paths(
        config: OutputConfig,
        site_id: str,
        measurement: str,
        processing_date: datetime.datetime,
    ) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    """Get the output path for the measurement."""
    # Build the path configuration
    path_config = dict(
        site_id=site_id,
        measurement = measurement,
        date=processing_date.strftime(config.output_date_format),
    )

    # Build the output paths
    out_svg = [
        pathlib.Path(path.format(ext='svg', **path_config)) / config.output_file_name.format(ext='svg', **path_config) \
            for path in config.output_path
    ]
    out_png = [
        pathlib.Path(path.format(ext='png', **path_config)) / config.output_file_name.format(ext='png', **path_config) \
            for path in config.output_path
    ]

    # Create the parent directories if they don't exist
    for path in out_svg:
        path.parent.mkdir(parents=True, exist_ok=True)
    for path in out_png:
        path.parent.mkdir(parents=True, exist_ok=True)

    return out_svg, out_png

def load_redis_connection_pool(redis_config: dict) -> redis.ConnectionPool:
    """
    Parses the configuration and instantiates the Redis connection pool
    """
    host = redis_config['host']
    port = redis_config['port']
    db = redis_config['db']
    pwd = redis_config.get('password')
    LOGGER.info(f'Configure redis connection to {host}:{port} using db {db}')

    if pwd:
        pool = redis.ConnectionPool(host=host, port=port, db=db, decode_responses=True, password=pwd)
    else:
        pool = redis.ConnectionPool(host=host, port=port, db=db, decode_responses=True)

    client = redis.Redis(connection_pool=pool)
    client.ping()  # Will raise an exception in case a connection error occurs
    LOGGER.info(f'Redis connection to {host}:{port} using db {db} is alive.')

    return pool
