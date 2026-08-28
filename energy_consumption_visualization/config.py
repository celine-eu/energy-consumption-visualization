"""
Channel and summary configuration loaded from config.yml.
"""
import dataclasses
import datetime
import typing
import pathlib

from .util import get_color, get_as_list, parse_duration, parse_sites

@dataclasses.dataclass(frozen=True)
class HistoryProviderConfig:
    """Identity used to fetch TimescaleDB history."""
    dp_name: str
    dp_unit: typing.Optional[str] = None
    dp_data_provider: typing.Optional[str] = None
    dp_device_id: typing.Optional[str] = None
    dp_location_code: typing.Optional[str] = None
    retry_n: int = 0
    retry_wait_s: float = 5

@dataclasses.dataclass(frozen=True)
class ChartConfig:
    chart_slot: str
    chart_label: str
    chart_unit: str
    chart_resample_bin_width: datetime.timedelta
    chart_resample_method: str
    chart_time_zone: str
    chart_dpi: int
    chart_text_color: str
    chart_top_adjust: float
    chart_bottom_adjust: float
    chart_title: typing.Optional[str]
    chart_title_color: typing.Optional[str]
    chart_color: typing.Optional[str]
    chart_linestyle: typing.Optional[str]
    chart_linewidth: typing.Optional[float]
    chart_marker: typing.Optional[str]
    chart_markersize: typing.Optional[float]
    chart_autoscale_factor: typing.Optional[float]

@dataclasses.dataclass(frozen=True)
class OutputConfig:
    output_path: list[str]
    output_file_name: str
    output_date_format: str

@dataclasses.dataclass(frozen=True)
class TitleConfig:
    title_slot: str
    title_label: str
    title_font_size: int
    title_color: str

@dataclasses.dataclass(frozen=True)
class RankingConfig(TitleConfig, ChartConfig, OutputConfig):
    template_path: pathlib.Path
    site_map: dict[str, str]
    apartments_by_site: dict[str, int]
    ranking_slot: str
    ranking_include_emoticon: bool
    ranking_avg_label: str
    ranking_avg_color: str
    ranking_highlight_color: str
    ranking_avg_marker: str
    ranking_avg_markersize: float
    ranking_avg_linestyle: str
    ranking_avg_linewidth: float
    ranking_avg_font_size: float
    ranking_value_decimals: int
    ranking_rank_label: str
    ranking_address_label: str

    @staticmethod
    def load(
            ranking_config: dict[str, typing.Any] | None,
            site_map: dict[str, str],
            apartments_by_site: dict[str, int]
        ) -> typing.Optional['RankingConfig']:
        if ranking_config is None:
            return None

        try:
            value_decimals = int(ranking_config.get('ranking_value_decimals', 0))
            if value_decimals < 0:
                raise ValueError(f'value_decimals must be >= 0, got {value_decimals}')

            return RankingConfig(
                #
                # Mandatory fields
                #
                template_path=pathlib.Path(ranking_config['template_path']).resolve(strict=True),
                site_map=site_map,
                apartments_by_site=apartments_by_site,
                ranking_slot=ranking_config['ranking_slot'],
                ranking_include_emoticon=ranking_config['ranking_include_emoticon'],
                ranking_avg_label=ranking_config['ranking_avg_label'],
                ranking_avg_color=get_color(ranking_config['ranking_avg_color']),
                ranking_highlight_color=get_color(ranking_config['ranking_highlight_color']),
                chart_slot=ranking_config['chart_slot'],
                chart_time_zone=ranking_config['chart_time_zone'],
                chart_label=ranking_config['chart_label'],
                chart_unit=ranking_config['chart_unit'],
                chart_resample_bin_width=parse_duration(ranking_config['chart_resample_bin_width']),
                title_slot=ranking_config['title_slot'],
                title_label=ranking_config['title_label'],
                title_font_size=ranking_config['title_font_size'],
                title_color=get_color(ranking_config['title_color']),
                #
                # Optional fields
                #
                chart_resample_method=ranking_config.get('chart_resample_method', 'sum'),
                chart_dpi=int(ranking_config.get('chart_dpi', 120)),
                chart_text_color=get_color(ranking_config.get('chart_text_color', 'midnight ink')),
                chart_top_adjust=float(ranking_config.get('chart_top_adjust', 1.0)),
                chart_bottom_adjust=float(ranking_config.get('chart_bottom_adjust', 0.14)),
                chart_title=None,
                chart_title_color=None,
                chart_color=get_color(ranking_config.get('chart_color', 'deep teal')),
                chart_linestyle=ranking_config.get('chart_linestyle', '-'),
                chart_linewidth=ranking_config.get('chart_linewidth', 0.5),
                chart_marker=ranking_config.get('chart_marker', 's'),
                chart_markersize=ranking_config.get('chart_markersize', 4),
                chart_autoscale_factor=ranking_config.get('chart_autoscale_factor'),
                ranking_rank_label=ranking_config.get('ranking_rank_label', 'Rank'),
                ranking_address_label=ranking_config.get('ranking_address_label', 'Address'),
                ranking_avg_marker=ranking_config.get('rating_avg_marker', 's'),
                ranking_avg_markersize=float(ranking_config.get('ranking_avg_markersize', 4)),
                ranking_avg_linestyle=ranking_config.get('ranking_avg_linestyle', '-'),
                ranking_avg_linewidth=float(ranking_config.get('ranking_avg_linewidth', 0.5)),
                ranking_avg_font_size=float(ranking_config.get('ranking_avg_font_size', 15.6)),
                ranking_value_decimals=value_decimals,
                output_path=get_as_list(ranking_config.get('output_path', '{date}/{site_id}')),
                output_file_name=ranking_config.get('output_file_name', '{measurement}-ranking.{ext}'),
                output_date_format=ranking_config.get('output_date_format', '%Y%m%d-%H%M'),
            )
        except KeyError as exc:
            raise RuntimeError(f'Missing rating config field: {exc}') from exc
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f'Invalid rating config: {exc}') from exc

