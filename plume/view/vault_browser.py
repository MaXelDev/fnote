"""Panneau du vault : arborescence des dossiers, notes .plume et PDF.

Les opérations sur fichiers (renommer, déplacer, supprimer) sont faites ici et
signalées à la fenêtre pour mettre à jour les onglets ouverts. Le PDF compagnon
d'une note (produit par Plume) suit la note.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QDir, QFile, QFileInfo, QSize, Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QFileIconProvider, QFileSystemModel, QInputDialog, QLabel,
                               QMenu, QMessageBox, QPushButton, QTreeView, QVBoxLayout, QWidget)

from . import icons

NOTE_EXT, PDF_EXT = ".plume", ".pdf"


class _Icons(QFileIconProvider):
    def icon(self, info):
        if isinstance(info, QFileInfo):
            if info.isDir():
                return icons.icon("folder")
            if info.suffix().lower() == "plume":
                return icons.icon("note")
            if info.suffix().lower() == "pdf":
                return icons.icon("pdf")
        return super().icon(info)


def companion_of(note: Path) -> Path | None:
    """PDF compagnon d'une note, s'il existe et vient de Plume."""
    from ..pdf.exporter import is_plume_pdf
    pdf = note.with_suffix(PDF_EXT)
    return pdf if note.suffix == NOTE_EXT and pdf.exists() and is_plume_pdf(pdf) else None


def safe_name(name: str) -> str:
    return name.strip().replace("/", "-").replace("\\", "-").lstrip(".")


class VaultTree(QTreeView):
    """Arbre acceptant le glisser-déposer de fichiers vers un dossier."""

    moveRequested = Signal(list, Path)

    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def dragMoveEvent(self, e):
        e.acceptProposedAction()

    def dropEvent(self, e):
        model = self.model()
        idx = self.indexAt(e.position().toPoint())
        target = Path(model.filePath(idx)) if idx.isValid() else Path(model.rootPath())
        if target.is_file():
            target = target.parent
        sources = [Path(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile()]
        if sources:
            self.moveRequested.emit(sources, target)
        e.ignore()  # on déplace nous-mêmes (et on prévient les onglets)


class VaultBrowser(QWidget):
    openNote = Signal(Path)
    importPdf = Signal(Path)
    newNoteIn = Signal(Path)
    pathMoved = Signal(Path, Path)     # ancien chemin → nouveau (fichier ou dossier)
    pathDeleted = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root: Path | None = None
        self.model = QFileSystemModel(self)
        self.model.setIconProvider(_Icons())
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
        self.model.setNameFilters(["*" + NOTE_EXT, "*" + PDF_EXT])
        self.model.setNameFilterDisables(False)
        self.model.setReadOnly(True)

        self.tree = VaultTree()
        self.tree.setModel(self.model)
        for col in (1, 2, 3):
            self.tree.hideColumn(col)
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(20, 20))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.activated.connect(self._activate)
        self.tree.moveRequested.connect(self.move_paths)

        self.empty = QLabel("Aucun vault choisi.")
        self.empty.setObjectName("muted")
        self.empty.setWordWrap(True)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        new_btn = QPushButton("+ Nouvelle note")
        new_btn.clicked.connect(lambda: self.newNoteIn.emit(self._selected_dir()))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(new_btn)
        lay.addWidget(self.tree, 1)
        lay.addWidget(self.empty)
        self.set_root(None)

    def set_root(self, root: Path | None):
        self.root = root
        has = root is not None and root.is_dir()
        self.tree.setVisible(has)
        self.empty.setVisible(not has)
        if has:
            self.model.setRootPath(str(root))
            self.tree.setRootIndex(self.model.index(str(root)))

    # ----- utilitaires -----
    def _path(self, index) -> Path:
        return Path(self.model.filePath(index))

    def _selected_dir(self) -> Path:
        idx = self.tree.currentIndex()
        if not idx.isValid():
            return self.root
        p = self._path(idx)
        return p if p.is_dir() else p.parent

    def _activate(self, index):
        p = self._path(index)
        if p.suffix.lower() == NOTE_EXT:
            self.openNote.emit(p)
        elif p.suffix.lower() == PDF_EXT:
            self.importPdf.emit(p)

    def _menu(self, pos):
        idx = self.tree.indexAt(pos)
        p = self._path(idx) if idx.isValid() else self.root
        if p is None:
            return
        folder = p if p.is_dir() else p.parent
        m = QMenu(self)
        if p.suffix.lower() == NOTE_EXT:
            m.addAction("Ouvrir", lambda: self.openNote.emit(p))
        if p.suffix.lower() == PDF_EXT:
            m.addAction("Annoter ce PDF", lambda: self.importPdf.emit(p))
        m.addAction("Nouvelle note ici…", lambda: self.newNoteIn.emit(folder))
        m.addAction("Nouveau dossier…", lambda: self.new_folder(folder))
        if idx.isValid():
            m.addSeparator()
            m.addAction("Renommer…", lambda: self.rename(p))
            m.addAction("Mettre à la corbeille", lambda: self.trash(p))
        m.exec(self.tree.viewport().mapToGlobal(pos))

    # ----- opérations -----
    def new_folder(self, parent: Path):
        name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom du dossier :")
        name = safe_name(name)
        if ok and name:
            try:
                (parent / name).mkdir()
            except OSError as exc:
                QMessageBox.warning(self, "Impossible de créer le dossier", str(exc))

    def rename(self, p: Path):
        current = p.stem if p.is_file() else p.name
        name, ok = QInputDialog.getText(self, "Renommer", "Nouveau nom :", text=current)
        name = safe_name(name)
        if not ok or not name or name == current:
            return
        target = p.with_name(name + (p.suffix if p.is_file() else ""))
        self._move(p, target)

    def move_paths(self, sources: list, target_dir: Path):
        for src in sources:
            if src.parent == target_dir or target_dir == src or src in target_dir.parents:
                continue  # même dossier, ou dossier déplacé dans lui-même
            self._move(src, target_dir / src.name)

    def _move(self, src: Path, dst: Path):
        if dst.exists():
            QMessageBox.warning(self, "Nom déjà pris", f"« {dst.name} » existe déjà.")
            return
        companion = companion_of(src) if src.is_file() else None
        try:
            shutil.move(str(src), str(dst))
            if companion is not None and not dst.with_suffix(PDF_EXT).exists():
                shutil.move(str(companion), str(dst.with_suffix(PDF_EXT)))
        except OSError as exc:
            QMessageBox.warning(self, "Déplacement impossible", str(exc))
            return
        self.pathMoved.emit(src, dst)

    def trash(self, p: Path, confirm: bool = True):
        if confirm and QMessageBox.question(self, "Mettre à la corbeille",
                                            f"Mettre « {p.name} » à la corbeille ?") != QMessageBox.StandardButton.Yes:
            return
        companion = companion_of(p) if p.is_file() else None
        self.pathDeleted.emit(p)  # les onglets concernés se ferment d'abord
        for target in filter(None, (p, companion)):
            if not QFile.moveToTrash(str(target)):
                QMessageBox.warning(self, "Corbeille indisponible", f"Impossible de mettre « {target.name} » à la corbeille.")
