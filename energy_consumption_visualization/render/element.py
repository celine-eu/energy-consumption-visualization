import abc

from lxml import etree

class Element(abc.ABC):
    """Base class for all elements that can be rendered to an SVG."""

    @property
    @abc.abstractmethod
    def element(self) -> etree._Element:
        ...

    @property
    @abc.abstractmethod
    def slot_id(self) -> str:
        ...
