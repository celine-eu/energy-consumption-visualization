"""Test helpers shared by fixtures and test modules."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from energy_consumption_visualization.config import (
    ChannelConfig,
    CompareAgainstConfig,
    CompareConfig,
    HistoryProviderConfig,
    RankingConfig,
)
from energy_consumption_visualization.sample import Sample

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
TEMPLATE_SVG = FIXTURES_DIR / 'template.svg'


def make_samples(
        start: datetime,
        values: list[float],
        step: timedelta | None = None,
        quality: str = 'measured',
    ) -> list[Sample]:
    """Build timezone-aware UTC samples at a regular interval."""
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    step = step or timedelta(hours=1)
    return [
        Sample(timestamp=start + i * step, value=value, quality=quality)
        for i, value in enumerate(values)
    ]


class FakeHistoryProvider:
    """In-memory HistoryProvider stand-in keyed by (dp_name, location)."""

    def __init__(self, data: dict[tuple[str, str | None], list[Sample]] | None = None):
        self.data = data or {}
        self.calls: list[dict] = []

    def get_history(self, **kwargs) -> list[Sample]:
        self.calls.append(kwargs)
        key = (kwargs['dp_name'], kwargs.get('dp_location_code'))
        return list(self.data.get(key, []))


def make_ranking_config(
        template_path: Path,
        output_dir: Path,
        **overrides,
    ) -> RankingConfig:
    kwargs = dict(
        title_slot='title',
        title_label='Ranking',
        title_font_size=40,
        title_color='#226676',
        chart_slot='slot1',
        chart_label='Heat',
        chart_unit='kWh',
        chart_resample_bin_width=timedelta(hours=1),
        chart_resample_method='sum',
        chart_time_zone='FI',
        chart_dpi=80,
        chart_text_color='#0d1720',
        chart_top_adjust=1.0,
        chart_bottom_adjust=0.14,
        chart_title=None,
        chart_title_color=None,
        chart_color='#226676',
        chart_linestyle='-',
        chart_linewidth=0.5,
        chart_marker='s',
        chart_markersize=4,
        chart_autoscale_factor=None,
        output_path=[str(output_dir / '{date}' / '{site_id}')],
        output_file_name='{measurement}-ranking.{ext}',
        output_date_format='%Y%m%d-%H%M',
        template_path=template_path,
        site_map={'site_a': 'A Street', 'site_b': 'B Street', 'site_c': 'C Street'},
        apartments_by_site={'site_a': 10, 'site_b': 20, 'site_c': 5},
        ranking_slot='slot2',
        ranking_include_emoticon=True,
        ranking_avg_label='average',
        ranking_avg_color='#f9b500',
        ranking_highlight_color='#d1503c',
        ranking_avg_marker='s',
        ranking_avg_markersize=4.0,
        ranking_avg_linestyle='-',
        ranking_avg_linewidth=0.5,
        ranking_avg_font_size=12.0,
        ranking_value_decimals=0,
        ranking_rank_label='Rank',
        ranking_address_label='Address',
    )
    kwargs.update(overrides)
    return RankingConfig(**kwargs)


def make_compare_against_config(**overrides) -> CompareAgainstConfig:
    kwargs = dict(
        chart_slot='slot3',
        chart_label='Outdoor',
        chart_unit='C',
        chart_resample_bin_width=timedelta(hours=1),
        chart_resample_method='mean',
        chart_time_zone='FI',
        chart_dpi=80,
        chart_text_color='#0d1720',
        chart_top_adjust=0.87,
        chart_bottom_adjust=0.14,
        chart_title='Outdoor temperature',
        chart_title_color='#226676',
        chart_color='#226676',
        chart_linestyle=None,
        chart_linewidth=None,
        chart_marker=None,
        chart_markersize=None,
        chart_autoscale_factor=None,
        history_provider=HistoryProviderConfig(dp_name='outdoor_temp'),
    )
    kwargs.update(overrides)
    return CompareAgainstConfig(**kwargs)


def make_compare_config(
        template_path: Path,
        output_dir: Path,
        **overrides,
    ) -> CompareConfig:
    kwargs = dict(
        title_slot='title',
        title_label='Compare {site_label}',
        title_font_size=40,
        title_color='#226676',
        chart_slot='slot1',
        chart_label='Heat',
        chart_unit='kWh',
        chart_resample_bin_width=timedelta(hours=1),
        chart_resample_method='sum',
        chart_time_zone='FI',
        chart_dpi=80,
        chart_text_color='#0d1720',
        chart_top_adjust=0.87,
        chart_bottom_adjust=0.14,
        chart_title='Site heat',
        chart_title_color='#226676',
        chart_color='#226676',
        chart_linestyle=None,
        chart_linewidth=None,
        chart_marker=None,
        chart_markersize=None,
        chart_autoscale_factor=None,
        output_path=[str(output_dir / '{date}' / '{site_id}')],
        output_file_name='{measurement}-compare.{ext}',
        output_date_format='%Y%m%d-%H%M',
        site_map={'site_a': 'A Street', 'site_b': 'B Street'},
        compare_against=[make_compare_against_config()],
        compare_font_size=12.0,
        template_path=template_path,
    )
    kwargs.update(overrides)
    return CompareConfig(**kwargs)


def make_channel_config(
        *,
        ranking_config: RankingConfig | None = None,
        compare_config: CompareConfig | None = None,
        **overrides,
    ) -> ChannelConfig:
    kwargs = dict(
        name='heat',
        site_ids=['site_a', 'site_b'],
        stream_template='reg:{site_id}:heat',
        history_window=timedelta(days=7),
        history_provider=HistoryProviderConfig(
            dp_name='heat_kwh',
            dp_data_provider='D2-Regularize',
        ),
        ranking_config=ranking_config,
        compare_config=compare_config,
    )
    kwargs.update(overrides)
    return ChannelConfig(**kwargs)
