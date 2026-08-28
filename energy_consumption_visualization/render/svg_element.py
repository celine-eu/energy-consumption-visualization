from pathlib import Path

from .element import *
from .colors import *

# SVG namespace
SVG_NS = "http://www.w3.org/2000/svg"


class SvgElement(Element):
    """
    An SVG element.
    """

    def _add_rect(
            self, root: etree._Element,
            x: float, y: float, ww: float, hh: float, fill: str
        ) -> None:
        """
        Create a rectangle element.
        """
        r = etree.SubElement(root, f"{{{SVG_NS}}}rect")
        r.set("x", f"{x}")
        r.set("y", f"{y}")
        r.set("width", f"{ww}")
        r.set("height", f"{hh}")
        r.set("fill", fill)

    def _add_line(
            self, root: etree._Element,
            x1: float, y1: float, x2: float, y2: float,
            color: str, width: float
        ) -> None:
        """
        Create a line element.
        """
        l = etree.SubElement(root, f"{{{SVG_NS}}}line")
        l.set("x1", f"{x1}")
        l.set("y1", f"{y1}")
        l.set("x2", f"{x2}")
        l.set("y2", f"{y2}")
        l.set("stroke", color)
        l.set("stroke-width", f"{width}")

    def _add_text(
            self, root: etree._Element,
            x: float, y: float, s: str,
            fill: str, weight: str = "normal",
            size: float = 24, anchor: str = "middle"
        ) -> None:
        """
        Create a text element. If ``s`` contains ``\n``, emit M+1 ``tspan`` lines
        (for M newlines), vertically centered on ``y``.
        """
        lines = s.split(r"\n")
        line_h = size * 1.2
        y0 = y - (len(lines) - 1) * line_h / 2

        t = etree.SubElement(root, f"{{{SVG_NS}}}text")
        t.set("x", f"{x}")
        t.set("y", f"{y0}")
        t.set("font-family", "DejaVu Sans, sans-serif")
        t.set("font-size", f"{size}")
        t.set("fill", fill)
        t.set("font-weight", weight)
        t.set("text-anchor", anchor)
        t.set("dominant-baseline", "central")

        if len(lines) == 1:
            t.text = lines[0]
            return

        for i, line in enumerate(lines):
            ts = etree.SubElement(t, f"{{{SVG_NS}}}tspan")
            ts.set("x", f"{x}")
            if i > 0:
                ts.set("dy", f"{line_h}")
            ts.text = line

    def _add_emoji(
            self, root: etree._Element,
            path: Path, x: float, y: float, size: float = 28,
        ) -> None:
        """
        Inline an emoji SVG as a nested ``<svg>``, centered vertically on ``y``.
        """
        icon = etree.parse(str(path)).getroot()
        icon.set("x", f"{x}")
        icon.set("y", f"{y - size / 2}")
        icon.set("width", f"{size}")
        icon.set("height", f"{size}")
        root.append(icon)
