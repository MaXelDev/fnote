"""Rendu d'une page (fond + calques) avec QPainter, en coordonnées de page.

Utilisé par le canevas (caches bitmap), les miniatures et l'aperçu. Le contour de
chaque trait est calculé une fois puis mémorisé sur l'objet (attribut `_qpath`).
"""
from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF, QTransform

from ..engine import geometry
from ..engine.pressure import PressureCurve
from ..model.document import Page
from ..model.elements import ImageItem, Shape, Stroke

MM = 72 / 25.4  # points par millimètre
PAGE_STYLE = {"line_mm": 8.0, "grid_mm": 5.0, "dot_mm": 5.0, "top_mm": 25.0,
              "rule": "#c9d3df", "grid": "#dfe5ec", "dot": "#b7c2cf"}


def qcolor(rgba: str) -> QColor:
    """« #rrggbbaa » → QColor."""
    c = QColor(rgba[:7])
    c.setAlpha(int(rgba[7:9], 16) if len(rgba) >= 9 else 255)
    return c


def _polygon(arr: np.ndarray) -> QPolygonF:
    return QPolygonF([QPointF(float(x), float(y)) for x, y in arr])


def stroke_path(stroke: Stroke, curve: PressureCurve, curve_key) -> QPainterPath:
    """Chemin rempli du trait (encre) ou chemin à tracer (surligneur), mis en cache."""
    cached = stroke.__dict__.get("_qpath")
    if cached and cached[0] == curve_key:
        return cached[1]
    path = QPainterPath()
    if stroke.is_highlight:
        pts = stroke.points
        path.moveTo(pts[0][0], pts[0][1])
        for x, y, *_ in pts[1:]:
            path.lineTo(x, y)
        if len(pts) == 1:
            path.lineTo(pts[0][0] + 0.01, pts[0][1])
    else:
        xy = np.array([(p[0], p[1]) for p in stroke.points], float)
        w = geometry.widths(stroke.points, stroke.width, stroke.tool, curve)
        path.addPolygon(_polygon(geometry.outline(xy, w)))
        path.closeSubpath()
        path.setFillRule(Qt.FillRule.WindingFill)
    stroke.__dict__["_qpath"] = (curve_key, path)
    return path


