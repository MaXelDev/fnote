"""Stylo (plume, bille, crayon) et surligneur.

Pendant le tracé, seul le dernier segment est peint dans l'overlay du canevas et
seul son rectangle est rafraîchi. Au lever, le trait est lissé, enregistré (undo)
et « cuit » dans le cache de la page.

Formes auto-corrigées : si le stylet reste immobile ~0,5 s en fin de trait, le trait
est remplacé par la forme reconnue (même couleur, même épaisseur).
Règle : un trait commencé près d'un bord de la règle est collé à ce bord.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QPainterPath, QPen, QTransform

from ...engine.shape_recognition import recognize
from ...engine.smoothing import StreamSmoother, finalize
from ...model.elements import Shape, Stroke
from ...view.render import qcolor, shape_path
from .base import Tool

HOLD_MS = 500
HOLD_TOLERANCE_PX = 6.0  # tremblement toléré pendant le maintien (le S Pen bouge de quelques px)


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
        self._ruler_side = None
        self._shape: Shape | None = None
        self._anchor = QPointF()
        self._hold = QTimer(singleShot=True, interval=HOLD_MS, timeout=self._on_hold)

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
        elif self.spec["tool"] == "pencil":
            w *= 0.6 + 0.4 * float(self.canvas.curve(pressure))
        return max(w * self.canvas.zoom, 0.6)

    # ----- geste -----
    def press(self, pos, pressure, t):
        self.page_index, pt = self.canvas.view_to_page(pos)
        self._smoother = StreamSmoother()
        self._t0 = t
        self.points = []
        self._shape = None
        ruler = getattr(self.canvas, "ruler", None)
        self._ruler_side = ruler.geom.edge_near(pos.x(), pos.y()) if ruler is not None and ruler.visible else None
        self._anchor = QPointF(pos)
        if self._shapes_enabled():
            self._hold.start()
        self.canvas.begin_live()
        self._add(pos, pressure, t)

    def move(self, pos, pressure, t):
        if self._smoother is None or self._shape is not None:
            return
        if math.hypot(pos.x() - self._anchor.x(), pos.y() - self._anchor.y()) > HOLD_TOLERANCE_PX:
            self._anchor = QPointF(pos)
            if self._shapes_enabled():
                self._hold.start()  # le stylet bouge encore : on relance l'attente
        self._add(pos, pressure, t)

    def _shapes_enabled(self) -> bool:
        return self.canvas.config.shape_recognition and not self.is_highlighter and self._ruler_side is None

    def _add(self, view_pos: QPointF, pressure: float, t: float):
        if self._ruler_side is not None:
            g = self.canvas.ruler.geom
            offset = self.spec["width"] * self.canvas.zoom / 2
            view_pos = QPointF(*g.project(view_pos.x(), view_pos.y(), self._ruler_side, offset))
        _, pt = self.canvas.view_to_page(view_pos, self.page_index)
        raw = (pt.x(), pt.y(), max(0.0, min(1.0, pressure)), t - self._t0)
        p = self._smoother.add(raw) if self._ruler_side is None else raw  # collé à la règle : pas de lissage
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

    def _page_to_view_transform(self) -> QTransform:
        r = self.canvas.page_rect(self.page_index)
        z = self.canvas.zoom
        return QTransform(z, 0, 0, z, r.x(), r.y())

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

    def _on_hold(self):
        """Stylet immobile : on tente de remplacer le trait par une forme parfaite."""
        if self._smoother is None or len(self.points) < 6:
            return
        found = recognize(self.points)
        if found is None:
            return
        kind, geometry = found
        self._shape = Shape(kind=kind, geometry=geometry, color=self.spec["color"], width=self.spec["width"])
        c = self.canvas
        painter = c.live_painter(clear=True)
        painter.setPen(QPen(qcolor(self.spec["color"]), self.spec["width"] * c.zoom, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(self._page_to_view_transform().map(shape_path(self._shape)))
        painter.end()
        c.viewport().update()

    def release(self, pos, pressure, t):
        if self._smoother is None:
            return
        self._hold.stop()
        last_raw = self._smoother._raw[-1] if self._smoother._raw else None
        self._smoother = None
        if last_raw is not None and self._ruler_side is None and self.points[-1][:2] != last_raw[:2]:
            self.points.append(last_raw)  # le trait finit exactement là où le stylet s'est levé
        if self._shape is not None:
            shape, self._shape = self._shape, None
            self.points = []
            self.canvas.commit_elements(self.page_index, [shape])
            return
        points = finalize(self.points) if self._ruler_side is None else self.points
        if self.is_highlighter and self.canvas.config.straight_highlighter and len(points) > 1 \
                and self._ruler_side is None:
            points = straighten(points)
        stroke = Stroke(points=points, color=self.spec["color"], width=self.spec["width"], tool=self.spec["tool"])
        self.points = []
        self.canvas.commit_elements(self.page_index, [stroke])

    def cancel(self):
        self._hold.stop()
        self._smoother = None
        self._shape = None
        self.points = []
        self.canvas.end_live()

    def dispose(self):
        self._hold.stop()


def straighten(points):
    """Surligneur droit : ligne horizontale à la hauteur moyenne, de l'extrémité gauche à la droite."""
    xs = [p[0] for p in points]
    y = sum(p[1] for p in points) / len(points)
    p0, p1 = points[0], points[-1]
    return [(min(xs), y, p0[2], p0[3]), (max(xs), y, p1[2], p1[3])]
