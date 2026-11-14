"""Export compagnon pour Obsidian : NomDeLaNote.pdf écrit à côté du .plume, en arrière-plan.

Sécurité : on ne remplace jamais un PDF qui n'a pas été produit par Plume (par ex. le
cours d'origine portant le même nom) — on le signale à la place.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from ..model import serialization
from .exporter import export_to_file, is_plume_pdf


class _Signals(QObject):
    done = Signal(str)
    failed = Signal(str)


class _Job(QRunnable):
    def __init__(self, snapshot, curve, target: Path, signals: _Signals):
        super().__init__()
        self.snapshot, self.curve, self.target, self.signals = snapshot, curve, target, signals

    def run(self):
        try:
            export_to_file(self.snapshot, self.curve, self.target)
            self.signals.done.emit(str(self.target))
        except Exception as exc:  # signalé à l'utilisateur, jamais silencieux
            self.signals.failed.emit(f"{self.target.name} : {exc}")


class CompanionExporter(QObject):
    done = Signal(str)
    failed = Signal(str)
    skipped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool.globalInstance()
        self._signals = _Signals()
        self._signals.done.connect(self.done)
        self._signals.failed.connect(self.failed)

    @staticmethod
    def target_for(path: Path) -> Path:
        return Path(path).with_suffix(".pdf")

    def export(self, ctl, curve) -> bool:
        target = self.target_for(ctl.path)
        if target.exists() and not is_plume_pdf(target):
            self.skipped.emit(f"« {target.name} » existe déjà et ne vient pas de Plume : export compagnon ignoré.")
            return False
        # Instantané pris sur le fil principal : le document peut continuer à changer pendant l'export.
        snap = serialization.from_dict(serialization.to_dict(ctl.doc), dict(ctl.doc.assets), ctl.doc.source_pdf)
        self.pool.start(_Job(snap, curve, target, self._signals))
        return True