@dataclasses.dataclass(frozen=True)
class CompareAgainstConfig(ChartConfig):
    history_provider: HistoryProviderConfig

    @staticmethod
    def load(
            compare_against_config: dict[str, typing.Any]
        ) -> 'CompareAgainstConfig':

        try:
            return CompareAgainstConfig(
                chart_slot=compare_against_config['chart_slot'],
                chart_title=compare_against_config['chart_title'],
                chart_label=compare_against_config['chart_label'],
                chart_unit=compare_against_config['chart_unit'],
                chart_resample_bin_width=parse_duration(compare_against_config['chart_resample_bin_width']),
                chart_resample_method=compare_against_config['chart_resample_method'],
                chart_time_zone=compare_against_config['chart_time_zone'],
                chart_dpi=int(compare_against_config['chart_dpi']),
                chart_text_color=get_color(compare_against_config['chart_text_color']),
                chart_top_adjust=float(compare_against_config.get('chart_top_adjust', 0.87)),
                chart_bottom_adjust=float(compare_against_config.get('chart_bottom_adjust', 0.14)),
                chart_title_color=get_color(compare_against_config.get('chart_title_color', 'deep teal')),
                chart_color=get_color(compare_against_config.get('chart_color', 'deep teal')),
                chart_linestyle=None,
                chart_linewidth=None,
                chart_marker=None,
                chart_markersize=None,
                chart_autoscale_factor=compare_against_config.get('chart_autoscale_factor'),
                history_provider=HistoryProviderConfig(**compare_against_config['history_provider']),
            )
        except KeyError as exc:
            raise RuntimeError(f'Missing compare against config field: {exc}') from exc
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f'Invalid compare against config: {exc}') from exc

