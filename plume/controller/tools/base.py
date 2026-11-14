"""Interface commune des outils. Positions en coordonnées du viewport (pixels logiques)."""
from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter


class Tool:
    name = ""
    dot_color: QColor | None = None  # couleur du point de survol (None = pas de point)

    def __init__(self, canvas):
        self.canvas = canvas

    def press(self, pos: QPointF, pressure: float, t: float) -> None: ...
    def move(self, pos: QPointF, pressure: float, t: float) -> None: ...
    def release(self, pos: QPointF, pressure: float, t: float) -> None: ...
    def hover(self, pos: QPointF) -> None: ...

    def cancel(self) -> None:
        """Interrompt le geste en cours sans rien valider."""

    def paint_overlay(self, painter: QPainter) -> None:
        """Dessin par-dessus les pages (aperçu, sélection, gomme)."""

    @property
    def busy(self) -> bool:
        return False
