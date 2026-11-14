"""Outil actif et réglages des outils, partagés par tous les onglets."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .tools.eraser import EraserTool
from .tools.ink import InkTool
from .tools.lasso import LassoTool

MODES = ("pen", "highlighter", "eraser", "lasso")


class ToolState(QObject):
    changed = Signal()

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.mode = "pen"
        self.factories = {}  # outils ajoutés par les phases suivantes : mode → f(canvas, state)

    @property
    def pen_spec(self) -> dict:
        favs = self.config.favorites
        i = min(max(self.config.active_favorite, 0), len(favs) - 1)
        return favs[i]

    def set_mode(self, mode: str):
        self.mode = mode
        self.changed.emit()

    def set_favorite(self, index: int):
        self.config.active_favorite = index
        self.mode = "pen"
        self.changed.emit()

    def update_pen(self, **values):
        self.pen_spec.update(values)
        self.changed.emit()

    def update_highlighter(self, **values):
        self.config.highlighter.update(values)
        self.changed.emit()

    def update_eraser(self, **values):
        self.config.eraser.update(values)
        self.changed.emit()

    def make_tool(self, canvas, mode: str | None = None):
        mode = mode or self.mode
        if mode in self.factories:
            return self.factories[mode](canvas, self)
        if mode == "highlighter":
            return InkTool(canvas, self.config.highlighter)
        if mode == "eraser":
            return EraserTool(canvas, self.config.eraser)
        if mode == "lasso":
            return LassoTool(canvas, self)
        return InkTool(canvas, self.pen_spec)

    def make_side_tool(self, canvas):
        """Bouton latéral maintenu / bout gomme du stylet."""
        return self.make_tool(canvas, "lasso" if self.config.side_button_action == "lasso" else "eraser")
