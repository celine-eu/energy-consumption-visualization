import matplotlib
import matplotlib.pyplot as plt
import pytz
import re
import warnings
from datetime import datetime, timedelta,timezone
from functools import lru_cache
from pathlib import Path

__DURATION_UNITS = {
    'ms': timedelta(milliseconds=1),
    's': timedelta(seconds=1),
    'm': timedelta(minutes=1),
    'h': timedelta(hours=1),
    'd': timedelta(days=1),
    'w': timedelta(weeks=1),
}

__DURATION_PATTERN = re.compile(
    r'^\s*(\d+(?:\.\d+)?)\s*('
    + '|'.join(sorted(__DURATION_UNITS, key=len, reverse=True))
    + r')\s*$'
)

def parse_duration(value: str) -> timedelta:
    """
    Converts duration strings ('30s', '1m', '15m', '12h') to timedelta.
    Bare numbers are interpreted as seconds.
    """
    if isinstance(value, str):
        match = __DURATION_PATTERN.match(value)
        if match:
            amount, unit = match.groups()
            return float(amount) * __DURATION_UNITS[unit]

    raise ValueError(f'Invalid duration: {value!r}')

def get_local_timezone(country_code: str, utc_dt: datetime) -> pytz.tzinfo.BaseTzInfo:
    """
    Returns a timezone object representing the local timezone.

    country_code: ISO 3166-1 alpha-2 code, e.g. 'FI', 'US', 'JP'
    utc_dt: A datetime representing a UTC timestamp.
            Can be naive (assumed UTC) or timezone-aware.
    """
    # Normalize input to an aware UTC datetime
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    else:
        utc_dt = utc_dt.astimezone(timezone.utc)

    zone_names = pytz.country_timezones.get(country_code.upper())
    if not zone_names:
        raise ValueError(f"No timezones found for country code '{country_code}'")
    if 1 < len(zone_names):
        warnings.warn(f"Multiple timezones found for country code '{country_code}': Using '{zone_names[0]}'")

    return pytz.timezone(zone_names[0])

def subplots(width_px: int, height_px: int, dpi: float, **kwargs) -> tuple[plt.Figure, plt.Axes]:
    """
    Helper function wrapping :func:`matplotlib.pyplot.subplots`: Create a figure sized for a
    template slot using width and height in pixels.
    Template embed fills the slot from the SVG viewBox, so a wrong figsize still “fits” but
    leaves fonts and line widths tiny relative to the axes. Proper sizing keeps the figure
    readable once the chart is scaled into the dashboard slot.
    """
    return plt.subplots(nrows=1, ncols=1, figsize=(width_px / dpi, height_px / dpi), dpi=dpi, **kwargs)

@lru_cache(maxsize=1)
def resvg_font_dirs() -> list[str]:
    """
    Return matplotlib's bundled TTF directory for resvg font loading.

    Context: SVG text (table, title, footer) uses DejaVu Sans, but python:slim images often have
    no system fonts installed, so resvg would drop the glyphs. However, Matplotlib ships those fonts,
    so we can use them here.
    """
    return [str(Path(matplotlib.get_data_path()) / "fonts" / "ttf")]
