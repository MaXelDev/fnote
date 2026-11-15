"""Règle virtuelle : posée sur l'écran (elle ne défile pas), graduée en cm à l'échelle de la page.

Déplacer : glisser le corps (stylet, souris ou un doigt). Pivoter : poignée ronde, ou deux
doigts. Aimantation aux angles 0/15/30/45/90°. Un trait commencé près d'un bord s'y colle.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from ..engine.ruler_geometry import RulerGeometry, normalize_deg, snap_angle

MM_PER_PT = 25.4 / 72
KNOB_R = 14.0


class Ruler:
    dot_color = None

    def __init__(self, canvas):
        self.canvas = canvas
        vp = canvas.viewport()
        self.geom = RulerGeometry(vp.width() / 2, vp.height() / 2, 0.0,
                                  length=max(420.0, min(vp.width() * 0.8, 1000.0)), thickness=78.0)
        self.visible = False
        self._drag = None
        self._raw_angle = 0.0

    # ----- état -----
    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            vp = self.canvas.viewport()
            self.geom.cx, self.geom.cy = vp.width() / 2, vp.height() * 0.45
        self.canvas.viewport().update()

    def _knob(self) -> QPointF:
        return QPointF(*self.geom.to_screen(self.geom.length / 2 - 30, 0))

    def wants(self, pos: QPointF) -> bool:
        """La pression revient-elle à la règle (déplacer/pivoter) plutôt qu'à l'outil ?"""
        if not self.visible:
            return False
        k = self._knob()
        if math.hypot(pos.x() - k.x(), pos.y() - k.y()) <= KNOB_R + 6:
            return True
        return self.geom.contains(pos.x(), pos.y()) and self.geom.edge_near(pos.x(), pos.y()) is None

    # ----- geste (même interface qu'un outil) -----
    def press(self, pos, pressure=0.5, t=0.0):
        k = self._knob()
        if math.hypot(pos.x() - k.x(), pos.y() - k.y()) <= KNOB_R + 6:
            self._drag = ("rotate", None)
            self._raw_angle = self.geom.angle
        else:
            self._drag = ("move", QPointF(pos))

    def move(self, pos, pressure=0.5, t=0.0):
        if self._drag is None:
            return
        kind, last = self._drag
        if kind == "move":
            d = pos - last
            self.translate(d.x(), d.y())
            self._drag = ("move", QPointF(pos))
        else:
            deg = math.degrees(math.atan2(pos.y() - self.geom.cy, pos.x() - self.geom.cx))
            self.geom.angle = snap_angle(deg)
        self.canvas.viewport().update()

    def release(self, pos, pressure=0.5, t=0.0):
        self._drag = None

    def cancel(self):
        self._drag = None

    def paint_overlay(self, p):
        self.paint(p)

    # ----- deux doigts -----
    def translate(self, dx: float, dy: float):
        self.geom.cx += dx
        self.geom.cy += dy

    def begin_rotate(self):
        self._raw_angle = self.geom.angle

    def rotate_by(self, delta_deg: float):
        self._raw_angle += delta_deg
        self.geom.angle = snap_angle(self._raw_angle)
        self.canvas.viewport().update()

    # ----- dessin -----
    def paint(self, p: QPainter):
        if not self.visible:
            return
        g = self.geom
        L, T = g.length, g.thickness
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(g.cx, g.cy)
        p.rotate(g.angle)
        body = QRectF(-L / 2, -T / 2, L, T)
        p.setPen(QPen(QColor(38, 104, 108, 200), 1.2))
        p.setBrush(QColor(252, 252, 248, 215))
        p.drawRoundedRect(body, 6, 6)
        # graduations : 1 mm de page = zoom * 72 / 25,4 pixels
        mm_px = self.canvas.zoom / MM_PER_PT
        p.setPen(QPen(QColor(30, 30, 30, 200), 1))
        font = QFont()
        font.setPixelSize(10)
        p.setFont(font)
        step = 1 if mm_px >= 4 else (5 if mm_px >= 1 else 10)
        n = int(L / mm_px)
        for k in range(0, n + 1, step):
            x = -L / 2 + 12 + k * mm_px
            if x > L / 2 - 12:
                break
            h = 14 if k % 10 == 0 else (9 if k % 5 == 0 else 5)
            p.drawLine(QPointF(x, -T / 2), QPointF(x, -T / 2 + h))
            p.drawLine(QPointF(x, T / 2), QPointF(x, T / 2 - h))
            if k % 10 == 0 and mm_px * 10 >= 18:
                p.drawText(QRectF(x - 12, -T / 2 + 14, 24, 14), Qt.AlignmentFlag.AlignCenter, str(k // 10))
        # angle au centre
        font.setPixelSize(13)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(38, 104, 108))
        p.drawText(QRectF(-40, -9, 80, 18), Qt.AlignmentFlag.AlignCenter, f"{normalize_deg(g.angle):.0f}°")
        # poignée de rotation
        p.setBrush(QColor(38, 104, 108, 230))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(L / 2 - 30, 0), KNOB_R, KNOB_R)
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawArc(QRectF(L / 2 - 30 - 7, -7, 14, 14), 30 * 16, 280 * 16)
        p.restore()
