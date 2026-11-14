"""Courbe de pression réglable : pression brute du stylet (0..1) → facteur d'épaisseur."""
from __future__ import annotations

import numpy as np


class PressureCurve:
    """Courbe définie par des points (pression, facteur), interpolée linéairement et monotone."""

    def __init__(self, points=((0.0, 0.15), (0.5, 0.6), (1.0, 1.0))):
        pts = sorted((min(max(float(x), 0.0), 1.0), max(float(y), 0.0)) for x, y in points)
        if len(pts) < 2:
            pts = [(0.0, 0.15), (1.0, 1.0)]
        self.x = np.array([p[0] for p in pts])
        # Monotone : appuyer plus fort ne doit jamais affiner le trait.
        self.y = np.maximum.accumulate(np.array([p[1] for p in pts]))

    def __call__(self, pressure):
        return np.interp(np.clip(pressure, 0.0, 1.0), self.x, self.y)

    @classmethod
    def from_sensitivity(cls, sensitivity: float) -> "PressureCurve":
        """Réglage simple : 0 = ferme (il faut appuyer), 1 = très sensible."""
        s = min(max(sensitivity, 0.0), 1.0)
        mid = 0.35 + 0.5 * s
        return cls([(0.0, 0.1 + 0.15 * s), (0.5, mid), (1.0, 1.0)])
