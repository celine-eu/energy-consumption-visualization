from __future__ import annotations

from io import BytesIO
from lxml import etree
from pathlib import Path
from svgelements import SVG

import warnings
import resvg_py  # Rust resvg engine: full SVG spec coverage (see note at bottom)

from .element import Element
from .util import resvg_font_dirs

class Template:
    """
    Embeds elements into a template and renders it to SVG and PNG.
    """

    def __init__(self, template: Path):
        p = template.resolve(strict=True)
        self._template = etree.parse(str(p)).getroot()
        self._font_family = "DejaVu Sans"

    def check_slot_presence(self, list_of_slot_ids: list[str]) -> bool:
        """
        Check if the slots with the given IDs are present in the template.
        """
        for slot_id in list_of_slot_ids:
            if not self._template.xpath(f"//*[@id='{slot_id}']"):
                warnings.warn(f"slot '{slot_id}' not found in template")
                return False
        return True

    def get_slot_dimensions(self, slot_id: str) -> tuple[int, int]:
        """
        Return (width, height) of the slot with the given ID, in pixels.
        """
        # Find the slot in the template
        matches = self._template.xpath("//*[@id=$i]", i=slot_id)
        if not matches:
            raise RuntimeError(f"slot '{slot_id}' not found in template")

        # Get the viewBox dimensions of the template
        _, _, vb_w, vb_h = map(float, self._template.get("viewBox").split())

        # Get the width and height of the template
        svg_w = float(self._template.get("width"))
        svg_h = float(self._template.get("height"))

        # Get the bounding box of the slot
        _, _, width, height = self._slot_bbox(matches[0])

        # Return the width and height of the slot, in pixels
        return round(width * svg_w / vb_w), round(height * svg_h / vb_h)

    def embed(self, element: Element) -> None:
        """
        Replace placeholder `slot_id` with the element, scaled to fit the slot.
        """
        # Find the slot in the template
        matches = self._template.xpath("//*[@id=$i]", i=element.slot_id)
        if not matches:
            raise RuntimeError(f"slot '{element.slot_id}' not found in template")
        slot = matches[0]
        # Get the bounding box of the slot
        x, y, w, h = self._slot_bbox(slot)

        # Position + size the nested element; its own viewBox scales the content to fit.
        node = element.element
        node.set("x", f"{x:.6f}")
        node.set("y", f"{y:.6f}")
        node.set("width", f"{w:.6f}")
        node.set("height", f"{h:.6f}")
        if node.get("viewBox") is None:
            node.set("viewBox", f"0 0 {w} {h}")

        # Slot aspect ratio already matches the element's aspect ratio, so we can drop the preserveAspectRatio attribute to avoid stretching.
        # If the slot's proportions change, either re-match the element's size or drop the following attribute to avoid stretching.
        node.set("preserveAspectRatio", "none")

        # Replace the slot with the element
        slot.getparent().replace(slot, node)

    def render(self, out_svg: Path, out_png: Path):
        """
        Render the template to SVG and PNG.
        """
        # Write the SVG to a file
        out_svg.write_bytes(etree.tostring(self._template, xml_declaration=True, encoding="UTF-8"))

        # Render the SVG to PNG (explicit fonts: slim containers lack DejaVu)
        png = resvg_py.svg_to_bytes(
            svg_path=str(out_svg),
            width=1080,
            height=1920,
            background="#ffffff",
            font_dirs=resvg_font_dirs(),
            font_family=self._font_family,
            sans_serif_family=self._font_family,
        )
        out_png.write_bytes(bytes(png))

    def _slot_bbox(self, el: etree._Element) -> tuple[float, float, float, float]:
        """
        Return (x, y, width, height) of a placeholder in user units.
        """
        slot_id = el.get("id", "?")
        if any(isinstance(child.tag, str) for child in el):
            raise RuntimeError(f"slot '{slot_id}' contains nested elements")

        # svgelements defaults omitted size attrs to 1; SVG uses 0. Force the spec
        # default so a shapeless placeholder is reported as having no dimensions.
        node = etree.fromstring(etree.tostring(el))
        tag = node.tag.rsplit("}", 1)[-1] if isinstance(node.tag, str) else ""
        if tag in ("rect", "image", "svg", "use"):
            if node.get("width") is None:
                node.set("width", "0")
            if node.get("height") is None:
                node.set("height", "0")
        elif tag == "circle" and node.get("r") is None:
            node.set("r", "0")
        elif tag == "ellipse":
            if node.get("rx") is None:
                node.set("rx", "0")
            if node.get("ry") is None:
                node.set("ry", "0")

        try:
            parsed = SVG.parse(BytesIO(b"<svg>" + etree.tostring(node) + b"</svg>"))
            bbox = parsed.bbox()
        except TypeError:
            bbox = None

        if bbox is None:
            raise RuntimeError(f"slot '{slot_id}' has no dimensions")
        xmin, ymin, xmax, ymax = bbox
        width, height = xmax - xmin, ymax - ymin
        if width <= 0 or height <= 0:
            raise RuntimeError(f"slot '{slot_id}' has no dimensions")
        return xmin, ymin, width, height
