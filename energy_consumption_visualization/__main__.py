import click
import pathlib
import pyrdp_commons.cli
import threading

from .channel import Channel
from .config import ChannelConfig
from .history import HistoryProvider
from .logger import LOGGER
from .util import load_redis_connection_pool


def run_service(config: dict, one_shot: bool = False) -> None:
    redis_pool = load_redis_connection_pool(redis_config=config['redis'])
    channel_configs = ChannelConfig.load_channel_configs(config['channels'])

    history_provider = HistoryProvider(config['timescale'])
    stop_event = threading.Event()

    channels = [
        Channel(
            config=channel_config,
            redis_pool=redis_pool,
            history_provider=history_provider,
            stop_event=stop_event,
        )
        for channel_config in channel_configs
    ]

    if one_shot:
        LOGGER.info(f'Starting {len(channels)} channels in one-shot mode ...')
    else:
        LOGGER.info(f'Starting {len(channels)} channels in service mode ...')

    for channel in channels:
        if one_shot:
            try:
                channel.process_once()
            except Exception as exc:
                LOGGER.exception(f'Processing failed for {channel.name}: {exc}')
        else:
            channel.start()

    if one_shot:
        LOGGER.info('One-shot mode finished')
        return

    try:
        while not stop_event.is_set():
            stop_event.wait(1)
    except KeyboardInterrupt:
        LOGGER.info('Stopping dashboard service ...')
    finally:
        stop_event.set()
        for channel in channels:
            channel.join(timeout=10)
        LOGGER.info('Dashboard service stopped')


@click.command()
@click.option('-c', '--config', default='config.yml', help='config file path')
@click.option(
    '--one-shot',
    is_flag=True,
    help='Process each channel once with datetime.now() and exit',
)
def main(config, one_shot):
    config_file_path = pathlib.Path(config).resolve(strict=True)
    config = pyrdp_commons.cli.setup_app(config_file=str(config_file_path), env_file=None)
    run_service(config, one_shot=one_shot)


if __name__ == '__main__':
    main()
