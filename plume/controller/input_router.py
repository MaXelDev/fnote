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
MOUSE_WAKE_PX = 8.0  # la souris doit vraiment bouger pour faire revenir le curseur
_PEN_EVENTS = {QEvent.Type.TabletPress, QEvent.Type.TabletMove, QEvent.Type.TabletRelease}


class InputRouter(QObject):
    proximityChanged = Signal(bool)

    def __init__(self, app: QApplication):
        super().__init__(app)
        self.pen_near = False
        self._pen_left_at = 0.0
        self._cursor_hidden = False
        self._mouse_from = None  # position souris de référence depuis le dernier passage du stylet
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
            self._mouse_from = None
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
            self._mouse_from = None
        elif t == QEvent.Type.Enter and obj.isWidgetType() and obj.isWindow():
            self._mouse_from = None  # GNOME ramène la souris sous la pointe : nouvelle référence
        elif t == QEvent.Type.MouseMove and self._cursor_hidden and not self.pen_near:
            dev = event.pointingDevice()
            if dev is not None and dev.type() in (QInputDevice.DeviceType.Mouse, QInputDevice.DeviceType.TouchPad):
                # GNOME envoie un faux mouvement du pavé tactile quand le stylet s'éloigne :
                # seul un vrai déplacement (distance depuis la première position vue) rend le curseur.
                pos = event.globalPosition()
                if self._mouse_from is None:
                    self._mouse_from = pos
                elif (pos - self._mouse_from).manhattanLength() > MOUSE_WAKE_PX:
                    self._show_cursor()
        return False


_router: InputRouter | None = None


def router() -> InputRouter:
    """Routeur unique de l'application (créé à la première demande)."""
    global _router
    if _router is None:
        _router = InputRouter(QApplication.instance())
    return _router
