"""Géométrie de la règle virtuelle (pure, testable) : bords, aimantation du trait, angles."""
from __future__ import annotations

import math

SNAP_ANGLES_STEP = 15.0
SNAP_ANGLE_TOL = 2.5
EDGE_CAPTURE = 18.0   # px : un trait commencé à moins de cette distance d'un bord s'y aimante


def snap_angle(deg: float) -> float:
    """Aimante aux multiples de 15° (0, 15, 30, 45, 90…) quand on en est proche."""
    snapped = round(deg / SNAP_ANGLES_STEP) * SNAP_ANGLES_STEP
    return snapped if abs(deg - snapped) <= SNAP_ANGLE_TOL else deg


def normalize_deg(deg: float) -> float:
    """Angle affiché dans ]-90, 90] (une règle à 180° est la même qu'à 0°)."""
    d = (deg + 90) % 180 - 90
    return 90.0 if d == -90 else d


class RulerGeometry:
    """Règle centrée en (cx, cy), de longueur L et d'épaisseur T, pivotée de `angle` degrés (écran)."""

    def __init__(self, cx: float, cy: float, angle: float = 0.0, length: float = 700.0, thickness: float = 72.0):
        self.cx, self.cy, self.angle, self.length, self.thickness = cx, cy, angle, length, thickness

    @property
    def u(self):  # direction de la règle
        a = math.radians(self.angle)
        return math.cos(a), math.sin(a)

    @property
    def n(self):  # normale (vers le bas de la règle)
        ux, uy = self.u
        return -uy, ux

    def to_local(self, x: float, y: float) -> tuple[float, float]:
        dx, dy = x - self.cx, y - self.cy
        ux, uy = self.u
        nx, ny = self.n
        return dx * ux + dy * uy, dx * nx + dy * ny

    def to_screen(self, s: float, t: float) -> tuple[float, float]:
        ux, uy = self.u
        nx, ny = self.n
        return self.cx + s * ux + t * nx, self.cy + s * uy + t * ny

    def contains(self, x: float, y: float) -> bool:
        s, t = self.to_local(x, y)
        return abs(s) <= self.length / 2 and abs(t) <= self.thickness / 2

    def edge_near(self, x: float, y: float) -> int | None:
        """-1 = bord du haut, +1 = bord du bas, None = trop loin."""
        s, t = self.to_local(x, y)
        if abs(s) > self.length / 2 + EDGE_CAPTURE:
            return None
        for side in (-1, 1):
            if abs(t - side * self.thickness / 2) <= EDGE_CAPTURE and abs(t) >= self.thickness / 2 - EDGE_CAPTURE:
                return side
        return None

    def project(self, x: float, y: float, side: int, offset: float = 0.0) -> tuple[float, float]:
        """Point projeté sur le bord `side`, décalé de `offset` vers l'extérieur (demi-épaisseur du trait)."""
        s, _ = self.to_local(x, y)
        return self.to_screen(s, side * (self.thickness / 2 + offset))
