"""Fenêtre de diagnostic du stylet (--debug-tablet).

Affiche en direct ce que Qt reçoit : type de périphérique, pression, inclinaison,
boutons, proximité, fréquence des événements, échelle d'écran et décalage entre
la position du stylet et celle du pointeur souris.
"""
from __future__ import annotations

import time
from collections import deque

from PySide6.QtCore import QEvent, QObject, QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QInputDevice, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QListWidget, QVBoxLayout, QWidget)

PROXIMITY = {QEvent.Type.TabletEnterProximity: "entrée en proximité", QEvent.Type.TabletLeaveProximity: "sortie de proximité"}


def _name(enum_value) -> str:
    return getattr(enum_value, "name", str(enum_value))


class _ProximityFilter(QObject):
    """Qt envoie la proximité à QApplication, pas au widget : filtre global."""

    def __init__(self, window: "TabletDebugWindow"):
        super().__init__(window)
        self.window = window

    def eventFilter(self, obj, event):
        if event.type() in PROXIMITY:
            self.window.on_proximity(event)
        return False


class DrawArea(QWidget):
    """Zone d'essai : chaque échantillon du stylet est un disque proportionnel à la pression."""

    def __init__(self, window: "TabletDebugWindow"):
        super().__init__()
        self.window = window
        self.samples: deque[tuple[QPointF, float]] = deque(maxlen=4000)
        self.setMinimumSize(500, 360)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)

    def tabletEvent(self, event):
        self.window.on_tablet(event)
        if event.type() == QEvent.Type.TabletMove and event.pressure() > 0:
            self.samples.append((event.position(), event.pressure()))
            self.update()
        event.accept()  # pas d'événement souris synthétisé

    def mouseMoveEvent(self, event):
        self.window.on_mouse(event)

    def mousePressEvent(self, event):
        self.window.on_mouse(event)

    def event(self, event):
        if event.type() in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd):
            self.window.on_touch(event)
            return True
        return super().event(event)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#ffffff"))
        p.setPen(QPen(QColor("#c9d3df")))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        if not self.samples:
            p.setPen(QColor("#565f6b"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Écris ici avec le stylet.\nLa taille des points suit la pression.")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#1f5fd1"))
        for pos, pressure in self.samples:
            r = 0.5 + 4 * pressure
            p.drawEllipse(pos, r, r)


class TabletDebugWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diagnostic du stylet — Plume")
        self.resize(900, 620)
        self.last_tablet: QPointF | None = None
        self.last_mouse: QPointF | None = None
        self.times: deque[float] = deque(maxlen=200)

        self.live = QLabel()
        self.live.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.live.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.live.setMinimumWidth(330)
        self.log = QListWidget()
        self.area = DrawArea(self)

        right = QVBoxLayout()
        right.addWidget(self.live)
        right.addWidget(QLabel("Événements (proximité, tactile, boutons) :"))
        right.addWidget(self.log)
        layout = QHBoxLayout(self)
        layout.addWidget(self.area, 3)
        layout.addLayout(right, 2)

        self.info = {"Plateforme Qt": QGuiApplication.platformName()}
        self._screen_info()
        self._log_devices()
        QApplication.instance().installEventFilter(_ProximityFilter(self))
        self._refresh()

    def _screen_info(self):
        screen = self.screen() or QGuiApplication.primaryScreen()
        self.info["Échelle écran (devicePixelRatio)"] = f"{screen.devicePixelRatio():g}"
        self.info["Résolution logique"] = f"{screen.size().width()}×{screen.size().height()}"

    def _log_devices(self):
        for dev in QInputDevice.devices():
            self._add_log(f"périphérique : {dev.name() or '(sans nom)'} — {_name(dev.type())}")

    def _add_log(self, text: str):
        self.log.insertItem(0, f"{time.strftime('%H:%M:%S')}  {text}")
        if self.log.count() > 300:
            self.log.takeItem(self.log.count() - 1)

    # ----- réception -----
    def on_tablet(self, e):
        now = time.perf_counter()
        self.times.append(now)
        dev = e.pointingDevice()
        self.last_tablet = e.globalPosition()
        self.info.update({
            "Événement": _name(e.type()),
            "Périphérique": f"{dev.name() or '?'} ({_name(dev.type())})",
            "Pointe": _name(dev.pointerType()),
            "Pression": f"{e.pressure():.3f}",
            "Inclinaison X / Y": f"{e.xTilt():.0f}° / {e.yTilt():.0f}°",
            "Rotation": f"{e.rotation():.0f}°",
            "Boutons": _name(e.buttons()),
            "Position (pixels logiques)": f"{e.position().x():.2f}, {e.position().y():.2f}",
        })
        if e.type() in (QEvent.Type.TabletPress, QEvent.Type.TabletRelease):
            self._add_log(f"{_name(e.type())} bouton={_name(e.button())} pression={e.pressure():.2f}")
        self._refresh()

    def on_proximity(self, e):
        self._add_log(f"stylet : {PROXIMITY[e.type()]} ({_name(e.pointingDevice().pointerType())})")
        self.info["Proximité"] = "oui" if e.type() == QEvent.Type.TabletEnterProximity else "non"
        self._refresh()

    def on_mouse(self, e):
        self.last_mouse = e.globalPosition()
        self.info["Source souris"] = _name(e.pointingDevice().type())
        self._refresh()

    def on_touch(self, e):
        pts = e.points()
        self._add_log(f"tactile : {_name(e.type())}, {len(pts)} doigt(s)")

    def _refresh(self):
        if len(self.times) > 1 and self.times[-1] - self.times[0] > 0:
            self.info["Fréquence stylet"] = f"{(len(self.times) - 1) / (self.times[-1] - self.times[0]):.0f} Hz"
        if self.last_tablet is not None and self.last_mouse is not None:
            d = self.last_tablet - self.last_mouse
            self.info["Décalage stylet ↔ pointeur"] = f"{d.x():.1f}, {d.y():.1f} px"
        self.live.setText("\n".join(f"{k} : {v}" for k, v in self.info.items()))
