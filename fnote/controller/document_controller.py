"""Une note ouverte : document, historique, fichier, sauvegarde automatique."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from ..model import serialization
from ..model.document import Document, now_iso
from ..model.history import History


class DocumentController(QObject):
    saved = Signal()
    saveFailed = Signal(str)
    dirtyChanged = Signal(bool)

    def __init__(self, doc: Document, path: Path, config, parent=None):
        super().__init__(parent)
        self.doc, self.path, self.config = doc, Path(path), config
        self.history = History(doc)
        self._saved_revision = 0
        self._timer = QTimer(self, singleShot=True, timeout=self.save)
        self.after_save = []  # crochets f(controller) : export PDF compagnon…

    @classmethod
    def open(cls, path: Path, config, parent=None) -> "DocumentController":
        return cls(serialization.load(path), path, config, parent)

    @property
    def dirty(self) -> bool:
        return self.history.revision != self._saved_revision

    @property
    def title(self) -> str:
        return self.path.stem

    def on_changed(self):
        """Appelé après chaque modification : relance le minuteur de sauvegarde auto."""
        self.dirtyChanged.emit(self.dirty)
        self._timer.start(max(500, self.config.autosave_delay_ms))

    def save(self) -> bool:
        self._timer.stop()
        if not self.dirty and self.path.exists():
            return True
        try:
            self.doc.modified = now_iso()
            if not self.doc.title:
                self.doc.title = self.path.stem
            serialization.save(self.doc, self.path)
        except OSError as exc:
            self.saveFailed.emit(f"{self.path.name} : {exc}")
            return False
        self._saved_revision = self.history.revision
        self.dirtyChanged.emit(False)
        self.saved.emit()
        for hook in self.after_save:
            hook(self)
        return True

    def rename_to(self, path: Path) -> None:
        self.path = Path(path)
