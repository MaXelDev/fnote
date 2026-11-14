"""Fenêtre principale : onglets de notes, barre d'outils, menus."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QDockWidget, QFileDialog, QInputDialog, QLabel, QMainWindow, QMenu, QMessageBox,
                               QTabWidget, QVBoxLayout, QWidget)

from ..controller.document_controller import DocumentController
from ..controller.tool_state import ToolState
from ..model import serialization
from ..model.config import Config
from ..model.document import Document
from .canvas import Canvas
from .pages_panel import PagesPanel
from .toolbar import Toolbar


class NoteTab(QWidget):
    """Un onglet = une note ouverte (contrôleur + canevas)."""

    titleChanged = Signal()

    def __init__(self, ctl: DocumentController, tools: ToolState, debug_perf=False):
        super().__init__()
        self.ctl, self.tools = ctl, tools
        pdf = None
        if ctl.doc.source_pdf:
            from ..pdf.source import PdfSource
            pdf = PdfSource(ctl.doc.source_pdf)
        self.canvas = Canvas(ctl.doc, ctl.history, ctl.config, pdf_source=pdf, debug_perf=debug_perf)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas)
        self.canvas.changed.connect(ctl.on_changed)
        ctl.dirtyChanged.connect(lambda *_: self.titleChanged.emit())
        self.apply_tools()

    def apply_tools(self):
        self.canvas.set_tool(self.tools.make_tool(self.canvas))
        if self.canvas.side_tool is not None:
            self.canvas.side_tool.dispose()
        self.canvas.side_tool = self.tools.make_side_tool(self.canvas)


class MainWindow(QMainWindow):
    def __init__(self, config: Config, open_path: str | None = None, debug_perf: bool = False):
        super().__init__()
        self.config = config
        self.debug_perf = debug_perf
        self.tools = ToolState(config)
        self.tools.changed.connect(self._tools_changed)
        self.extra_actions = {}  # actions de barre ajoutées par d'autres modules : nom → f(onglet)
        from ..pdf.companion import CompanionExporter
        self.companion = CompanionExporter(self)
        self.companion.failed.connect(lambda msg: self.statusBar().showMessage(f"Export PDF compagnon impossible : {msg}", 8000))
        self.companion.skipped.connect(lambda msg: self.statusBar().showMessage(msg, 8000))
        self.resize(1200, 860)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.empty = QLabel("Crée une note (Ctrl+N) ou ouvre-en une (Ctrl+O).")
        self.empty.setObjectName("muted")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabs.addTab(self.empty, "Accueil")
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition.RightSide, None)
        self.setCentralWidget(self.tabs)
        self.toolbar = Toolbar(self.tools, self)
        self.toolbar.action.connect(self._toolbar_action)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.pages_panel = PagesPanel()
        self.pages_dock = QDockWidget("Pages", self)
        self.pages_dock.setObjectName("pages")
        self.pages_dock.setWidget(self.pages_panel)
        self.pages_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.pages_dock)
        self.pages_dock.hide()
        self.pages_dock.visibilityChanged.connect(lambda on: self.toolbar.set_checked("pages", on))
        self._build_menus()
        self.menuBar().hide()  # tout passe par la barre d'outils et le bouton « Menu »
        self.tabs.currentChanged.connect(lambda *_: self._on_tab_changed())
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
        self._action(m, "Importer un PDF…", self.import_pdf_dialog, "Ctrl+Shift+I")
        self._action(m, "Exporter en PDF…", self.export_pdf_dialog, "Ctrl+E")
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
        # Raccourcis des outils
        for i in range(len(self.config.favorites)):
            self.addAction(self._shortcut(str(i + 1), lambda i=i: self.tools.set_favorite(i)))
        self.addAction(self._shortcut("P", lambda: self.tools.set_mode("pen")))
        self.addAction(self._shortcut("H", lambda: self.tools.set_mode("highlighter")))
        self.addAction(self._shortcut("E", lambda: self.tools.set_mode("eraser")))
        self.addAction(self._shortcut("L", lambda: self.tools.set_mode("lasso")))
        self.addAction(self._shortcut("R", lambda: self._toolbar_action("ruler")))
        self.addAction(self._shortcut("F9", lambda: self._toolbar_action("sidebar")))
        self._action(e, "Coller", self.paste, QKeySequence.StandardKey.Paste)
        self._action(e, "Copier la sélection", lambda: self._selection("copy"), QKeySequence.StandardKey.Copy)
        self._action(e, "Couper la sélection", lambda: self._selection("cut"), QKeySequence.StandardKey.Cut)
        self._action(e, "Dupliquer la sélection", lambda: self._selection("duplicate"), "Ctrl+D")
        self._action(e, "Supprimer la sélection", lambda: self._selection("delete"), QKeySequence.StandardKey.Delete)
        self._action(e, "Insérer une image…", self.insert_image, "Ctrl+I")
        self.extra_actions["image"] = lambda tab: self.insert_image()
        self.extra_actions["ruler"] = self._toggle_ruler
        # Menu compact (bouton « ⋮ » de la barre)
        self.app_menu = QMenu(self)
        for menu in (m, e, v, h):
            self.app_menu.addMenu(menu)

    def _toolbar_action(self, name: str):
        tab = self.current_tab()
        if name == "undo":
            self.undo()
        elif name == "redo":
            self.redo()
        elif name == "fit":
            self.fit_width()
        elif name == "pages":
            self.pages_dock.setVisible(not self.pages_dock.isVisible())
        elif name == "menu":
            b = self.toolbar.buttons["menu"]
            self.app_menu.exec(b.mapToGlobal(b.rect().bottomLeft()))
        elif name in self.extra_actions:
            self.extra_actions[name](tab)
        self._sync_undo()

    def _toggle_ruler(self, tab):
        if tab is not None:
            tab.canvas.ruler.toggle()
        self.toolbar.set_checked("ruler", bool(tab and tab.canvas.ruler.visible))

    def _lasso(self):
        from ..controller.tools.lasso import LassoTool
        tab = self.current_tab()
        if tab and isinstance(tab.canvas.tool, LassoTool):
            return tab.canvas.tool
        return None

    def _selection(self, key: str):
        if (tool := self._lasso()) is not None:
            tool.action(key)
            self._sync_undo()

    def paste(self):
        """Ctrl+V : sélection copiée dans Plume, sinon image du presse-papiers système."""
        from PySide6.QtWidgets import QApplication
        from ..controller import images
        from ..controller.tools.lasso import CLIPBOARD, MIME_MARK, paste
        tab = self.current_tab()
        if tab is None:
            return
        mime = QApplication.clipboard().mimeData()
        if CLIPBOARD["elements"] and mime is not None and mime.hasFormat(MIME_MARK):
            self.tools.set_mode("lasso")
            paste(tab.canvas, self._lasso())
        elif mime and mime.hasImage():
            images.add_image(tab.canvas, QApplication.clipboard().image())
        self._sync_undo()

    def insert_image(self):
        from ..controller import images
        tab = self.current_tab()
        if tab is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Insérer une image", str(Path.home() / "Images"), images.IMAGE_FILTER)
        if not path:
            return
        img = images.load_file(path)
        if img.isNull() or images.add_image(tab.canvas, img) is None:
            QMessageBox.warning(self, "Image illisible", "Ce fichier n'est pas une image prise en charge (ou dépasse 64 Mo).")
        self._sync_undo()

    def _sync_undo(self):
        tab = self.current_tab()
        h = tab.ctl.history if tab else None
        self.toolbar.set_enabled("undo", bool(h and h.can_undo))
        self.toolbar.set_enabled("redo", bool(h and h.can_redo))

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
        self._sync_undo()

    def redo(self):
        if tab := self.current_tab():
            tab.canvas.redo()
        self._sync_undo()

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
        ctl.after_save.append(self._export_companion)
        tab = NoteTab(ctl, self.tools, self.debug_perf)
        tab.titleChanged.connect(self._refresh_tab_titles)
        tab.canvas.changed.connect(self._sync_undo)
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

    # ----- PDF -----
    def _export_companion(self, ctl):
        if self.config.companion_pdf:
            from ..engine.pressure import PressureCurve
            tab = next((t for t in self.note_tabs() if t.ctl is ctl), None)
            curve = tab.canvas.curve if tab is not None else PressureCurve(self.config.pressure_curve)
            self.companion.export(ctl, curve)

    def import_pdf_dialog(self) -> None:
        start = str(self.vault() or Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Importer un PDF", start, "PDF (*.pdf)")
        if path:
            self.import_pdf(Path(path))

    def import_pdf(self, pdf_path: Path, folder: Path | None = None) -> None:
        """Crée « Nom (annoté).plume » (dans le vault si le PDF est hors du vault) et l'ouvre."""
        from ..pdf.importer import PdfImportError, import_pdf, note_path_for
        try:
            doc = import_pdf(pdf_path)
        except (OSError, PdfImportError) as exc:
            QMessageBox.critical(self, "Import impossible", f"{pdf_path.name} : {exc}")
            return
        vault = self.vault()
        inside = vault is not None and Path(pdf_path).resolve().is_relative_to(vault.resolve())
        target_dir = folder or (Path(pdf_path).parent if inside or vault is None else vault)
        path = note_path_for(target_dir / Path(pdf_path).name)
        doc.title = path.stem
        serialization.save(doc, path)
        self._add_tab(DocumentController(doc, path, self.config))
        self.statusBar().showMessage(f"PDF importé : {path.name}", 4000)

    def export_pdf_dialog(self) -> None:
        tab = self.current_tab()
        if tab is None:
            return
        from ..pdf.exporter import export_to_file
        default = str(tab.ctl.path.with_suffix(".pdf"))
        path, _ = QFileDialog.getSaveFileName(self, "Exporter en PDF", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            export_to_file(tab.ctl.doc, tab.canvas.curve, Path(path))
        except Exception as exc:  # export : on montre l'erreur, rien n'est perdu
            QMessageBox.critical(self, "Export impossible", str(exc))
            return
        self.statusBar().showMessage(f"Exporté : {Path(path).name}", 4000)

    def save(self) -> None:
        if tab := self.current_tab():
            if tab.ctl.save():
                self.statusBar().showMessage("Enregistré", 2000)

    def _on_tab_changed(self):
        tab = self.current_tab()
        self.pages_panel.set_canvas(tab.canvas if tab else None)
        self.toolbar.set_checked("ruler", bool(tab and tab.canvas.ruler.visible))
        self._sync_undo()
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
