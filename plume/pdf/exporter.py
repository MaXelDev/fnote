"""Export PDF vectoriel.

- Pages issues d'un PDF : la page d'origine est recopiée telle quelle (texte sélectionnable).
- Encre : contour du trait à pression → polygone rempli (vectoriel, identique à l'écran).
- Surligneur : chemin translucide en mode de fusion « multiply », placé sous l'encre.
- Formes : chemins vectoriels. Images : insérées (recadrées/pivotées via Qt).
"""
from __future__ import annotations

import math
import re

import numpy as np
import pymupdf
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRect
from PySide6.QtGui import QImage, QTransform

from ..engine import geometry
from ..engine.pressure import PressureCurve
from ..model.elements import ImageItem, Shape, Stroke
from ..model.serialization import atomic_write
from ..view.render import MM, PAGE_STYLE

PRODUCER = "Plume"


def _rgb(hex_rgba: str) -> tuple[tuple[float, float, float], float]:
    h = hex_rgba.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    a = int(h[6:8], 16) / 255 if len(h) >= 8 else 1.0
    return (r, g, b), a


def _pt(x, y, m):
    p = pymupdf.Point(x, y)
    return p * m if m is not None else p


def _background(pg, page):
    kind = page.background.get("kind")
    shape = pg.new_shape()
    w, h = page.width, page.height
    if kind == "lined":
        y = PAGE_STYLE["top_mm"] * MM
        while y < h - 10 * MM:
            shape.draw_line((12 * MM, y), (w - 12 * MM, y))
            y += PAGE_STYLE["line_mm"] * MM
        shape.finish(color=_rgb(PAGE_STYLE["rule"])[0], width=0.4)
    elif kind == "grid":
        step = PAGE_STYLE["grid_mm"] * MM
        for x in np.arange(step, w, step):
            shape.draw_line((x, 0), (x, h))
        for y in np.arange(step, h, step):
            shape.draw_line((0, y), (w, y))
        shape.finish(color=_rgb(PAGE_STYLE["grid"])[0], width=0.3)
    elif kind == "dots":
        step = PAGE_STYLE["dot_mm"] * MM
        for y in np.arange(step, h, step):
            for x in np.arange(step, w, step):
                shape.draw_circle((x, y), 0.45)
        shape.finish(color=None, fill=_rgb(PAGE_STYLE["dot"])[0])
    shape.commit()


def _image_png(img: QImage, item: ImageItem) -> bytes:
    x0, y0, x1, y1 = item.crop
    part = img.copy(QRect(int(x0 * img.width()), int(y0 * img.height()),
                          max(1, int((x1 - x0) * img.width())), max(1, int((y1 - y0) * img.height()))))
    if item.rotation % 360:
        part = part.transformed(QTransform().rotate(item.rotation))
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    part.save(buf, "PNG")
    return bytes(data.data())


def _image_rect(item: ImageItem):
    x, y, w, h = item.rect
    cx, cy = x + w / 2, y + h / 2
    a = math.radians(item.rotation)
    bw = abs(w * math.cos(a)) + abs(h * math.sin(a))
    bh = abs(w * math.sin(a)) + abs(h * math.cos(a))
    return pymupdf.Rect(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)


