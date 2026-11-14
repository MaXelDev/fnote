"""Fenêtre principale : onglets de notes, barre d'outils, menus."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QFileDialog, QInputDialog, QLabel, QMainWindow, QMessageBox, QTabWidget,
                               QVBoxLayout, QWidget)

from ..controller.document_controller import DocumentController
from ..controller.tool_state import ToolState
from ..model import serialization
from ..model.config import Config
from ..model.document import Document
from .canvas import Canvas


class NoteTab(QWidget):
    """Un onglet = une note ouverte (contrôleur + canevas)."""

    titleChanged = Signal()

    def __init__(self, ctl: DocumentController, tools: ToolState, debug_perf=False):
        super().__init__()
        self.ctl, self.tools = ctl, tools
        self.canvas = Canvas(ctl.doc, ctl.history, ctl.config, debug_perf=debug_perf)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas)
        self.canvas.changed.connect(ctl.on_changed)
        ctl.dirtyChanged.connect(lambda *_: self.titleChanged.emit())
        self.apply_tools()

    def apply_tools(self):
        self.canvas.set_tool(self.tools.make_tool(self.canvas))
        self.canvas.side_tool = self.tools.make_side_tool(self.canvas)


class MainWindow(QMainWindow):
    def __init__(self, config: Config, open_path: str | None = None, debug_perf: bool = False):
        super().__init__()
        self.config = config
        self.debug_perf = debug_perf
        self.tools = ToolState(config)
        self.tools.changed.connect(self._tools_changed)
        self.resize(1200, 860)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(lambda *_: self._on_tab_changed())
        self.empty = QLabel("Crée une note (Ctrl+N) ou ouvre-en une (Ctrl+O).")
        self.empty.setObjectName("muted")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabs.addTab(self.empty, "Accueil")
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition.RightSide, None)
        self.setCentralWidget(self.tabs)
        self._build_menus()
        if open_path:
            self.open_file(Path(open_path))
        self._update_title()

    # ----- accès -----
    def current_tab(self) -> NoteTab | None:
        w = self.tabs.currentWidget()
        return w if isinstance(w, NoteTab) else None

    def note_tabs(self) -> list[NoteTab]:
        return [w for i in range(self.tabs.count()) if isinstance(w := self.tabs.widget(i), NoteTab)]

    # ----- menus -----
    def _action(self, menu, text, slot, shortcut=None):
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(slot)
        menu.addAction(act)
        self.addAction(act)
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
        e = self.menuBar().addMenu("&Édition")
        self.act_undo = self._action(e, "Annuler", self.undo, QKeySequence.StandardKey.Undo)
        self.act_redo = self._action(e, "Rétablir", self.redo, "Ctrl+Y")
        self.addAction(self._shortcut("Ctrl+Shift+Z", self.redo))
        v = self.menuBar().addMenu("&Affichage")
        self._action(v, "Zoom avant", lambda: self._zoom(1.2), QKeySequence.StandardKey.ZoomIn)
        self._action(v, "Zoom arrière", lambda: self._zoom(1 / 1.2), QKeySequence.StandardKey.ZoomOut)
        self._action(v, "Ajuster à la largeur", self.fit_width, "Ctrl+0")
        self._action(v, "Plein écran", self.toggle_fullscreen, "F11")
        h = self.menuBar().addMenu("&Aide")
        self._action(h, "Diagnostic du stylet…", self.show_tablet_debug)

    def _shortcut(self, seq, slot):
        act = QAction(self)
        act.setShortcut(QKeySequence(seq))
        act.triggered.connect(slot)
        return act

    # ----- outils -----
    def _tools_changed(self):
        for tab in self.note_tabs():
            tab.apply_tools()
        self.config.save()

    def undo(self):
        if tab := self.current_tab():
            tab.canvas.undo()

    def redo(self):
        if tab := self.current_tab():
            tab.canvas.redo()

    def _zoom(self, factor):
        if tab := self.current_tab():
            tab.canvas.set_zoom(tab.canvas.zoom * factor)

    def fit_width(self):
        if tab := self.current_tab():
            tab.canvas.zoom_fit_width()

    # ----- vault -----
    def vault(self) -> Path | None:
        p = Path(self.config.vault_path) if self.config.vault_path else None
        return p if p and p.is_dir() else None

    def ensure_vault(self) -> Path | None:
        """Premier lancement : demande le dossier racine des notes."""
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
    def new_note(self, folder: Path | None = None) -> None:
        folder = folder or self.ensure_vault()
        if not folder:
            return
        name, ok = QInputDialog.getText(self, "Nouvelle note", "Nom de la note :")
        name = name.strip().replace("/", "-")
        if not ok or not name:
            return
        path = Path(folder) / f"{name}.plume"
        if path.exists():
            QMessageBox.warning(self, "Nom déjà pris", f"« {path.name} » existe déjà.")
            return
        doc = Document(title=name)
        doc.pages[0].background = {"kind": self.config.default_background}
        serialization.save(doc, path)
        self._add_tab(DocumentController(doc, path, self.config))

    def open_dialog(self) -> None:
        start = str(self.vault() or Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir une note", start, "Notes Plume (*.plume)")
        if path:
            self.open_file(Path(path))

    def open_file(self, path: Path) -> None:
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, NoteTab) and w.ctl.path.resolve() == path.resolve():
                self.tabs.setCurrentIndex(i)
                return
        try:
            ctl = DocumentController.open(path, self.config)
        except (OSError, serialization.PlumeFormatError) as exc:
            QMessageBox.critical(self, "Impossible d'ouvrir la note", f"{path.name} : {exc}")
            return
        self._add_tab(ctl)

    def _add_tab(self, ctl: DocumentController) -> NoteTab:
        ctl.setParent(self)
        ctl.saveFailed.connect(lambda msg: QMessageBox.critical(self, "Échec de l'enregistrement", msg))
        tab = NoteTab(ctl, self.tools, self.debug_perf)
        tab.titleChanged.connect(self._refresh_tab_titles)
        if self.tabs.indexOf(self.empty) >= 0:
            self.tabs.removeTab(self.tabs.indexOf(self.empty))
        idx = self.tabs.addTab(tab, ctl.title)
        self.tabs.setCurrentIndex(idx)
        tab.canvas.setFocus()
        return tab

    def _refresh_tab_titles(self):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, NoteTab):
                self.tabs.setTabText(i, w.ctl.title + (" •" if w.ctl.dirty else ""))
        self._update_title()

    def close_tab(self, index: int) -> None:
        w = self.tabs.widget(index)
        if not isinstance(w, NoteTab):
            return
        if not w.ctl.save():
            return
        self.tabs.removeTab(index)
        w.deleteLater()
        if not self.note_tabs():
            self.tabs.addTab(self.empty, "Accueil")
            self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition.RightSide, None)

    def save(self) -> None:
        if tab := self.current_tab():
            if tab.ctl.save():
                self.statusBar().showMessage("Enregistré", 2000)

    def _on_tab_changed(self):
        self._update_title()

    def _update_title(self) -> None:
        tab = self.current_tab()
        name = tab.ctl.title if tab else "Plume"
        self.setWindowTitle(f"{name} — Plume" if tab else "Plume")

    def closeEvent(self, event):
        for tab in self.note_tabs():
            if not tab.ctl.save():
                event.ignore()
                return
        self.config.save()
        super().closeEvent(event)

    # ----- divers -----
    def toggle_fullscreen(self) -> None:
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def show_tablet_debug(self) -> None:
        from .debug_tablet import TabletDebugWindow
        self._debug = TabletDebugWindow()
        self._debug.show()
