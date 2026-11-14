"""Reconnaissance de formes : trait à main levée → ligne, rectangle, ellipse/cercle, triangle, flèche.

recognize(points) renvoie (kind, geometry) ou None. geometry suit le format de Shape :
ligne/flèche = [début, fin] ; rectangle = 4 sommets ; triangle = 3 sommets ;
ellipse = 4 coins de son rectangle englobant (éventuellement pivoté).
"""
from __future__ import annotations

import math

import numpy as np

MIN_SIZE = 6.0          # points de page
SNAP_DEG = 6.0          # aimantation horizontale / verticale / 45°


def _cross(a, b):
    """Produit vectoriel 2D (NumPy ≥ 2 ne l'accepte plus en 2D)."""
    a, b = np.asarray(a), np.asarray(b)
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _dp(xy: np.ndarray, eps: float) -> np.ndarray:
    """Douglas-Peucker itératif, renvoie les indices gardés."""
    keep = np.zeros(len(xy), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(xy) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        seg = xy[b] - xy[a]
        n = np.linalg.norm(seg)
        rel = xy[a + 1:b] - xy[a]
        d = np.abs(_cross(seg, rel)) / n if n > 0 else np.linalg.norm(rel, axis=1)
        i = int(np.argmax(d))
        if d[i] > eps:
            k = a + 1 + i
            keep[k] = True
            stack += [(a, k), (k, b)]
    return np.flatnonzero(keep)


def _snap_angle(theta: float, step: float = 90.0) -> float:
    deg = math.degrees(theta)
    snapped = round(deg / step) * step
    return math.radians(snapped) if abs(deg - snapped) < SNAP_DEG else theta


def _rot(theta: float) -> np.ndarray:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s], [s, c]])


def _line_dev(xy: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    seg = b - a
    n = np.linalg.norm(seg)
    if n == 0:
        return float("inf")
    return float(np.max(np.abs(_cross(seg, xy - a)) / n))


def _straight_line(xy):
    a, b = xy[0], xy[-1]
    theta = _snap_angle(math.atan2(*(b - a)[::-1]), 45.0)
    length = np.linalg.norm(b - a)
    return a, a + length * np.array([math.cos(theta), math.sin(theta)])


def _box_corners(center, theta, half_w, half_h) -> list:
    r = _rot(theta)
    local = np.array([[-half_w, -half_h], [half_w, -half_h], [half_w, half_h], [-half_w, half_h]])
    return [tuple(map(float, p)) for p in local @ r.T + center]


def _ellipse(xy) -> tuple[float, list] | None:
    c = xy.mean(axis=0)
    cov = np.cov((xy - c).T)
    vals, vecs = np.linalg.eigh(cov)
    major = vecs[:, 1]
    theta = math.atan2(major[1], major[0])
    local = (xy - c) @ _rot(theta)
    lo, hi = local.min(axis=0), local.max(axis=0)
    a, b = (hi - lo) / 2
    if min(a, b) < 1e-6:
        return None
    center = c + _rot(theta) @ ((hi + lo) / 2)
    local = (xy - center) @ _rot(theta)
    resid = float(np.mean(np.abs((local[:, 0] / a) ** 2 + (local[:, 1] / b) ** 2 - 1)))
    if b / a > 0.85:  # presque rond : cercle parfait
        a = b = (a + b) / 2
    theta = _snap_angle(theta)
    return resid, _box_corners(center, theta, a, b)


def _rectangle(xy, verts) -> list | None:
    v = xy[verts]
    edges = np.roll(v, -1, axis=0) - v
    # angles internes proches de 90°
    for i in range(4):
        e1, e2 = edges[i - 1], edges[i]
        cosang = abs(np.dot(e1, e2)) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-9)
        if cosang > 0.42:  # > ~25° d'écart avec l'angle droit
            return None
    longest = edges[np.argmax(np.linalg.norm(edges, axis=1))]
    theta = _snap_angle(math.atan2(longest[1], longest[0]))
    local = xy @ _rot(theta)
    lo, hi = local.min(axis=0), local.max(axis=0)
    center = _rot(theta) @ ((hi + lo) / 2)
    return _box_corners(center, theta, *((hi - lo) / 2))


def _arrow(xy, diag):
    start = xy[0]
    d = np.linalg.norm(xy - start, axis=1)
    tip = int(np.argmax(d))
    if tip >= len(xy) - 3 or tip < 3:
        return None
    shaft_len = d[tip]
    if _line_dev(xy[:tip + 1], start, xy[tip]) > 0.08 * shaft_len:
        return None
    head = xy[tip:]
    head_len = np.sum(np.linalg.norm(np.diff(head, axis=0), axis=1))
    near = np.linalg.norm(head - xy[tip], axis=1).max()
    if 0.1 * shaft_len <= head_len <= 1.2 * shaft_len and near <= 0.4 * shaft_len:
        a, b = _straight_line(np.array([start, xy[tip]]))
        return "arrow", [tuple(map(float, a)), tuple(map(float, b))]
    return None


def _smooth(xy: np.ndarray) -> np.ndarray:
    """Moyenne glissante [1,2,3,2,1] : retire le tremblement de la main, garde les extrémités."""
    if len(xy) < 7:
        return xy
    k = np.array([1, 2, 3, 2, 1], float)
    k /= k.sum()
    out = xy.copy()
    for d in range(2):
        out[2:-2, d] = np.convolve(xy[:, d], k, mode="valid")
    return out


def _rms_dev(xy, a, b) -> float:
    seg = b - a
    n = np.linalg.norm(seg)
    return float(np.sqrt(np.mean((_cross(seg, xy - a) / n) ** 2))) if n else float("inf")


def recognize(points):
    xy = np.array([(p[0], p[1]) for p in points], float)
    if len(xy) < 5:
        return None
    xy = _smooth(xy)
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    diag = float(np.linalg.norm(hi - lo))
    if diag < MIN_SIZE:
        return None
    gap = float(np.linalg.norm(xy[-1] - xy[0]))
    closed = gap < 0.2 * diag

    if not closed:
        chord = gap
        length = float(np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1)))
        if (chord > 0 and length / chord < 1.15 and _rms_dev(xy, xy[0], xy[-1]) < 0.035 * chord
                and _line_dev(xy, xy[0], xy[-1]) < 0.1 * chord):
            a, b = _straight_line(xy)
            return "line", [tuple(map(float, a)), tuple(map(float, b))]
        return _arrow(xy, diag)

    ring = np.vstack([xy, xy[:1]])
    idx = _dp(ring, 0.06 * diag)[:-1]  # sommets (le dernier = premier)
    if len(idx) == 3:
        return "triangle", [tuple(map(float, ring[i])) for i in idx]
    if len(idx) == 4:
        rect = _rectangle(ring, idx)
        if rect is not None:
            return "rect", rect
    ell = _ellipse(xy)
    if ell is not None and ell[0] < 0.22 and len(idx) >= 5:
        return "ellipse", ell[1]
    return None