def _shape_points(s: Shape):
    g = np.array(s.geometry, float)
    if s.kind == "ellipse":
        c = g.mean(axis=0)
        u, v = (g[1] - g[0]) / 2, (g[3] - g[0]) / 2
        a = np.linspace(0, 2 * math.pi, 73)
        return [c + np.cos(t) * u + np.sin(t) * v for t in a], []
    if s.kind in ("rect", "triangle"):
        return list(g) + [g[0]], []
    extra = []
    if s.kind == "arrow":
        (x0, y0), (x1, y1) = g[0], g[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        size = max(6.0, s.width * 5, 0.12 * math.dist(g[0], g[-1]))
        for da in (math.radians(150), -math.radians(150)):
            extra.append([(x1, y1), (x1 + size * math.cos(ang + da), y1 + size * math.sin(ang + da))])
    return list(g), extra


def _multiply_highlights(out: pymupdf.Document, pg) -> None:
    """Passe en « multiply » les états graphiques translucides (surligneur) de la page."""
    try:
        holder, prefix = pg.xref, "Resources/ExtGState"
        kind, value = out.xref_get_key(pg.xref, "Resources")
        if kind == "xref":  # ressources indirectes : on écrit dans leur objet
            holder, prefix = int(value.split()[0]), "ExtGState"
        kind, value = out.xref_get_key(holder, prefix)
        if kind == "xref":
            holder, prefix = int(value.split()[0]), ""
            value = out.xref_object(holder)
        # Entrées en ligne : /nom<</CA .55/ca 1>>
        for name, body in re.findall(r"/([^\s/<>]+)\s*<<([^>]*)>>", value):
            ca = re.search(r"/CA\s+([\d.]+)", body)
            if ca and float(ca.group(1)) < 1:
                out.xref_set_key(holder, f"{prefix}/{name}/BM".lstrip("/"), "/Multiply")
        # Entrées indirectes : /nom 12 0 R
        for _name, xref in re.findall(r"/([^\s/<>]+)\s+(\d+)\s+0\s+R", value):
            k, ca = out.xref_get_key(int(xref), "CA")
            if k != "null" and float(ca) < 1:
                out.xref_set_key(int(xref), "BM", "/Multiply")
    except Exception:  # cosmétique : sans multiply, le surlignage reste translucide et lisible
        pass


def export_document(doc, curve: PressureCurve, image_loader=None) -> bytes:
    """Renvoie le PDF exporté. image_loader(asset) -> QImage (par défaut : depuis doc.assets)."""
    image_loader = image_loader or (lambda name: QImage.fromData(doc.assets.get(name, b"")))
    out = pymupdf.open()
    src = pymupdf.open(stream=doc.source_pdf, filetype="pdf") if doc.source_pdf else None
    for page in doc.pages:
        bg = page.background
        if bg.get("kind") == "pdf" and src is not None and 0 <= bg.get("pdf_page", -1) < src.page_count:
            out.insert_pdf(src, from_page=bg["pdf_page"], to_page=bg["pdf_page"])
            pg = out[-1]
        else:
            pg = out.new_page(width=page.width, height=page.height)
            _background(pg, page)
        m = pg.derotation_matrix if pg.rotation else None

        shape = pg.new_shape()
        for s in page.highlights:
            rgb, a = _rgb(s.color)
            shape.draw_polyline([_pt(p[0], p[1], m) for p in s.points] if len(s.points) > 1
                                else [_pt(s.points[0][0], s.points[0][1], m)] * 2)
            shape.finish(color=rgb, width=s.width, stroke_opacity=a, closePath=False, lineCap=0, lineJoin=1)
        shape.commit()
        _multiply_highlights(out, pg)

        for item in page.images:
            img = image_loader(item.asset)
            if not img.isNull():
                pg.insert_image(_image_rect(item), stream=_image_png(img, item), keep_proportion=False)

        shape = pg.new_shape()
        for s in page.ink:
            rgb, a = _rgb(s.color)
            xy = np.array([(p[0], p[1]) for p in s.points], float)
            poly = geometry.outline(xy, geometry.widths(s.points, s.width, s.tool, curve))
            shape.draw_polyline([_pt(x, y, m) for x, y in poly])
            shape.finish(color=None, fill=rgb, fill_opacity=a, closePath=True)
        for s in page.shapes:
            rgb, a = _rgb(s.color)
            pts, extra = _shape_points(s)
            shape.draw_polyline([_pt(x, y, m) for x, y in pts])
            for seg in extra:
                shape.draw_polyline([_pt(x, y, m) for x, y in seg])
            shape.finish(color=rgb, width=s.width, stroke_opacity=a, closePath=False, lineCap=1, lineJoin=1)
        shape.commit()
    out.set_metadata({"producer": PRODUCER, "creator": PRODUCER, "title": doc.title or ""})
    return out.tobytes(garbage=3, deflate=True)


def export_to_file(doc, curve: PressureCurve, path) -> None:
    data = export_document(doc, curve)
    atomic_write(path, lambda fh: fh.write(data))


def is_plume_pdf(path) -> bool:
    """Le fichier est-il un PDF produit par Plume (donc remplaçable sans risque) ?"""
    try:
        with pymupdf.open(path) as d:
            return (d.metadata or {}).get("producer") == PRODUCER
    except Exception:
        return False
