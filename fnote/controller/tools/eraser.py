"""Gomme : trait entier ou partielle, option « surligneur seulement ».

Un geste de gomme = une seule étape d'annulation (groupe d'historique).
Le test se fait sur le segment parcouru entre deux échantillons : une gomme
rapide n'oublie aucun trait.
"""
from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPen

from ...engine import geometry
from ...model.elements import Shape, Stroke
from ...model.history import RemoveElements, ReplaceElements
from .base import Tool


def shape_polyline(s: Shape) -> np.ndarray:
    g = np.array(s.geometry, float)
    if s.kind == "ellipse":
        c = g.mean(axis=0)
        u, v = (g[1] - g[0]) / 2, (g[3] - g[0]) / 2
        a = np.linspace(0, 2 * math.pi, 48)
        return c + np.outer(np.cos(a), u) + np.outer(np.sin(a), v)
    if s.kind in ("rect", "triangle", "polygon"):
        return np.vstack([g, g[:1]])
    return g


def hits(page, a, b, radius: float, highlight_only: bool):
    """Éléments de la page touchés par le geste [a, b]."""
    layers = [page.highlights] if highlight_only else [page.highlights, page.ink, page.shapes]
    (ax, ay), (bx, by) = a, b
    found = []
    for layer in layers:
        for e in layer:
            x0, y0, x1, y1 = e.bounds()
            r = radius + e.width / 2
            if x1 < min(ax, bx) - r or x0 > max(ax, bx) + r or y1 < min(ay, by) - r or y0 > max(ay, by) + r:
                continue
            xy = shape_polyline(e) if isinstance(e, Shape) else np.array([(p[0], p[1]) for p in e.points])
            if geometry.polyline_hits_segment(xy, a, b, r):
                found.append(e)
    return found


class EraserTool(Tool):
    name = "eraser"
    dot_color = QColor("#7b8490")

    def __init__(self, canvas, spec: dict):
        super().__init__(canvas)
        self.spec = dict(spec)  # {"mode": "stroke"|"partial", "size": pt, "highlight_only": bool}
        self.page_index = -1
        self._last: tuple[float, float] | None = None
        self._pos: QPointF | None = None

    @property
    def busy(self) -> bool:
        return self._last is not None

    def press(self, pos, pressure, t):
        self.page_index, pt = self.canvas.view_to_page(pos)
        self._last = (pt.x(), pt.y())
        self.canvas.history.begin_group()
        self._erase(self._last, self._last)
        self.hover(pos)

    def move(self, pos, pressure, t):
        if self._last is None:
            return
        _, pt = self.canvas.view_to_page(pos, self.page_index)
        cur = (pt.x(), pt.y())
        self._erase(self._last, cur)
        self._last = cur
        self.hover(pos)

    def release(self, pos, pressure, t):
        if self._last is None:
            return
        self._last = None
        self.canvas.history.end_group()
        self.canvas.changed.emit()

    def cancel(self):
        if self._last is not None:
            self._last = None
            self.canvas.history.end_group()

    def _erase(self, a, b):
        page = self.canvas.doc.pages[self.page_index]
        radius = self.spec["size"] / 2
        touched = hits(page, a, b, radius, self.spec.get("highlight_only", False))
        if not touched:
            return
        if self.spec["mode"] == "stroke":
            self.canvas.apply(RemoveElements(page.id, touched), emit=False)
            return
        old, new = [], []
        for e in touched:
            old.append(e)
            if isinstance(e, Stroke):
                for piece in geometry.split_by_eraser(e.points, a, b, radius + e.width / 2):
                    new.append(Stroke(points=piece, color=e.color, width=e.width, tool=e.tool))
        self.canvas.apply(ReplaceElements(page.id, old, new), emit=False)

    def hover(self, pos):
        old = self._pos
        self._pos = None if pos is None else QPointF(pos)
        r = self.spec["size"] / 2 * self.canvas.zoom + 3
        for p in filter(None, (old, self._pos)):
            self.canvas.viewport().update(int(p.x() - r), int(p.y() - r), int(2 * r) + 1, int(2 * r) + 1)

    def paint_overlay(self, painter):
        if self._pos is None:
            return
        r = self.spec["size"] / 2 * self.canvas.zoom
        painter.setPen(QPen(QColor(0, 0, 0, 120), 1))
        painter.setBrush(QColor(255, 255, 255, 90))
        painter.drawEllipse(self._pos, r, r)
        painter.setBrush(Qt.BrushStyle.NoBrush)
