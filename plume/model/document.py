"""Document → Pages → calques → éléments."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from .elements import Element, ImageItem, Shape, Stroke, new_id

A4 = (595.28, 841.89)  # points PDF
BACKGROUNDS = ("blank", "lined", "grid", "dots", "pdf")
# Ordre de rendu fixe : le surligneur passe toujours sous l'encre.
LAYERS = ("highlights", "images", "ink", "shapes")


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Page:
    width: float = A4[0]
    height: float = A4[1]
    background: dict = field(default_factory=lambda: {"kind": "blank"})
    highlights: list[Stroke] = field(default_factory=list)
    images: list[ImageItem] = field(default_factory=list)
    ink: list[Stroke] = field(default_factory=list)
    shapes: list[Shape] = field(default_factory=list)
    id: str = field(default_factory=new_id)

    @staticmethod
    def layer_for(element: Element) -> str:
        if isinstance(element, Stroke):
            return "highlights" if element.is_highlight else "ink"
        if isinstance(element, ImageItem):
            return "images"
        return "shapes"

    def layer(self, name: str) -> list:
        return getattr(self, name)

    def elements(self):
        """Tous les éléments, dans l'ordre de rendu."""
        for name in LAYERS:
            yield from self.layer(name)

    def add(self, element: Element, index: int | None = None) -> None:
        layer = self.layer(self.layer_for(element))
        layer.insert(len(layer) if index is None else index, element)

    def remove(self, element: Element) -> int:
        """Retire l'élément et renvoie son ancien indice dans son calque."""
        layer = self.layer(self.layer_for(element))
        index = next(i for i, e in enumerate(layer) if e.id == element.id)
        del layer[index]
        return index


@dataclass
class Document:
    pages: list[Page] = field(default_factory=lambda: [Page()])
    title: str = ""
    created: str = field(default_factory=now_iso)
    modified: str = field(default_factory=now_iso)
    source_pdf: bytes | None = None          # PDF importé, stocké dans l'archive
    assets: dict[str, bytes] = field(default_factory=dict)  # "assets/<sha1>.png" → contenu

    def page(self, page_id: str) -> Page:
        return next(p for p in self.pages if p.id == page_id)

    def page_index(self, page_id: str) -> int:
        return next(i for i, p in enumerate(self.pages) if p.id == page_id)