@dataclasses.dataclass(frozen=True)
class CompareConfig(TitleConfig, ChartConfig, OutputConfig):
    site_map: dict[str, str]
    compare_against: list[CompareAgainstConfig]
    compare_font_size: float
    template_path: pathlib.Path

    @staticmethod
    def load(
            compare_config: dict[str, typing.Any] | None,
            site_map: dict[str, str],
        ) -> 'CompareConfig | None':
        if compare_config is None:
            return None

        try:
            return CompareConfig(
                #
                # Mandatory fields
                #
                site_map=site_map,
                compare_against=[
                    CompareAgainstConfig.load(a) for a in compare_config['against']
                ],
                template_path=pathlib.Path(compare_config['template_path']).resolve(strict=True),
                chart_slot=compare_config['chart_slot'],
                chart_time_zone=compare_config['chart_time_zone'],
                chart_title=compare_config['chart_title'],
                chart_label=compare_config['chart_label'],
                chart_unit=compare_config['chart_unit'],
                chart_resample_bin_width=parse_duration(compare_config['chart_resample_bin_width']),
                chart_resample_method=compare_config['chart_resample_method'],
                title_label=compare_config['title_label'],
                title_font_size=compare_config['title_font_size'],
                title_color=get_color(compare_config['title_color']),
                #
                # Optional fields
                #
                compare_font_size=float(compare_config.get('compare_font_size', 15.6)),
                chart_dpi=int(compare_config.get('chart_dpi', 120)),
                chart_text_color=get_color(compare_config.get('chart_text_color', 'midnight ink')),
                chart_top_adjust=float(compare_config.get('chart_top_adjust', 0.87)),
                chart_bottom_adjust=float(compare_config.get('chart_bottom_adjust', 0.14)),
                chart_title_color=get_color(compare_config.get('chart_title_color', 'deep teal')),
                chart_color=get_color(compare_config.get('chart_color', 'deep teal')),
                chart_linestyle=None,
                chart_linewidth=None,
                chart_marker=None,
                chart_markersize=None,
                chart_autoscale_factor=compare_config.get('chart_autoscale_factor'),
                title_slot=compare_config.get('title_slot', 'title'),
                output_path=get_as_list(compare_config.get('output_path', '{date}/{site_id}')),
                output_file_name=compare_config.get('output_file_name', '{measurement}-compare.{ext}'),
                output_date_format=compare_config.get('output_date_format', '%Y%m%d-%H%M'),
            )
        except KeyError as exc:
            raise RuntimeError(f'Missing compare config field: {exc}') from exc
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f'Invalid compare config: {exc}') from exc

@dataclasses.dataclass(frozen=True)
class ChannelConfig:
    """Static configuration of a single measurement channel (all sites)."""
    name: str
    site_ids: typing.List[str]
    stream_template: str
    history_window: datetime.timedelta
    history_provider: HistoryProviderConfig
    ranking_config: RankingConfig | None
    compare_config: CompareConfig | None

    def stream_for(self, site_id: str) -> str:
        return self.stream_template.format(site_id=site_id)

    @staticmethod
    def load_channel_configs(channels: dict) -> typing.List['ChannelConfig']:
        if not channels:
            raise RuntimeError('channels config is empty')

        configs = []
        for channel_key, entry in channels.items():
            entry = dict(entry)
            try:
                site_map, apartments_by_site = parse_sites(entry['sites'])
                config = ChannelConfig(
                    name=channel_key,
                    site_ids=list(site_map.keys()),
                    stream_template=entry['stream_template'],
                    history_window=parse_duration(entry['history_window']),
                    history_provider=HistoryProviderConfig(**entry['history_provider']),
                    ranking_config=RankingConfig.load(entry.get('ranking'), site_map, apartments_by_site),
                    compare_config=CompareConfig.load(entry.get('compare'), site_map),
                )
            except KeyError as exc:
                raise RuntimeError(
                    f'Missing config field for channel {channel_key}: {exc}'
                ) from exc
            except TypeError as exc:
                raise RuntimeError(
                    f'Invalid channel config for channel {channel_key}: {exc}'
                ) from exc
            configs.append(config)
        return configs
