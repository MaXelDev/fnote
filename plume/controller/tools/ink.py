"""Stylo (plume, bille, crayon) et surligneur.

Pendant le tracé, seul le dernier segment est peint dans l'overlay du canevas et
seul son rectangle est rafraîchi. Au lever, le trait est lissé, enregistré
(undo) et « cuit » dans le cache de la page.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainterPath, QPen

from ...engine.smoothing import StreamSmoother, finalize
from ...model.elements import Stroke
from ...view.render import qcolor
from .base import Tool


class InkTool(Tool):
    def __init__(self, canvas, spec: dict):
        super().__init__(canvas)
        self.spec = dict(spec)  # {"tool": ..., "color": "#rrggbbaa", "width": pt}
        self.name = self.spec["tool"]
        self.dot_color = qcolor(self.spec["color"])
        self.points: list[tuple] = []
        self.page_index = -1
        self._smoother: StreamSmoother | None = None
        self._t0 = 0.0
        self.on_point = None  # crochet (formes auto, règle) : f(tool, point_page) -> point_page

    @property
    def is_highlighter(self) -> bool:
        return self.spec["tool"] == "highlighter"

    @property
    def busy(self) -> bool:
        return self._smoother is not None

    def _width_px(self, pressure: float) -> float:
        w = self.spec["width"]
        if self.spec["tool"] == "fountain":
            w *= float(self.canvas.curve(pressure))
        return max(w * self.canvas.zoom, 0.6)

    # ----- geste -----
    def press(self, pos, pressure, t):
        self.page_index, pt = self.canvas.view_to_page(pos)
        self._smoother = StreamSmoother()
        self._t0 = t
        self.points = []
        self.canvas.begin_live()
        self._add(pt, pressure, t)

    def move(self, pos, pressure, t):
        if self._smoother is None:
            return
        _, pt = self.canvas.view_to_page(pos, self.page_index)
        self._add(pt, pressure, t)

    def _add(self, pt: QPointF, pressure: float, t: float):
        if self.on_point is not None:
            pt = self.on_point(self, pt)
        raw = (pt.x(), pt.y(), max(0.0, min(1.0, pressure)), t - self._t0)
        p = self._smoother.add(raw)
        self.points.append(p)
        if self.is_highlighter:
            self._paint_highlight_preview()
        else:
            self._paint_segment()

    def _paint_segment(self):
        c = self.canvas
        a = self.points[-2] if len(self.points) > 1 else self.points[-1]
        b = self.points[-1]
        va, vb = c.page_to_view(self.page_index, a[0], a[1]), c.page_to_view(self.page_index, b[0], b[1])
        width = self._width_px(b[2])
        painter = c.live_painter()
        painter.setPen(QPen(qcolor(self.spec["color"]), width, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(va, vb)
        painter.end()
        pad = width + 2
        c.viewport().update(QRectF(va, vb).normalized().adjusted(-pad, -pad, pad, pad).toAlignedRect())

    def _paint_highlight_preview(self):
        # Le chemin entier est repeint d'un bloc : pas d'accumulation d'opacité.
        c = self.canvas
        path = QPainterPath()
        for i, p in enumerate(self.points):
            v = c.page_to_view(self.page_index, p[0], p[1])
            path.moveTo(v) if i == 0 else path.lineTo(v)
        if len(self.points) == 1:
            path.lineTo(path.currentPosition() + QPointF(0.01, 0))
        painter = c.live_painter(clear=True)
        painter.setPen(QPen(qcolor(self.spec["color"]), self.spec["width"] * c.zoom, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.FlatCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
        painter.end()
        pad = self.spec["width"] * c.zoom + 2
        c.viewport().update(path.boundingRect().adjusted(-pad, -pad, pad, pad).toAlignedRect())

    def release(self, pos, pressure, t):
        if self._smoother is None:
            return
        self._smoother = None
        points = finalize(self.points)
        if self.is_highlighter and self.canvas.config.straight_highlighter and len(points) > 1:
            points = straighten(points)
        stroke = Stroke(points=points, color=self.spec["color"], width=self.spec["width"], tool=self.spec["tool"])
        self.points = []
        self.canvas.commit_elements(self.page_index, [stroke])

    def cancel(self):
        self._smoother = None
        self.points = []
        self.canvas.end_live()


def straighten(points):
    """Surligneur droit : ligne horizontale à la hauteur moyenne, de l'extrémité gauche à la droite."""
    xs = [p[0] for p in points]
    y = sum(p[1] for p in points) / len(points)
    p0, p1 = points[0], points[-1]
    return [(min(xs), y, p0[2], p0[3]), (max(xs), y, p1[2], p1[3])]
