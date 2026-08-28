"""Tests for SVG template, table, title, figure, and render helpers."""
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from energy_consumption_visualization.postprocess.ranking import _EMOJI_DIR
from energy_consumption_visualization.render.figure import Figure
from energy_consumption_visualization.render.table import Table
from energy_consumption_visualization.render.template import Template
from energy_consumption_visualization.render.title import Title
from energy_consumption_visualization.render.util import get_local_timezone, resvg_font_dirs

SVG_NS = 'http://www.w3.org/2000/svg'


def _write_svg(path: Path, body: str) -> Path:
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'
        f'{body}'
        '</svg>',
        encoding='utf-8',
    )
    return path


def test_table_body_row_ids_highlight_and_emoji():
    table = Table(
        headers=['Rank', 'Address'],
        rows=[['1', 'A Street'], ['2', 'B Street']],
        width=400,
        height=200,
        slot_id='slot2',
        col_widths=[1, 2],
    )
    root = table.element
    assert root.xpath("//*[@id='body-row-0']")
    assert root.xpath("//*[@id='body-row-1']")

    table.highlight_row(0, '#d1503c')
    group = table._body_row_group(table.element, 0)
    rects = [el for el in group if el.tag == f'{{{SVG_NS}}}rect']
    assert rects
    assert rects[0].get('fill') == '#d1503c'
    texts = group.findall(f'{{{SVG_NS}}}text')
    assert texts
    assert all(t.get('font-weight') == 'bold' for t in texts)

    emoji = _EMOJI_DIR / 'party_popper.svg'
    table.place_emoji_in_row(0, emoji)
    nested = group.findall(f'{{{SVG_NS}}}svg')
    assert nested


def test_table_bad_col_widths_raises():
    table = Table(
        headers=['A', 'B'],
        rows=[['1', '2']],
        width=100,
        height=50,
        slot_id='slot2',
        col_widths=[1],
    )
    with pytest.raises(ValueError, match='col_widths length'):
        _ = table.element


def test_title_viewbox_and_text():
    title = Title(
        title='Hello',
        font_size=24,
        color='#226676',
        width=200,
        height=40,
        slot_id='title',
    )
    root = title.element
    assert root.get('viewBox') == '0 0 200 40'
    texts = root.findall(f'{{{SVG_NS}}}text')
    assert texts
    assert texts[0].text == 'Hello'
    assert title.slot_id == 'title'


def test_template_slot_presence_and_dimensions(template_path):
    template = Template(template_path)
    assert template.check_slot_presence(['title', 'slot1', 'slot2'])
    with pytest.warns(UserWarning, match='not found'):
        assert template.check_slot_presence(['missing']) is False

    width, height = template.get_slot_dimensions('title')
    assert width == 1000
    assert height == 80

    with pytest.raises(RuntimeError, match='not found'):
        template.get_slot_dimensions('nope')


def test_template_embed_replaces_slot(template_path):
    template = Template(template_path)
    title = Title(
        title='Ranked',
        font_size=20,
        color='#226676',
        width=100,
        height=20,
        slot_id='title',
    )
    template.embed(title)
    assert not template._template.xpath("//*[@id='title']")
    nested = template._template.xpath(f"//*[local-name()='svg']")
    assert nested


def test_slot_bbox_rect_and_path(tmp_path):
    rect_svg = _write_svg(
        tmp_path / 'rect.svg',
        '<rect id="slot" x="10" y="20" width="40" height="30"/>',
    )
    template = Template(rect_svg)
    x, y, w, h = template._slot_bbox(template._template.xpath("//*[@id='slot']")[0])
    assert (x, y, w, h) == pytest.approx((10, 20, 40, 30))

    path_svg = _write_svg(
        tmp_path / 'path.svg',
        '<path id="slot" d="M 0 0 H 50 V 25 H 0 Z"/>',
    )
    path_template = Template(path_svg)
    _, _, pw, ph = path_template._slot_bbox(
        path_template._template.xpath("//*[@id='slot']")[0]
    )
    assert pw == pytest.approx(50)
    assert ph == pytest.approx(25)


def test_slot_bbox_nested_children_raises(tmp_path):
    svg = _write_svg(
        tmp_path / 'nested.svg',
        '<g id="slot"><rect x="0" y="0" width="10" height="10"/></g>',
    )
    template = Template(svg)
    slot = template._template.xpath("//*[@id='slot']")[0]
    with pytest.raises(RuntimeError, match='nested elements'):
        template._slot_bbox(slot)


def test_slot_bbox_zero_size_raises(tmp_path):
    svg = _write_svg(
        tmp_path / 'empty.svg',
        '<rect id="slot" x="0" y="0" width="0" height="10"/>',
    )
    template = Template(svg)
    slot = template._template.xpath("//*[@id='slot']")[0]
    with pytest.raises(RuntimeError, match='no dimensions'):
        template._slot_bbox(slot)


def test_figure_namespaces_ids():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    element = Figure(fig, 'slot1').element
    ids = [el.get('id') for el in element.iter() if el.get('id')]
    assert ids
    assert all(i.startswith('slot1__') for i in ids)


def test_get_local_timezone_fi_and_unknown():
    utc = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    tz = get_local_timezone('FI', utc)
    assert tz.zone == 'Europe/Helsinki'
    with pytest.raises(ValueError, match='No timezones found'):
        get_local_timezone('ZZ', utc)


def test_resvg_font_dirs():
    dirs = resvg_font_dirs()
    assert dirs
    font_dir = Path(dirs[0])
    assert font_dir.is_dir()
    assert font_dir.name == 'ttf'
