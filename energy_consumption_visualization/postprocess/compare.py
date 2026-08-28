from __future__ import annotations

import logging
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import shutil

from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from ..config import ChartConfig, CompareConfig, CompareAgainstConfig
from ..render import Figure, Template, Title
from ..render.util import get_local_timezone, subplots
from ..util import get_output_paths
from ..sample import Sample

LOGGER = logging.getLogger('energy_consumption_visualization.postprocess.compare')

def compare(
        measurement: str,
        site_id: str,
        samples: list[Sample],
        extra_histories: dict[str, list[Sample]],
        config: CompareConfig,
        processing_date: datetime,
    ) -> None:
    """
    Postprocessing: compare the given measurement for a specific site with other data
    """
    LOGGER.info(f'processing comparison at {processing_date.strftime("%Y-%m-%d %H:%M:%S")}')

    site_series = _build_measurement_series(measurement, site_id, samples, config)

    extra_configs = {a.history_provider.dp_name: a for a in config.compare_against}
    extra_series = _build_extra_series(extra_histories, extra_configs)

    _apply_common_plot_style(config)

    _render_site_comparison(measurement, site_id, site_series, extra_series, processing_date, config, extra_configs)

def _samples_to_series(
        samples: list[Sample],
        config: ChartConfig,
    ) -> pd.Series:
    """Convert the samples to a pandas series."""
    df = pd.DataFrame([Sample.to_dict(s, include_quality=False) for s in samples])
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)

    bin_width = config.chart_resample_bin_width
    method = config.chart_resample_method
    return df.resample(bin_width).agg(method)['value']  # type: ignore[return-value]

def _build_measurement_series(
        measurement: str,
        site_id: str,
        samples: list[Sample],
        config: ChartConfig,
    ) -> pd.Series:
    """Build the series for the site."""
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
        return pd.Series()

    # Convert the samples to a pandas series
    return _samples_to_series(samples, config)

def _build_extra_series(
        histories: dict[str, list[Sample]],
        extra_configs: dict[str, CompareAgainstConfig],
    ) -> dict[str, pd.Series]:
    """Build the series for the comparison."""
    series: dict[str, pd.Series] = {}
    # Iterate over all sites in the histories
    for name, samples in histories.items():
        # Sort the samples by timestamp
        samples.sort(key=lambda s: s.timestamp)
        try:
            LOGGER.debug(
                f'processing samples for {name!r}: '
                f'samples={len(samples)}, first={samples[0].timestamp}, last={samples[-1].timestamp}'
            )
        except IndexError:
            LOGGER.warning(
                f'no samples for {name!r}'
            )
            continue

        # Convert the samples to a pandas series
        series[name] = _samples_to_series(samples, extra_configs[name])
    return series

def _to_mpl_dates(
        index: pd.DatetimeIndex,
        tz_name: str,
        bin_shift: timedelta,
    ):
    """Convert the index to matplotlib dates."""
    tz = get_local_timezone(tz_name, cast(datetime, index[-1]))
    return mdates.date2num(index.tz_convert(tz) + bin_shift)


def _apply_common_plot_style(config: CompareConfig) -> None:
    """Apply the common plot style."""
    plt.rcParams.update({
        'font.size': config.compare_font_size,
        'xtick.labelsize': 0.62 * config.compare_font_size,
        'ytick.labelsize': 0.62 * config.compare_font_size,
        'legend.fontsize': 0.62 * config.compare_font_size,
        'figure.titleweight': 'bold',
    })

