import matplotlib
matplotlib.use("Agg")  # headless / no display needed

from .figure import Figure # noqa: F401
from .table import Table # noqa: F401
from .template import Template # noqa: F401
from .title import Title # noqa: F401

__all__ = ["Figure", "Table", "Template", "Title"]
