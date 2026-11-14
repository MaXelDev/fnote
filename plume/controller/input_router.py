"""Routage global des entrées : proximité du stylet, curseur caché, rejet de la paume.

Sous Wayland, TabletEnterProximity / TabletLeaveProximity arrivent à QApplication et
pas au widget : d'où ce filtre installé sur l'application entière.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QCursor, QInputDevice
from PySide6.QtWidgets import QApplication

PALM_GRACE_S = 0.5  # le tactile reste ignoré un instant après le départ du stylet
_PEN_EVENTS = {QEvent.Type.TabletPress, QEvent.Type.TabletMove, QEvent.Type.TabletRelease}


class InputRouter(QObject):
    proximityChanged = Signal(bool)

    def __init__(self, app: QApplication):
        super().__init__(app)
        self.pen_near = False
        self._pen_left_at = 0.0
        self._cursor_hidden = False
        app.installEventFilter(self)

    # ----- état -----
    def palm_blocked(self) -> bool:
        """Vrai si le tactile doit être ignoré (stylet proche ou vient de partir)."""
        return self.pen_near or time.monotonic() - self._pen_left_at < PALM_GRACE_S

    def mouse_blocked(self) -> bool:
        """La souris ne doit pas voler la position du stylet (pointeur qui « saute »)."""
        return self.pen_near

    # ----- curseur -----
    def _hide_cursor(self):
        if not self._cursor_hidden:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))
            self._cursor_hidden = True

    def _show_cursor(self):
        if self._cursor_hidden:
            QApplication.restoreOverrideCursor()
            self._cursor_hidden = False

    # ----- filtre -----
    def eventFilter(self, obj, event):
        t = event.type()
        if t == QEvent.Type.TabletEnterProximity:
            self.pen_near = True
            self._hide_cursor()
            self.proximityChanged.emit(True)
        elif t == QEvent.Type.TabletLeaveProximity:
            self.pen_near = False
            self._pen_left_at = time.monotonic()
            self.proximityChanged.emit(False)
        elif t in _PEN_EVENTS:
            # Certains compositeurs n'envoient pas la proximité : on cache quand même.
            if not self.pen_near:
                self.pen_near = True
                self.proximityChanged.emit(True)
            self._hide_cursor()
        elif t == QEvent.Type.MouseMove and self._cursor_hidden and not self.pen_near:
            dev = event.pointingDevice()
            if dev is not None and dev.type() in (QInputDevice.DeviceType.Mouse, QInputDevice.DeviceType.TouchPad):
                self._show_cursor()  # la vraie souris bouge : le curseur revient
        return False


_router: InputRouter | None = None


def router() -> InputRouter:
    """Routeur unique de l'application (créé à la première demande)."""
    global _router
    if _router is None:
        _router = InputRouter(QApplication.instance())
    return _router
