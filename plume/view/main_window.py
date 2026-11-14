"""Fenêtre principale (phase 0) : choix du vault, nouvelle note, ouvrir, enregistrer.

La zone centrale affiche les pages ; le vrai canevas d'écriture arrive en phase 1.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QAction, QKeySequence, QPainter
from PySide6.QtWidgets import (QFileDialog, QInputDialog, QMainWindow, QMessageBox, QScrollArea,
                               QSizePolicy, QWidget)

from ..model import serialization
from ..model.config import Config
from ..model.document import Document
from . import style


class PagesPreview(QWidget):
    """Pages blanches empilées, ajustées à la largeur. Remplacé par Canvas en phase 1."""

    MARGIN = 24

    def __init__(self):
        super().__init__()
        self.doc: Document | None = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_document(self, doc: Document | None) -> None:
        self.doc = doc
        self._relayout()
        self.update()

    def _scale(self) -> float:
        if not self.doc:
            return 1.0
        widest = max(p.width for p in self.doc.pages)
        return min(1.6, max(0.2, (self.width() - 2 * self.MARGIN) / widest))

    def _relayout(self) -> None:
        if self.doc:
            gap = style.tokens()["page"]["gap"]
            h = sum(p.height * self._scale() + gap for p in self.doc.pages) + 2 * self.MARGIN
            self.setMinimumHeight(int(h))

    def resizeEvent(self, event):
        self._relayout()
        super().resizeEvent(event)

    def paintEvent(self, event):
        c = style.colors()
        painter = QPainter(self)
        painter.fillRect(self.rect(), c["desk"])
        if not self.doc:
            return
        s, y = self._scale(), self.MARGIN
        gap = style.tokens()["page"]["gap"]
        for page in self.doc.pages:
            w, h = page.width * s, page.height * s
            painter.fillRect(QRectF((self.width() - w) / 2, y, w, h), c["page"])
            y += h + gap


class MainWindow(QMainWindow):
    def __init__(self, config: Config, open_path: str | None = None):
        super().__init__()
        self.config = config
        self.doc: Document | None = None
        self.path: Path | None = None
        self.resize(1100, 800)

        self.preview = PagesPreview()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.preview)
        self.setCentralWidget(scroll)
        self._build_menus()

        if open_path:
            self.open_file(Path(open_path))
        self._update_title()

    # ----- menus -----
    def _action(self, menu, text, slot, shortcut=None):
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    def _build_menus(self):
        m = self.menuBar().addMenu("&Fichier")
        self._action(m, "Nouvelle note…", self.new_note, QKeySequence.StandardKey.New)
        self._action(m, "Ouvrir…", self.open_dialog, QKeySequence.StandardKey.Open)
        self._action(m, "Enregistrer", self.save, QKeySequence.StandardKey.Save)
        m.addSeparator()
        self._action(m, "Choisir le vault…", self.choose_vault)
        m.addSeparator()
        self._action(m, "Quitter", self.close, QKeySequence.StandardKey.Quit)
        v = self.menuBar().addMenu("&Affichage")
        self._action(v, "Plein écran", self.toggle_fullscreen, "F11")
        h = self.menuBar().addMenu("&Aide")
        self._action(h, "Diagnostic du stylet…", self.show_tablet_debug)

    # ----- vault -----
    def vault(self) -> Path | None:
        p = Path(self.config.vault_path) if self.config.vault_path else None
        return p if p and p.is_dir() else None

    def ensure_vault(self) -> Path | None:
        """Premier lancement (S12) : demande le dossier racine des notes."""
        if self.vault() is None:
            if self.config.vault_path:
                QMessageBox.warning(self, "Vault introuvable",
                                    f"Le dossier « {self.config.vault_path} » n'existe plus. Choisis ton vault.")
            self.choose_vault()
        return self.vault()

    def choose_vault(self) -> None:
        start = self.config.vault_path or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Choisir le dossier de tes notes (vault Obsidian)", start)
        if folder:
            self.config.vault_path = folder
            self.config.save()
            self._update_title()

    # ----- notes -----
    def new_note(self) -> None:
        vault = self.ensure_vault()
        if not vault:
            return
        name, ok = QInputDialog.getText(self, "Nouvelle note", "Nom de la note :")
        name = name.strip().replace("/", "-")
        if not ok or not name:
            return
        path = vault / f"{name}.plume"
        if path.exists():
            QMessageBox.warning(self, "Nom déjà pris", f"« {path.name} » existe déjà dans le vault.")
            return
        doc = Document(title=name)
        doc.pages[0].background = {"kind": self.config.default_background}
        serialization.save(doc, path)
        self._set_document(doc, path)

    def open_dialog(self) -> None:
        start = str(self.vault() or Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir une note", start, "Notes Plume (*.plume)")
        if path:
            self.open_file(Path(path))

    def open_file(self, path: Path) -> None:
        try:
            doc = serialization.load(path)
        except (OSError, serialization.PlumeFormatError) as exc:
            QMessageBox.critical(self, "Impossible d'ouvrir la note", f"{path.name} : {exc}")
            return
        self._set_document(doc, path)

    def save(self) -> None:
        if not (self.doc and self.path):
            return
        try:
            serialization.save(self.doc, self.path)
            self.statusBar().showMessage("Enregistré", 2000)
        except OSError as exc:
            QMessageBox.critical(self, "Échec de l'enregistrement", str(exc))

    def _set_document(self, doc: Document, path: Path) -> None:
        self.doc, self.path = doc, path
        self.preview.set_document(doc)
        self._update_title()

    def _update_title(self) -> None:
        name = self.path.stem if self.path else "aucune note"
        self.setWindowTitle(f"{name} — Plume")

    # ----- divers -----
    def toggle_fullscreen(self) -> None:
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def show_tablet_debug(self) -> None:
        from .debug_tablet import TabletDebugWindow
        self._debug = TabletDebugWindow()
        self._debug.show()
