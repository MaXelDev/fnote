"""Éléments d'une page : traits, formes, images. Coordonnées en points PDF (1/72 pouce)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

TOOLS = ("fountain", "ballpoint", "pencil", "highlighter")
SHAPE_KINDS = ("line", "rect", "ellipse", "triangle", "arrow")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _bounds(xs, ys, pad: float) -> tuple[float, float, float, float]:
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


@dataclass
class Stroke:
    """Trait à main levée. points = [(x, y, pression 0..1, t en ms), ...]."""
    points: list[tuple[float, float, float, float]]
    color: str = "#1a1a1aff"
    width: float = 1.6
    tool: str = "fountain"
    id: str = field(default_factory=new_id)

    @property
    def is_highlight(self) -> bool:
        return self.tool == "highlighter"

    def bounds(self):
        return _bounds([p[0] for p in self.points], [p[1] for p in self.points], self.width / 2)


@dataclass
class Shape:
    """Forme parfaite (issue de la reconnaissance). geometry = sommets [(x, y), ...]."""
    kind: str
    geometry: list[tuple[float, float]]
    color: str = "#1a1a1aff"
    width: float = 1.6
    rotation: float = 0.0
    id: str = field(default_factory=new_id)

    def bounds(self):
        return _bounds([p[0] for p in self.geometry], [p[1] for p in self.geometry], self.width / 2)


@dataclass
class ImageItem:
    """Image insérée. asset = chemin dans l'archive ; rect = (x, y, largeur, hauteur)."""
    asset: str
    rect: tuple[float, float, float, float]
    rotation: float = 0.0
    crop: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    id: str = field(default_factory=new_id)

    def bounds(self):
        x, y, w, h = self.rect
        return (x, y, x + w, y + h)


Element = Stroke | Shape | ImageItem
