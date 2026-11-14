"""Géométrie des traits : épaisseurs, contour d'un trait à pression, tests d'intersection.

Le contour (polygone) sert à la fois au rendu à l'écran et à l'export PDF vectoriel.
Toutes les coordonnées sont en points de page.
"""
from __future__ import annotations

import math

import numpy as np

from .pressure import PressureCurve

CAP_STEPS = 8


def widths(points, base_width: float, tool: str, curve: PressureCurve) -> np.ndarray:
    """Épaisseur en chaque point selon l'outil."""
    p = np.array([pt[2] for pt in points], dtype=float)
    if tool == "fountain":
        return base_width * curve(p)
    return np.full(len(points), float(base_width))  # bille, crayon, surligneur : constante


def _cap(center, normal, radius, start: bool) -> np.ndarray:
    """Demi-cercle d'extrémité, de +normal vers -normal en passant par l'arrière/avant."""
    base = math.atan2(normal[1], normal[0])
    sign = 1.0 if start else -1.0
    angles = base + sign * np.linspace(0, math.pi, CAP_STEPS + 2)[1:-1]
    return center + radius * np.column_stack([np.cos(angles), np.sin(angles)])


def outline(xy: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Polygone fermé entourant un trait d'épaisseur variable (à remplir en WindingFill)."""
    xy = np.asarray(xy, dtype=float)
    w = np.maximum(np.asarray(w, dtype=float), 0.05)
    if len(xy) == 1 or np.allclose(xy, xy[0]):
        r = w.max() / 2
        a = np.linspace(0, 2 * math.pi, 2 * CAP_STEPS, endpoint=False)
        return xy[0] + r * np.column_stack([np.cos(a), np.sin(a)])
    tangent = np.gradient(xy, axis=0)
    norm = np.linalg.norm(tangent, axis=1, keepdims=True)
    norm[norm == 0] = 1
    tangent /= norm
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    half = (w / 2)[:, None]
    left, right = xy + normal * half, xy - normal * half
    end_cap = _cap(xy[-1], normal[-1], w[-1] / 2, start=False)
    start_cap = _cap(xy[0], -normal[0], w[0] / 2, start=False)
    return np.vstack([left, end_cap, right[::-1], start_cap])


# ---------- distances (gomme, lasso) ----------

def point_segment_distance(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distance de chaque point p (n,2) au segment [a, b]."""
    ab = b - a
    denom = float(ab @ ab)
    t = np.zeros(len(p)) if denom == 0 else np.clip(((p - a) @ ab) / denom, 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def _segments_intersect(p1, p2, q1, q2) -> np.ndarray:
    """Les segments [p1[i], p2[i]] coupent-ils [q1, q2] ? (vectorisé sur i)."""
    def cross(o, a, b):
        return (a[..., 0] - o[..., 0]) * (b[..., 1] - o[..., 1]) - (a[..., 1] - o[..., 1]) * (b[..., 0] - o[..., 0])
    d1, d2 = cross(q1, q2, p1), cross(q1, q2, p2)
    d3, d4 = cross(p1, p2, q1), cross(p1, p2, q2)
    return (d1 * d2 < 0) & (d3 * d4 < 0)


def polyline_hits_segment(xy: np.ndarray, a, b, radius: float) -> bool:
    """La polyligne xy passe-t-elle à moins de radius du segment [a, b] ?

    Teste les segments entre échantillons, pas seulement les points : un geste de
    gomme rapide qui traverse un trait sans échantillon dedans l'efface quand même.
    """
    xy = np.asarray(xy, dtype=float)
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if (point_segment_distance(xy, a, b) <= radius).any():
        return True
    if len(xy) < 2:
        return False
    p1, p2 = xy[:-1], xy[1:]
    if _segments_intersect(p1, p2, a, b).any():
        return True
    # Extrémités du geste proches d'un segment du trait.
    for q in (a, b):
        seg = p2 - p1
        denom = (seg * seg).sum(axis=1)
        denom[denom == 0] = 1
        t = np.clip(((q - p1) * seg).sum(axis=1) / denom, 0, 1)
        if (np.linalg.norm(q - (p1 + t[:, None] * seg), axis=1) <= radius).any():
            return True
    return False


def resample(points, step: float):
    """Insère des points intermédiaires pour qu'aucun écart ne dépasse step."""
    if len(points) < 2:
        return list(points)
    out = [points[0]]
    for prev, cur in zip(points, points[1:]):
        d = math.hypot(cur[0] - prev[0], cur[1] - prev[1])
        n = int(d // step)
        for k in range(1, n + 1):
            f = k / (n + 1)
            out.append(tuple(prev[i] + (cur[i] - prev[i]) * f for i in range(4)))
        out.append(cur)
    return out


def split_by_eraser(points, a, b, radius: float):
    """Gomme partielle : renvoie les morceaux de trait restants (listes de points)."""
    pts = resample(points, max(radius / 2, 0.2))
    xy = np.array([(p[0], p[1]) for p in pts])
    keep = point_segment_distance(xy, np.asarray(a, float), np.asarray(b, float)) > radius
    pieces, current = [], []
    for p, k in zip(pts, keep):
        if k:
            current.append(p)
        elif current:
            pieces.append(current)
            current = []
    if current:
        pieces.append(current)
    return pieces


def point_in_polygon(xy: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """Test pair-impair vectorisé : quels points de xy (n,2) sont dans poly (m,2) ?"""
    xy, poly = np.asarray(xy, float), np.asarray(poly, float)
    x, y = xy[:, 0][:, None], xy[:, 1][:, None]
    x1, y1 = poly[:, 0], poly[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    cond = (y1 > y) != (y2 > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        xint = (x2 - x1) * (y - y1) / (y2 - y1) + x1
    return ((cond & (x < xint)).sum(axis=1) % 2) == 1