def _plot_series(
        ax: plt.Axes,
        fig: plt.Figure,
        series: pd.Series,
        config: ChartConfig,
    ) -> None:
    """Plot the series data."""
    # Calculate the resample bin width in hours
    resample_bin_width_hours = config.chart_resample_bin_width.total_seconds() / 3600
    # Calculate the bin shift
    bin_shift = config.chart_resample_bin_width / 2

    # Convert the site series and median index to matplotlib dates
    sts = _to_mpl_dates(pd.DatetimeIndex(series.index), config.chart_time_zone, bin_shift)

    # Plot the series
    ax.bar(
        sts, series.values,
        color=config.chart_color,
        linestyle=config.chart_linestyle,
        linewidth=config.chart_linewidth,
        width=(resample_bin_width_hours - 1) / 24,
    )

    # Apply plot style specific to this plot
    fig.autofmt_xdate(rotation=45)
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.set_ylabel(f'{config.chart_label.replace(r'\n', ' ')} / {config.chart_unit}', labelpad=15)
    fig.subplots_adjust(top=config.chart_top_adjust, bottom=config.chart_bottom_adjust)

    ax.spines[:].set_color(config.chart_text_color)
    ax.tick_params(colors=config.chart_text_color)
    ax.yaxis.label.set_color(config.chart_text_color)
    ax.xaxis.label.set_color(config.chart_text_color)

    if config.chart_autoscale_factor:
        bf = 1. - config.chart_autoscale_factor
        tf = 1. + config.chart_autoscale_factor
        ax.set_ylim(bottom=bf*float(series.values.min()), top=tf*float(series.values.max()))

    if config.chart_title:
        fig.suptitle(config.chart_title, color=config.chart_title_color)

def _embed_chart(
        template: Template,
        site_series: pd.Series,
        config: ChartConfig,
        width_px: int,
        height_px: int,
    ) -> None:
    """Embed the plot into the template."""
    # Create the plot
    fig, ax = subplots(width_px, height_px, dpi=config.chart_dpi)
    # Plot the site series
    _plot_series(ax, fig, site_series, config)
    # Embed the plot into the template
    template.embed(Figure(fig, config.chart_slot))

def _embed_title(
        template: Template,
        config: CompareConfig,
        site_id: str,
        width_px: int,
        height_px: int,
    ) -> None:
    """Embed the title into the template."""
    # Create the title element
    title_element = Title(
        slot_id=config.title_slot,
        title=config.title_label.format(site_label=config.site_map[site_id]),
        font_size=config.title_font_size, color=config.title_color,
        width=width_px, height=height_px,
    )
    # Embed the title element into the template
    template.embed(title_element)

def _render_site_comparison(
        measurement: str,
        site_id: str,
        site_series: pd.Series,
        extra_series: dict[str, pd.Series],
        processing_date: datetime,
        config: CompareConfig,
        extra_configs: dict[str, CompareAgainstConfig],
    ) -> None:
    """Render the site overview for the measurement and site."""
    LOGGER.info(f'creating comparison plot for {measurement!r}/site={site_id!r}')

    template = Template(config.template_path)

    # Check if the template has the required slots
    required_slots = [config.chart_slot, config.title_slot]
    for extra_config in config.compare_against:
        required_slots.append(extra_config.chart_slot)

    if not template.check_slot_presence(required_slots):
        str_required_slots = ', '.join(required_slots)
        LOGGER.warning(f'template "{config.template_path!r}" does not have the required slots: {str_required_slots}')
        return

    # Embed the title into the template
    title_dimensions = template.get_slot_dimensions(config.title_slot)
    LOGGER.debug(f'adding title to template with dimensions: {title_dimensions}')
    _embed_title(template, config, site_id, *title_dimensions)

    # Embed the main into the template
    chart_dimensions = template.get_slot_dimensions(config.chart_slot)
    LOGGER.debug(f'adding chart to template with dimensions: {chart_dimensions}')
    _embed_chart(template, site_series, config, *chart_dimensions)

    for dp_name, series in extra_series.items():
        extra_config = extra_configs[dp_name]
        extra_chart_dimensions = template.get_slot_dimensions(extra_config.chart_slot)
        LOGGER.debug(f'adding extra to template with dimensions: {extra_chart_dimensions}')
        _embed_chart(template, series, extra_config, *extra_chart_dimensions)

    # Render the template
    out_svg, out_png = get_output_paths(config, site_id, measurement, processing_date)
    template.render(out_svg[0], out_png[0])
    if len(out_svg) > 1:
        for out_svg_path in out_svg[1:]:
            shutil.copy2(out_svg[0], out_svg_path)
        for out_png_path in out_png[1:]:
            shutil.copy2(out_png[0], out_png_path)
    LOGGER.info(f'rendered rating plot for {measurement!r}/site={site_id!r} to {out_svg} and {out_png}')
