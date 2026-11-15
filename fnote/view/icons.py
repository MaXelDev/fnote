"""Icônes dessinées en vectoriel (originales, sans fichier ni licence tierce).

Chaque icône est tracée sur une grille 24×24 avec la couleur de texte du thème.
"""
from __future__ import annotations

from functools import cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from . import style


def _pen(p: QPainter, color: QColor, w: float = 1.8):
    p.setPen(QPen(color, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)


def _draw(name: str, p: QPainter, c: QColor):
    _pen(p, c)
    if name == "pen":
        p.translate(12, 12)
        p.rotate(45)
        p.drawRoundedRect(QRectF(-3, -10, 6, 15), 1.5, 1.5)
        path = QPainterPath(QPointF(-3, 5))
        path.lineTo(0, 10)
        path.lineTo(3, 5)
        p.drawPath(path)
    elif name == "highlighter":
        p.translate(12, 12)
        p.rotate(45)
        p.drawRoundedRect(QRectF(-4, -10, 8, 12), 1.5, 1.5)
        path = QPainterPath(QPointF(-4, 2))
        path.lineTo(-2, 7)
        path.lineTo(2, 9)
        path.lineTo(4, 2)
        p.drawPath(path)
        p.resetTransform()
        _pen(p, c, 2.2)
        p.drawLine(QPointF(4, 21), QPointF(20, 21))
    elif name == "eraser":
        p.translate(12, 12)
        p.rotate(-35)
        p.drawRoundedRect(QRectF(-8, -4.5, 16, 9), 2, 2)
        p.drawLine(QPointF(0, -4.5), QPointF(0, 4.5))
        p.resetTransform()
        p.drawLine(QPointF(9, 20.5), QPointF(20, 20.5))
    elif name == "lasso":
        p.setPen(QPen(c, 1.8, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(QRectF(3, 3, 18, 12))
        _pen(p, c)
        path = QPainterPath(QPointF(8, 14.5))
        path.cubicTo(5, 18, 9, 21, 11, 18)
        p.drawPath(path)
    elif name == "ruler":
        p.translate(12, 12)
        p.rotate(-30)
        p.drawRect(QRectF(-10, -4, 20, 8))
        for i, x in enumerate(range(-7, 9, 3)):
            p.drawLine(QPointF(x, -4), QPointF(x, -1 if i % 2 else 0.5))
    elif name == "image":
        p.drawRoundedRect(QRectF(3, 5, 18, 14), 2, 2)
        path = QPainterPath(QPointF(5, 17))
        path.lineTo(10, 11)
        path.lineTo(14, 15)
        path.lineTo(16, 13)
        path.lineTo(19, 17)
        p.drawPath(path)
        p.drawEllipse(QPointF(16, 9), 1.5, 1.5)
    elif name in ("undo", "redo"):
        if name == "redo":
            p.translate(24, 0)
            p.scale(-1, 1)
        path = QPainterPath(QPointF(8, 6))
        path.lineTo(4, 10)
        path.lineTo(8, 14)
        p.drawPath(path)
        arc = QPainterPath(QPointF(4, 10))
        arc.lineTo(14, 10)
        arc.cubicTo(22, 10, 22, 20, 14, 20)
        arc.lineTo(9, 20)
        p.drawPath(arc)
    elif name == "pages":
        p.drawRoundedRect(QRectF(7, 3, 12, 15), 1.5, 1.5)
        p.drawPolyline([QPointF(5, 7), QPointF(5, 21), QPointF(15, 21)])
    elif name == "fit":
        p.drawLine(QPointF(3, 5), QPointF(3, 19))
        p.drawLine(QPointF(21, 5), QPointF(21, 19))
        p.drawLine(QPointF(7, 12), QPointF(17, 12))
        p.drawPolyline([QPointF(10, 9), QPointF(7, 12), QPointF(10, 15)])
        p.drawPolyline([QPointF(14, 9), QPointF(17, 12), QPointF(14, 15)])
    elif name == "shapes":
        p.drawEllipse(QRectF(3, 3, 11, 11))
        p.drawRect(QRectF(10, 10, 11, 11))
    elif name == "plus":
        p.drawLine(QPointF(12, 5), QPointF(12, 19))
        p.drawLine(QPointF(5, 12), QPointF(19, 12))
    elif name == "menu":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        for y in (6, 12, 18):
            p.drawEllipse(QPointF(12, y), 1.7, 1.7)
    elif name == "folder":
        path = QPainterPath(QPointF(3, 7))
        path.lineTo(9, 7)
        path.lineTo(11, 9)
        path.lineTo(21, 9)
        path.lineTo(21, 19)
        path.lineTo(3, 19)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "note":
        p.drawRoundedRect(QRectF(5, 3, 14, 18), 2, 2)
        path = QPainterPath(QPointF(8, 14))
        path.cubicTo(10, 9, 12, 17, 16, 11)
        p.drawPath(path)
    elif name == "pdf":
        p.drawRoundedRect(QRectF(5, 3, 14, 18), 2, 2)
        for y in (8, 12, 16):
            p.drawLine(QPointF(8, y), QPointF(16, y))
    elif name == "sidebar":
        p.drawRoundedRect(QRectF(3, 4, 18, 16), 2, 2)
        p.drawLine(QPointF(9, 4), QPointF(9, 20))


@cache
def _icon(name: str, color: str) -> QIcon:
    icon = QIcon()
    for scale in (1, 2):
        pm = QPixmap(24 * scale, 24 * scale)
        pm.setDevicePixelRatio(scale)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        _draw(name, p, QColor(color))
        p.end()
        icon.addPixmap(pm)
    return icon


def icon(name: str) -> QIcon:
    return _icon(name, style.colors()["text"])