def shape_path(shape: Shape) -> QPainterPath:
    g = shape.geometry
    path = QPainterPath()
    if shape.kind == "ellipse":
        # geometry = 4 coins du rectangle englobant (éventuellement pivoté)
        c = np.mean(np.array(g, float), axis=0)
        (x0, y0), (x1, y1) = g[0], g[1]
        rx, ry = math.dist(g[0], g[1]) / 2, math.dist(g[0], g[3]) / 2
        angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
        local = QPainterPath()
        local.addEllipse(QPointF(0, 0), rx, ry)
        return QTransform().translate(c[0], c[1]).rotate(angle).map(local)
    path.moveTo(*g[0])
    for p in g[1:]:
        path.lineTo(*p)
    if shape.kind in ("rect", "triangle"):
        path.closeSubpath()
    if shape.kind == "arrow" and len(g) >= 2:
        (x0, y0), (x1, y1) = g[0], g[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        size = max(6.0, shape.width * 5, 0.12 * math.dist(g[0], g[-1]))
        for da in (math.radians(150), -math.radians(150)):
            path.moveTo(x1, y1)
            path.lineTo(x1 + size * math.cos(ang + da), y1 + size * math.sin(ang + da))
    return path


class PageRenderer:
    """Peint des pages. pdf_source (optionnel) : objet avec render(n, scale) -> QImage."""

    def __init__(self, doc, curve: PressureCurve, pdf_source=None):
        self.doc, self.pdf_source = doc, pdf_source
        self.set_curve(curve)
        self._images: dict[str, QImage] = {}

    def set_curve(self, curve: PressureCurve) -> None:
        self.curve = curve
        self.curve_key = (tuple(curve.x), tuple(curve.y))

    def image(self, asset: str) -> QImage:
        img = self._images.get(asset)
        if img is None:
            img = QImage.fromData(self.doc.assets.get(asset, b""))
            self._images[asset] = img
        return img

    # ----- fond -----
    def paint_background(self, p: QPainter, page: Page, scale: float) -> None:
        rect = QRectF(0, 0, page.width, page.height)
        p.fillRect(rect, QColor("#ffffff"))
        bg = page.background
        kind = bg.get("kind", "blank")
        if kind == "pdf" and self.pdf_source is not None:
            img = self.pdf_source.render(bg["pdf_page"], scale)
            if img is not None and not img.isNull():
                p.drawImage(rect, img)
            return
        hair = 1.0 / max(scale, 0.01)  # ~1 pixel quel que soit le zoom
        if kind == "lined":
            p.setPen(QPen(QColor(PAGE_STYLE["rule"]), hair))
            y = PAGE_STYLE["top_mm"] * MM
            while y < page.height - 10 * MM:
                p.drawLine(QPointF(12 * MM, y), QPointF(page.width - 12 * MM, y))
                y += PAGE_STYLE["line_mm"] * MM
        elif kind == "grid":
            step = PAGE_STYLE["grid_mm"] * MM
            p.setPen(QPen(QColor(PAGE_STYLE["grid"]), hair))
            x = step
            while x < page.width:
                p.drawLine(QPointF(x, 0), QPointF(x, page.height))
                x += step
            y = step
            while y < page.height:
                p.drawLine(QPointF(0, y), QPointF(page.width, y))
                y += step
        elif kind == "dots":
            step = PAGE_STYLE["dot_mm"] * MM
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(PAGE_STYLE["dot"]))
            r = max(0.45, 1.2 / max(scale, 0.01))
            y = step
            while y < page.height:
                x = step
                while x < page.width:
                    p.drawEllipse(QPointF(x, y), r, r)
                    x += step
                y += step

    # ----- éléments -----
    def paint_highlight(self, p: QPainter, s: Stroke) -> None:
        p.save()
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        pen = QPen(qcolor(s.color), s.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap,
                   Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(stroke_path(s, self.curve, self.curve_key))  # un seul chemin : opacité uniforme
        p.restore()

    def paint_ink(self, p: QPainter, s: Stroke) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(qcolor(s.color))
        p.drawPath(stroke_path(s, self.curve, self.curve_key))

    def paint_shape(self, p: QPainter, s: Shape) -> None:
        p.setPen(QPen(qcolor(s.color), s.width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(shape_path(s))

    def paint_image(self, p: QPainter, item: ImageItem) -> None:
        img = self.image(item.asset)
        if img.isNull():
            return
        x, y, w, h = item.rect
        cx0, cy0, cx1, cy1 = item.crop
        src = QRectF(cx0 * img.width(), cy0 * img.height(), (cx1 - cx0) * img.width(), (cy1 - cy0) * img.height())
        p.save()
        p.translate(x + w / 2, y + h / 2)
        p.rotate(item.rotation)
        p.drawImage(QRectF(-w / 2, -h / 2, w, h), img, src)
        p.restore()

    def paint_element(self, p: QPainter, e) -> None:
        if isinstance(e, Stroke):
            (self.paint_highlight if e.is_highlight else self.paint_ink)(p, e)
        elif isinstance(e, Shape):
            self.paint_shape(p, e)
        else:
            self.paint_image(p, e)

    def paint_page(self, p: QPainter, page: Page, scale: float, background: bool = True, exclude=()) -> None:
        """Peint la page entière ; le painter doit déjà être en coordonnées de page."""
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if background:
            self.paint_background(p, page, scale)
        for e in page.elements():
            if e.id not in exclude:
                self.paint_element(p, e)

    def render_page(self, page: Page, scale: float, dpr: float = 1.0, exclude=()) -> QImage:
        """Image de la page à `scale` pixels logiques par point (cache du canevas)."""
        w, h = max(1, round(page.width * scale * dpr)), max(1, round(page.height * scale * dpr))
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.setDevicePixelRatio(dpr)
        p = QPainter(img)
        p.scale(scale, scale)
        self.paint_page(p, page, scale, exclude=exclude)
        p.end()
        return img
