from __future__ import annotations

import logging
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import shutil

from collections import OrderedDict
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path
from typing import cast

from ..config import ChartConfig, TitleConfig, RankingConfig
from ..render import Template, Figure, Table, Title
from ..render.util import subplots, get_local_timezone
from ..util import  get_output_paths
from ..sample import Sample

LOGGER = logging.getLogger('d2_dashboard.postprocess.ranking')

# Path to the directory containing the emojis
_EMOJI_DIR = Path(__file__).resolve().parents[1] / 'render' / 'emojis'

def ranking(
        measurement: str,
        histories: dict[str, list[Sample]],
        config: RankingConfig,
        processing_date: datetime,
    ) -> None:
    """
    Postprocessing: rating for the given measurement across all sites
    """
    LOGGER.info(f'processing rating at {processing_date.strftime("%Y-%m-%d %H:%M:%S")}')

    # Build the resampled series for the measurement
    series_by_site = _build_resampled_series(
        measurement, histories, config,
    )

    # Calculate the median across all sites
    median = _median_across_sites(series_by_site)

    # Build the ranking table for the measurement
    ranking_headers, ranking_rows, ranking_highlights = _build_ranking_table(
        series_by_site, config
    )

    # Apply common style for all plots
    _apply_common_plot_style(config)

    # Iterate over all sites in the series and render the site overview
    for site_id in series_by_site:
        _render_site_rating(
            measurement, site_id, series_by_site[site_id], median,
            ranking_headers, ranking_rows, ranking_highlights[site_id],
            processing_date, config,
        )

def _samples_to_series(
        samples: list[Sample],
        bin_width: timedelta,
    ) -> pd.Series:
    """Convert the samples to a pandas series."""
    df = pd.DataFrame([Sample.to_dict(s, include_quality=False) for s in samples])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    return df.resample(bin_width).agg('sum')['value']  # type: ignore[return-value]

def _build_resampled_series(
        measurement: str,
        histories: dict[str, list[Sample]],
        config: RankingConfig,
    ) -> dict[str, pd.Series]:
    """Build the resampled series for the measurement."""
    series_by_site: dict[str, pd.Series] = {}
    # Iterate over all sites in the histories
    for site_id, samples in histories.items():
        # Sort the samples by timestamp
        samples.sort(key=lambda s: s.timestamp)
        try:
            LOGGER.debug(
                f'processing samples for {measurement!r}/site_id={site_id!r}: '
                f'samples={len(samples)}, first={samples[0].timestamp}, last={samples[-1].timestamp}'
            )
        except IndexError:
            LOGGER.warning(
                f'no samples for {measurement!r}/site_id={site_id!r}'
            )
            continue

        # Convert the samples to a pandas series and weight by 1 / n_apartments
        series = _samples_to_series(samples, config.chart_resample_bin_width)
        series_by_site[site_id] = series / float(config.apartments_by_site[site_id])
    return series_by_site

def _median_across_sites(series_by_site: dict[str, pd.Series]) -> pd.Series:
    """Calculate the median across all sites."""
    return pd.concat(series_by_site, axis=1, copy=False).median(axis=1)  # type: ignore[return-value]

def _rank_sites(series_by_site: dict[str, pd.Series]) -> OrderedDict:
    """Rank the sites by the sum of the series."""
    return OrderedDict(
        pd.concat(series_by_site, axis=1, copy=False).sum().sort_values(ascending=True)
    )

def _build_ranking_table(
        series_by_site: dict[str, pd.Series],
        config: RankingConfig
    ) -> tuple[list[str], list[list], dict[str, int]]:
    """Build the ranking table for the measurement.

    Returns headers, rows, and a map of highlight indices.
    """
    # Rank the sites by the sum of the series
    ranking = _rank_sites(series_by_site)
    # Build the headers for the ranking table
    headers = [
        config.ranking_rank_label,
        config.ranking_address_label,
        config.chart_label,
    ]
    # Build the rows and highlight indices for the ranking table
    rows: list[list] = []
    highlights: dict[str, int] = {}
    for idx, (site_id, value) in enumerate(ranking.items()):
        rows.append([
            idx + 1, # rank index
            config.site_map[site_id], # site address
            f'{float(value):.{config.ranking_value_decimals}f} {config.chart_unit}', # site value
        ])
        highlights[site_id] = idx
    return headers, rows, highlights

def _select_emoticon(rank: int, total_ranks: int) -> Path:
    """Return the emoji SVG path for the given rank band."""
    if rank == 1:
        return _EMOJI_DIR / 'party_popper.svg'
    elif rank == total_ranks:
        return _EMOJI_DIR / 'face_with_crossed_out_eyes.svg'
    elif rank <= ceil(float(total_ranks) / 3.):
        return _EMOJI_DIR / 'slightly_smiling_face.svg'
    elif rank <= ceil(float(total_ranks) * 2. / 3.):
        return _EMOJI_DIR / 'neutral_face.svg'
    else:
        return _EMOJI_DIR / 'slightly_frowning_face.svg'

def _apply_common_plot_style(config: RankingConfig) -> None:
    """Apply the common plot style."""
    plt.rcParams.update({
        'font.size': config.ranking_avg_font_size,
        'xtick.labelsize': 0.62 * config.ranking_avg_font_size,
        'ytick.labelsize': 0.62 * config.ranking_avg_font_size,
        'legend.fontsize': 0.62 * config.ranking_avg_font_size,
    })

def _to_mpl_dates(
        index: pd.DatetimeIndex,
        tz_name: str,
        bin_shift: timedelta,
    ):
    """Convert the index to matplotlib dates."""
    tz = get_local_timezone(tz_name, cast(datetime, index[-1]))
    return mdates.date2num(index.tz_convert(tz) + bin_shift)

