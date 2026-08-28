from pathlib import Path

from .svg_element import *
from .colors import *

# Default values
_DEFAULT_HEADER_COLOR = DEEP_TEAL
_DEFAULT_STRIPE = PALE_MIST
_DEFAULT_GRID = SOFT_TEAL
_DEFAULT_RULE = DEEP_TEAL
_DEFAULT_TEXT_COLOR = MIDNIGHT_INK
_DEFAULT_THIN = 1
_DEFAULT_THICK = 3
_DEFAULT_PAD = 45
_DEFAULT_BODY_FONT_SIZE = 26
_EMOJI_ROW_HEIGHT_FACTOR = 0.62


class Table(SvgElement):
    """
    A table element.
    """

    def __init__(
            self, headers: list[str], rows: list[list[str]],
            width: float, height: float,
            slot_id: str,
            col_widths: list[float] | None = None,
            header_line_factor: float = 0.5,
        ) -> None:
        self._headers = headers
        self._rows = rows
        self._width = width
        self._height = height
        self._slot_id = slot_id
        self._col_widths = col_widths
        self._header_line_factor = header_line_factor
        self._root: etree._Element | None = None
        self._header_h = 0.0
        self._body_rh = 0.0
        self._pad = _DEFAULT_PAD

    @property
    def element(self) -> etree._Element:
        if self._root is None:
            self._root = self._make_table_svg()
        return self._root

    @property
    def slot_id(self) -> str:
        return self._slot_id

    def highlight_row(self, row_index: int, color: str) -> None:
        """Update an existing body row: highlight fill and bold text."""
        group = self._body_row_group(self.element, row_index)
        y = self._header_h + row_index * self._body_rh
        rect_tag = f"{{{SVG_NS}}}rect"
        rects = [el for el in group if el.tag == rect_tag]
        if rects:
            rects[0].set("fill", color)
        else:
            r = etree.Element(rect_tag)
            r.set("x", "0")
            r.set("y", f"{y}")
            r.set("width", f"{self._width}")
            r.set("height", f"{self._body_rh}")
            r.set("fill", color)
            group.insert(0, r)
        for t in group.findall(f"{{{SVG_NS}}}text"):
            t.set("font-weight", "bold")

    def place_emoji_in_row(self, row_index: int, path: Path) -> None:
        """Place an emoji at the right edge of a body row, padded from the edge."""
        group = self._body_row_group(self.element, row_index)
        size = self._body_rh * _EMOJI_ROW_HEIGHT_FACTOR
        x = self._width - self._pad - size
        y = self._header_h + (row_index + 0.5) * self._body_rh
        self._add_emoji(group, path, x, y, size)

    def _body_row_group(self, root: etree._Element, row_index: int) -> etree._Element:
        """Return the ``<g>`` for a body row index."""
        matches = root.xpath("//*[@id=$i]", i=f"body-row-{row_index}")
        if not matches:
            raise ValueError(f"body row {row_index} not found in table")
        return matches[0]

    def _make_table_svg(
            self, stripe: str = _DEFAULT_STRIPE, grid: str = _DEFAULT_GRID, rule: str = _DEFAULT_RULE,
            header_color: str = _DEFAULT_HEADER_COLOR, text_color: str = _DEFAULT_TEXT_COLOR,
            thin: float = _DEFAULT_THIN, thick: float = _DEFAULT_THICK, pad: float = _DEFAULT_PAD
        ) -> etree._Element:
        """
        Make a table SVG element.

        Parameters:
            stripe: Color of the stripe background. Default: "#eef3f4".
            grid: Color of the grid lines. Default: "#cbd5d8".
            rule: Color of the rules. Default: "#226676".
            header_color: Color of the header labels. Default: "#226676".
            thin: Thickness of the grid lines. Default: 1.
            thick: Thickness of the rules. Default: 3.
            pad: Padding between columns in pixels. Default: 45.
        """
        # Calculate the number of columns and body rows
        ncol, n_body = len(self._headers), len(self._rows)
        # Header height grows with multi-line labels: weight = 1 + (lines-1)*X
        header_lines = max((h.count(r"\n") + 1 for h in self._headers), default=1)
        header_weight = 1 + (header_lines - 1) * self._header_line_factor
        unit = self._height / (header_weight + n_body)
        header_h = unit * header_weight
        body_rh = unit
        self._header_h = header_h
        self._body_rh = body_rh
        self._pad = pad
        # Calculate the column widths
        col_widths = self._resolved_col_widths(ncol)
        # Calculate the column x-coordinates
        col_x0 = self._col_x0(col_widths)
        # Create the root SVG element
        root = etree.Element(f"{{{SVG_NS}}}svg", nsmap={None: SVG_NS})
        # Set the viewBox of the SVG element
        root.set("viewBox", f"0 0 {self._width} {self._height}")

        # Body row groups (stripe + text) before chrome so grid/rules paint on top
        font_size = _DEFAULT_BODY_FONT_SIZE
        for i, r in enumerate(self._rows):
            group = etree.SubElement(root, f"{{{SVG_NS}}}g")
            group.set("id", f"body-row-{i}")
            if (i + 1) % 2 == 0:
                self._add_rect(
                    group, 0, header_h + i * body_rh, self._width, body_rh, stripe,
                )
            y_mid = header_h + (i + 0.5) * body_rh
            for j, cell in enumerate(r):
                x, anchor = self._cell_x(j, col_x0, col_widths, pad)
                self._add_text(
                    group, x, y_mid, str(cell), text_color, "normal", font_size, anchor,
                )

        # Horizontal grid lines only: thin interior boundaries between body rows
        for k in range(1, n_body):
            y = header_h + k * body_rh
            self._add_line(root, 0, y, self._width, y, grid, thin)

        # Thick horizontal rules: above + below header, and after the last row.
        # Inset the top/bottom rules by half the stroke so they aren't clipped by
        # the slot edge (which would render them at half thickness).
        half = thick / 2
        for y in (half, header_h, self._height - half):
            self._add_line(root, 0, y, self._width, y, rule, thick)

        # Header labels: dark, no background; "\n" → multi-line left-aligned text
        # (first column is centered)
        for j, htx in enumerate(self._headers):
            x, anchor = self._cell_x(j, col_x0, col_widths, pad)
            if r"\n" in htx and j != 0:
                self._add_text(root, x, header_h * 0.5, htx, header_color, "bold", 26, anchor="start")
            else:
                self._add_text(root, x, header_h * 0.5, htx, header_color, "bold", 26, anchor=anchor)

        return root

    def _resolved_col_widths(self, ncol: int) -> list[float]:
        """Pixel widths from relative ``col_widths`` weights (equal if omitted)."""
        if self._col_widths is None:
            weights = [1.0] * ncol
        else:
            if len(self._col_widths) != ncol:
                raise ValueError(
                    f"col_widths length {len(self._col_widths)} != number of columns {ncol}"
                )
            weights = list(self._col_widths)
        total = sum(weights)
        if total <= 0:
            raise ValueError("col_widths must sum to a positive value")
        return [self._width * w / total for w in weights]

    def _col_x0(self, widths: list[float]) -> list[float]:
        """Left edge of each column from column widths."""
        x0 = [0.0]
        for w in widths[:-1]:
            x0.append(x0[-1] + w)
        return x0

    def _cell_x(
            self, j: int, col_x0: list[float], col_widths: list[float], pad: float
        ) -> tuple[float, str]:
        """
        Calculate the x-coordinate and anchor for a cell.
        First column is centered; remaining columns are left-aligned with padding.
        """
        if j == 0:
            return (col_x0[j] + col_widths[j] / 2, "middle")
        return (col_x0[j] + pad, "start")
