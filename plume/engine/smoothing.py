"""Lissage du trait.

Pendant le tracé : moyenne pondérée des 3 derniers échantillons bruts, qui favorise
le plus récent → retard inférieur à un échantillon (≈ 2 ms à 200 Hz), donc invisible.
Au lever du stylet : lissage plus fort (noyau [1, 2, 1] en deux passes),
extrémités conservées, points quasi confondus supprimés.
"""
from __future__ import annotations

import numpy as np

_W = np.array([1.0, 2.0, 4.0])


class StreamSmoother:
    def __init__(self):
        self._raw: list[tuple[float, float, float, float]] = []

    def add(self, point):
        """point = (x, y, pression, t) → point lissé, à dessiner tout de suite."""
        self._raw.append(point)
        last = np.array(self._raw[-3:], dtype=float)
        w = _W[-len(last):]
        x, y, p = (last[:, :3] * w[:, None]).sum(axis=0) / w.sum()
        return (float(x), float(y), float(p), point[3])


def dedupe(points, min_dist: float = 0.05):
    """Supprime les points à moins de min_dist du précédent (garde toujours le dernier)."""
    if len(points) < 3:
        return list(points)
    out = [points[0]]
    for p in points[1:-1]:
        if (p[0] - out[-1][0]) ** 2 + (p[1] - out[-1][1]) ** 2 >= min_dist ** 2:
            out.append(p)
    out.append(points[-1])
    return out


def finalize(points, passes: int = 2):
    """Lissage final au lever du stylet. Les extrémités ne bougent pas."""
    pts = dedupe(points)
    if len(pts) < 3:
        return [tuple(map(float, p)) for p in pts]
    a = np.array(pts, dtype=float)
    for _ in range(passes):
        inner = (a[:-2, :3] + 2 * a[1:-1, :3] + a[2:, :3]) / 4
        a[1:-1, :3] = inner
    return [tuple(map(float, row)) for row in a]