def _plot_site_vs_median(
        ax: plt.Axes,
        fig: plt.Figure,
        site_series: pd.Series,
        median: pd.Series,
        site_id: str,
        config: RankingConfig,
    ) -> None:
    """Plot the site series vs the median."""
    # Calculate the resample bin width in hours
    resample_bin_width_hours = config.chart_resample_bin_width.total_seconds() / 3600
    # Calculate the bin shift
    bin_shift = config.chart_resample_bin_width / 2

    # Convert the site series and median index to matplotlib dates
    sts = _to_mpl_dates(pd.DatetimeIndex(site_series.index), config.chart_time_zone, bin_shift)
    mts = _to_mpl_dates(pd.DatetimeIndex(median.index), config.chart_time_zone, bin_shift)

    # Plot the site series and median
    ax.bar(
        sts, site_series.values,
        width=(resample_bin_width_hours - 1) / 24,
        color=config.chart_color,
        label=f'{config.site_map[site_id]}',
    )
    ax.plot(
        mts, median.values,
        color=config.ranking_avg_color,
        linestyle=config.ranking_avg_linestyle,
        linewidth=config.ranking_avg_linewidth,
        marker=config.ranking_avg_marker,
        markersize=config.ranking_avg_markersize,
        label=f'{config.ranking_avg_label.replace(r'\n', '\n')}',
    )

    # Apply plot style specific to this plot
    fig.autofmt_xdate(rotation=45)
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.set_ylabel(f'{config.chart_label.replace(r'\n', ' ')} / {config.chart_unit}', labelpad=15)
    ax.legend()
    fig.subplots_adjust(top=config.chart_top_adjust, bottom=config.chart_bottom_adjust)

    ax.spines[:].set_color(config.chart_text_color)
    ax.tick_params(colors=config.chart_text_color)
    ax.yaxis.label.set_color(config.chart_text_color)
    ax.xaxis.label.set_color(config.chart_text_color)

def _embed_chart(
        template: Template,
        site_series: pd.Series,
        median: pd.Series,
        site_id: str,
        config: RankingConfig,
        width_px: int, height_px: int,
    ) -> None:
    """Embed the plot into the template."""
    # Create the plot
    fig, ax = subplots(width_px, height_px, dpi=config.chart_dpi)
    # Plot the site series vs the median
    _plot_site_vs_median(ax, fig, site_series, median, site_id, config)
    # Embed the plot into the template
    template.embed(Figure(fig, config.chart_slot))

def _embed_ranking(
        template: Template,
        headers: list[str],
        rows: list[list],
        highlight: int,
        config: RankingConfig,
        width_px: int,
        height_px: int,
    ) -> None:
    """Embed the ranking into the template."""
    table_element = Table(
        slot_id=config.ranking_slot,
        headers=headers, rows=rows,
        width=width_px, height=height_px,
        col_widths=[2, 5, 4], header_line_factor=0.75,
    )
    table_element.highlight_row(highlight, config.ranking_highlight_color)
    if config.ranking_include_emoticon:
        table_element.place_emoji_in_row(
            highlight, _select_emoticon(highlight + 1, len(rows)),
        )
    template.embed(table_element)

def _embed_title(template: Template, config: TitleConfig, width_py: int, height_px: int) -> None:
    """Embed the title into the template."""
    # Create the title element
    title_element = Title(
        slot_id=config.title_slot,
        title=config.title_label, font_size=config.title_font_size, color=config.title_color,
        width=width_py, height=height_px,
    )
    # Embed the title element into the template
    template.embed(title_element)

def _render_site_rating(
        measurement: str,
        site_id: str,
        site_series: pd.Series,
        median: pd.Series,
        ranking_headers: list[str],
        ranking_rows: list[list],
        ranking_highlight: int,
        processing_date: datetime,
        config: RankingConfig,
    ) -> None:
    """Render the site ranking for the measurement and site."""
    LOGGER.info(f'creating ranking plot for {measurement!r}/site={site_id!r}')

    template = Template(config.template_path)

    # Check if the template has the required slots
    required_slots = [config.title_slot, config.chart_slot, config.ranking_slot]
    if not template.check_slot_presence(required_slots):
        str_required_slots = ', '.join(required_slots)
        LOGGER.warning(f'template "{config.template_path!r}" does not have the required slots: {str_required_slots}')
        return

    # Embed the title into the template
    title_dimensions = template.get_slot_dimensions(config.title_slot)
    LOGGER.debug(f'adding title to template with dimensions: {title_dimensions}')
    _embed_title(template, config, *title_dimensions)

    # Embed the plot into the template
    chart_dimensions = template.get_slot_dimensions(config.chart_slot)
    LOGGER.debug(f'adding chart to template with dimensions: {chart_dimensions}')
    _embed_chart(template, site_series, median, site_id, config, *chart_dimensions)

    # Embed the ranking into the template
    ranking_dimensions = template.get_slot_dimensions(config.ranking_slot)
    LOGGER.debug(f'adding ranking to template with dimensions: {ranking_dimensions}')
    _embed_ranking(template, ranking_headers, ranking_rows, ranking_highlight, config, *ranking_dimensions)

    # Render the template
    out_svg, out_png = get_output_paths(config, site_id, measurement, processing_date)
    template.render(out_svg[0], out_png[0])
    if len(out_svg) > 1:
        for out_svg_path in out_svg[1:]:
            shutil.copy2(out_svg[0], out_svg_path)
        for out_png_path in out_png[1:]:
            shutil.copy2(out_png[0], out_png_path)
    LOGGER.info(f'rendered ranking plot for {measurement!r}/site={site_id!r} to {out_svg} and {out_png}')
