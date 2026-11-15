"""Barre d'outils unique : annuler/rétablir, stylos favoris, outils, actions.

Un appui sélectionne l'outil ; un second appui sur l'outil déjà actif ouvre ses réglages.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QToolBar, QToolButton, QWidget

from . import icons, style
from .popovers import EraserPopover, HighlighterPopover, LassoPopover, PenPopover
from .render import qcolor

TIP_NAMES = {"fountain": "plume", "ballpoint": "bille", "pencil": "crayon"}


class FavoriteButton(QToolButton):
    def __init__(self, state, index: int):
        super().__init__()
        self.state, self.index = state, index
        self.setObjectName("favorite")
        self.setCheckable(True)
        size = style.tokens()["size"]["tool-button"]
        self.setFixedSize(QSize(size, size))

    def spec(self) -> dict:
        return self.state.config.favorites[self.index]

    def refresh(self):
        s = self.spec()
        self.setToolTip(f"Stylo favori {self.index + 1} — {TIP_NAMES.get(s['tool'], s['tool'])}, {s['width']:.1f} pt "
                        f"(touche {self.index + 1})")
        self.setAccessibleName(self.toolTip())
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        s = self.spec()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = qcolor(s["color"])
        r = QRectF(self.rect()).adjusted(11, 11, -11, -11)
        p.setPen(QPen(QColor(style.colors()["border"]), 1))
        p.setBrush(c)
        p.drawEllipse(r)
        # trait de l'épaisseur du stylo, en blanc sur la pastille
        p.setPen(QPen(QColor(255, 255, 255, 230), max(1.2, min(6.0, s["width"] * 1.4)), Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawLine(r.left() + 6, r.center().y() + 3, r.right() - 6, r.center().y() - 3)


class Toolbar(QToolBar):
    action = Signal(str)  # actions déléguées à la fenêtre : undo, redo, ruler, image, pages, fit, sidebar…

    def __init__(self, state, parent=None):
        super().__init__("Outils", parent)
        self.state = state
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QSize(24, 24))
        self._popover = None
        self.buttons: dict[str, QToolButton] = {}

        self._button("sidebar", "Afficher/masquer les notes (F9)", self._emit("sidebar"))
        self.addSeparator()
        self._button("undo", "Annuler (Ctrl+Z)", self._emit("undo"))
        self._button("redo", "Rétablir (Ctrl+Y)", self._emit("redo"))
        self.addSeparator()
        self.favorites = []
        for i in range(len(state.config.favorites)):
            b = FavoriteButton(state, i)
            b.clicked.connect(lambda _=False, i=i: self._favorite_clicked(i))
            self.addWidget(b)
            self.favorites.append(b)
        self.addSeparator()
        for mode, tip in (("highlighter", "Surligneur (H)"), ("eraser", "Gomme (E)"), ("lasso", "Lasso (L)")):
            self._button(mode, tip, lambda _=False, m=mode: self._mode_clicked(m), checkable=True)
        self._button("shapes", "Formes auto-corrigées : maintenir le stylet immobile à la fin du trait",
                     self._toggle_shapes, checkable=True)
        self._button("ruler", "Règle (R)", self._emit("ruler"), checkable=True)
        self._button("image", "Insérer une image", self._emit("image"))
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)
        self._button("pages", "Pages", self._emit("pages"), checkable=True)
        self._button("fit", "Ajuster à la largeur (Ctrl+0)", self._emit("fit"))
        self._button("menu", "Menu", self._emit("menu"))
        state.changed.connect(self.sync)
        self.sync()

    def _emit(self, name):
        return lambda *_: self.action.emit(name)

    def _button(self, name, tip, slot, checkable=False) -> QToolButton:
        b = QToolButton()
        b.setObjectName("tool")
        b.setIcon(icons.icon(name))
        b.setToolTip(tip)
        b.setAccessibleName(tip)
        b.setCheckable(checkable)
        b.clicked.connect(slot)
        self.addWidget(b)
        self.buttons[name] = b
        return b

    # ----- comportements -----
    def _favorite_clicked(self, i: int):
        already = self.state.mode == "pen" and self.state.config.active_favorite == i
        if already:
            self._open(PenPopover(self.state), self.favorites[i])
        else:
            self.state.set_favorite(i)
        self.sync()

    def _mode_clicked(self, mode: str):
        if self.state.mode == mode:
            pop = {"highlighter": HighlighterPopover, "eraser": EraserPopover, "lasso": LassoPopover}.get(mode)
            if pop:
                self._open(pop(self.state), self.buttons[mode])
        else:
            self.state.set_mode(mode)
        self.sync()

    def _toggle_shapes(self, on: bool):
        self.state.config.shape_recognition = on
        self.state.changed.emit()
        win = self.window()
        if hasattr(win, "statusBar"):  # un interrupteur sans retour se désactive sans qu'on le voie
            win.statusBar().showMessage(
                "Formes auto-corrigées activées : trace la forme puis garde le stylet immobile"
                if on else "Formes auto-corrigées désactivées", 5000)

    def _open(self, popover, anchor):
        self._popover = popover
        popover.show_below(anchor)

    def sync(self):
        cfg = self.state.config
        for i, b in enumerate(self.favorites):
            b.setChecked(self.state.mode == "pen" and cfg.active_favorite == i)
            b.refresh()
        for mode in ("highlighter", "eraser", "lasso"):
            self.buttons[mode].setChecked(self.state.mode == mode)
        self.buttons["shapes"].setChecked(cfg.shape_recognition)

    def set_checked(self, name: str, on: bool):
        if name in self.buttons:
            self.buttons[name].setChecked(on)

    def set_enabled(self, name: str, on: bool):
        if name in self.buttons:
            self.buttons[name].setEnabled(on)
