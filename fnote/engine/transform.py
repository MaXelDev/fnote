"""Transformations affines des éléments (lasso) et sélection par contour.

Matrices 3×3 NumPy en coordonnées de page. Les éléments transformés sont de
nouveaux objets avec le même identifiant (l'historique les échange).
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from ..model.elements import ImageItem, Shape, Stroke, new_id
from .geometry import point_in_polygon


def translate(dx: float, dy: float) -> np.ndarray:
    return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]], float)


def scale_about(cx: float, cy: float, sx: float, sy: float) -> np.ndarray:
    return translate(cx, cy) @ np.diag([sx, sy, 1.0]) @ translate(-cx, -cy)


def rotate_about(cx: float, cy: float, degrees: float) -> np.ndarray:
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return translate(cx, cy) @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]) @ translate(-cx, -cy)


def _apply(m: np.ndarray, xy) -> np.ndarray:
    xy = np.asarray(xy, float)
    return xy @ m[:2, :2].T + m[:2, 2]


def _linear_scale(m: np.ndarray) -> float:
    return math.sqrt(abs(np.linalg.det(m[:2, :2])))


def transform_element(e, m: np.ndarray):
    k = _linear_scale(m)
    if isinstance(e, Stroke):
        xy = _apply(m, [(p[0], p[1]) for p in e.points])
        pts = [(float(x), float(y), p[2], p[3]) for (x, y), p in zip(xy, e.points)]
        return replace(e, points=pts, width=e.width * k)
    if isinstance(e, Shape):
        return replace(e, geometry=[tuple(map(float, p)) for p in _apply(m, e.geometry)], width=e.width * k)
    x, y, w, h = e.rect
    cx, cy = _apply(m, [(x + w / 2, y + h / 2)])[0]
    sx, sy = np.linalg.norm(m[:2, 0]), np.linalg.norm(m[:2, 1])
    angle = math.degrees(math.atan2(m[1, 0], m[0, 0]))
    nw, nh = w * sx, h * sy
    return replace(e, rect=(float(cx - nw / 2), float(cy - nh / 2), float(nw), float(nh)),
                   rotation=(e.rotation + angle) % 360)


def with_new_id(e, dx: float = 0.0, dy: float = 0.0):
    """Copie (coller, dupliquer) avec un nouvel identifiant, éventuellement décalée."""
    moved = transform_element(e, translate(dx, dy)) if (dx or dy) else replace(e)
    return replace(moved, id=new_id())


def element_points(e) -> np.ndarray:
    if isinstance(e, Stroke):
        return np.array([(p[0], p[1]) for p in e.points], float)
    if isinstance(e, Shape):
        return np.array(e.geometry, float)
    x, y, w, h = e.rect
    return np.array([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x + w / 2, y + h / 2)], float)


def select_in_lasso(page, polygon, threshold: float = 0.5) -> list:
    """Éléments dont au moins `threshold` des points sont dans le contour du lasso."""
    poly = np.asarray(polygon, float)
    if len(poly) < 3:
        return []
    out = []
    for e in page.elements():
        pts = element_points(e)
        if len(pts) and point_in_polygon(pts, poly).mean() >= threshold:
            out.append(e)
    return out


def bounds(elements) -> tuple[float, float, float, float]:
    boxes = np.array([e.bounds() for e in elements], float)
    return (float(boxes[:, 0].min()), float(boxes[:, 1].min()), float(boxes[:, 2].max()), float(boxes[:, 3].max()))
