from .svg_element import *
from .colors import *

class Title(SvgElement):
    """
    A title element.
    """

    def __init__(
            self, title: str, font_size: float, color: str,
            width: float, height: float,
            slot_id: str,
        ) -> None:
        self._title = title
        self._font_size = font_size
        self._color = color
        self._width = width
        self._height = height
        self._slot_id = slot_id

    @property
    def element(self) -> etree._Element:
        return self._make_title_svg()

    @property
    def slot_id(self) -> str:
        return self._slot_id

    def _make_title_svg(self) -> etree._Element:
        """
        Make a title SVG element.

        Parameters:
            text_color: Color of the text. Default: "#226676".
        """
        # Create the root SVG element
        root = etree.Element(f"{{{SVG_NS}}}svg", nsmap={None: SVG_NS})
        # Set the viewBox of the SVG element
        root.set("viewBox", f"0 0 {self._width} {self._height}")

        self._add_text(root, self._width / 2, self._height / 2, self._title, self._color, "bold", self._font_size, anchor="middle")
        return root
