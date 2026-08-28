# Example configuration

YAML loaded at startup (`-c`, default `config.yml`).
`${ENV}` placeholders are expanded from the environment.
Field contract: [`energy_consumption_visualization/config.py`](energy_consumption_visualization/config.py).

This example defines one measurement channel (`heat`) with two sites, a ranking plot, and a comparison against outdoor temperature.

```yaml
channels:
  heat:
    sites:
      - id: site_north
        label: North Street 1
        n_apartments: 12
      - id: site_south
        label: South Avenue 8
        n_apartments: 24
    stream_template: regularize.heat.{site_id}
    history_window: 1w
    history_provider:
      dp_name: heat
      dp_unit: kWh
      dp_data_provider: regularize
      dp_device_id: null
    ranking:
      template_path: ./templates/ranking.svg
      title_slot: title
      title_label: Heating consumption per apartment
      title_font_size: 40
      title_color: deep teal
      chart_slot: slot1
      chart_label: Heating
      chart_unit: kWh
      chart_resample_bin_width: 3h
      chart_time_zone: FI
      ranking_slot: slot2
      ranking_include_emoticon: true
      ranking_avg_label: 'average of\nall buildings'
      ranking_avg_color: golden amber
      ranking_highlight_color: light terracotta
      chart_color: terracotta
      output_path:
        - ./img/{date}/{site_id}
        - ./img/latest/{site_id}
    compare:
      template_path: ./templates/compare.svg
      title_label: '{site_label}:\nHeating consumption'
      title_font_size: 40
      title_color: deep teal
      chart_slot: slot1
      chart_title: Heating consumption
      chart_label: consumption
      chart_unit: kWh
      chart_resample_bin_width: 3h
      chart_resample_method: sum
      chart_time_zone: FI
      chart_color: terracotta
      output_path:
        - ./img/{date}/{site_id}
        - ./img/latest/{site_id}
      against:
        - chart_slot: slot2
          chart_title: Outdoor temperature
          chart_label: temperature
          chart_unit: °C
          chart_resample_bin_width: 3h
          chart_resample_method: mean
          chart_time_zone: FI
          chart_dpi: 110
          chart_text_color: midnight ink
          chart_color: soft aqua
          history_provider:
            dp_name: outdoor_temp
            dp_unit: °C
            dp_data_provider: regularize
            dp_device_id: null

redis:
  host: localhost
  port: 6379
  db: 0
  password: ${REDIS_PASSWORD}

timescale:
  host: localhost
  port: 5432
  db: rdp_db
  user: ${POSTGRES_USER}
  password: ${POSTGRES_PASSWORD}

logging:
  root:
    level: WARNING
    handlers: [console]
  loggers:
    peewee:
      level: INFO
    matplotlib:
      level: WARNING
```
