import io
import matplotlib.pyplot as plt

from .element import *

class Figure(Element):

    def __init__(self, fig: plt.Figure, slot_id: str) -> None:
        self._fig = fig
        self._slot_id = slot_id

    @property
    def element(self) -> etree._Element:
        return self._fig_to_svg_root()

    @property
    def slot_id(self) -> str:
        return self._slot_id

    def _fig_to_svg_root(self) -> etree._Element:
        """
        Render a matplotlib figure to an <svg> element with all IDs namespaced.

        matplotlib generates internal IDs (clip paths, gradients). Two embedded
        figures can collide, so every id and reference is prefixed with `uid`.
        """
        # Save the figure to a buffer
        buf = io.BytesIO()
        self._fig.savefig(buf, format="svg")

        # Close the figure to free up memory
        plt.close(self._fig)

        # Parse the SVG string into an etree element
        root = etree.fromstring(buf.getvalue())

        # Namespace the ids
        self._namespace_ids(root)

        return root

    def _namespace_ids(self, root: etree._Element) -> None:
        """
        Namespace the IDs in the SVG element.
        """
        # Get the old IDs
        old_ids = {el.get("id") for el in root.iter() if el.get("id")}

        # Define a function to rename the IDs
        def rename(v: str) -> str:
            return f"{self._slot_id}__{v}"

        # Iterate over the elements in the SVG element
        for el in root.iter():
            if (v := el.get("id")) is not None:
                el.set("id", rename(v))
            # "{http://www.w3.org/1999/xlink}href" is ElementTree’s namespaced form of the SVG attribute xlink:href.
            # "href" is the modern SVG / plain attribute. Check for both here:
            for attr in ("href", "{http://www.w3.org/1999/xlink}href"):
                hv = el.get(attr)
                if hv and hv.startswith("#") and hv[1:] in old_ids:
                    el.set(attr, "#" + rename(hv[1:]))
            for attr, val in list(el.attrib.items()):
                if "url(#" in val:
                    for oid in old_ids:
                        val = val.replace(f"url(#{oid})", f"url(#{rename(oid)})")
                    el.set(attr, val)
