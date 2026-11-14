"""Paramètres de Plume (enregistrés dans ~/.config/plume/config.json)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QLineEdit, QPushButton, QSlider, QSpinBox, QWidget)

from ..engine.pressure import PressureCurve
from . import style
from .pages_panel import BACKGROUNDS


class CurvePreview(QWidget):
    """Courbe de pression : pression du stylet (x) → épaisseur du trait (y)."""

    def __init__(self):
        super().__init__()
        self.curve = PressureCurve()
        self.setFixedSize(140, 90)

    def paintEvent(self, _):
        c = style.colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(c["surface"]))
        p.setPen(QPen(QColor(c["border"]), 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        path = QPainterPath()
        w, h = self.width() - 12, self.height() - 12
        for i in range(41):
            x = i / 40
            pt = QPointF(6 + x * w, 6 + h - float(self.curve(x)) * h)
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        p.setPen(QPen(QColor(c["accent"]), 2))
        p.drawPath(path)


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Paramètres")
        form = QFormLayout(self)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self.vault = QLineEdit(config.vault_path)
        browse = QPushButton("Parcourir…")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.vault, 1)
        row.addWidget(browse)
        form.addRow("Dossier des notes (vault)", row)

        self.sens = QSlider(Qt.Orientation.Horizontal)
        self.sens.setRange(0, 100)
        self.sens.setValue(int(config.pressure_sensitivity * 100))
        self.preview = CurvePreview()
        self.sens.valueChanged.connect(self._curve_changed)
        sens_row = QHBoxLayout()
        sens_row.addWidget(self.sens, 1)
        sens_row.addWidget(self.preview)
        form.addRow("Sensibilité à la pression\n(gauche : appuyer fort, droite : très sensible)", sens_row)
        self._curve_changed(self.sens.value())

        self.bg = QComboBox()
        for key, label in BACKGROUNDS:
            self.bg.addItem(label, key)
        self.bg.setCurrentIndex(max(0, self.bg.findData(config.default_background)))
        form.addRow("Fond des nouvelles pages", self.bg)

        self.side = QComboBox()
        self.side.addItem("Gomme", "eraser")
        self.side.addItem("Lasso", "lasso")
        self.side.setCurrentIndex(max(0, self.side.findData(config.side_button_action)))
        form.addRow("Bouton du stylet maintenu", self.side)

        self.checks = {}
        for key, label in (("finger_draws", "Le doigt dessine (sinon il fait défiler)"),
                           ("hover_dot", "Point discret sous la pointe en survol"),
                           ("shape_recognition", "Formes auto-corrigées (maintenir le stylet immobile)"),
                           ("straight_highlighter", "Surligneur droit"),
                           ("companion_pdf", "Créer NomDeLaNote.pdf à chaque sauvegarde (pour Obsidian)")):
            cb = QCheckBox(label)
            cb.setChecked(bool(getattr(config, key)))
            self.checks[key] = cb
            form.addRow("", cb)

        self.autosave = QSpinBox()
        self.autosave.setRange(1, 60)
        self.autosave.setSuffix(" s")
        self.autosave.setValue(max(1, config.autosave_delay_ms // 1000))
        form.addRow("Sauvegarde automatique après", self.autosave)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Dossier des notes", self.vault.text())
        if folder:
            self.vault.setText(folder)

    def _curve_changed(self, value: int):
        self.preview.curve = PressureCurve.from_sensitivity(value / 100)
        self.preview.update()

    def apply(self) -> None:
        c = self.config
        c.vault_path = self.vault.text().strip()
        c.pressure_sensitivity = self.sens.value() / 100
        curve = PressureCurve.from_sensitivity(c.pressure_sensitivity)
        c.pressure_curve = [[float(x), float(y)] for x, y in zip(curve.x, curve.y)]
        c.default_background = self.bg.currentData()
        c.side_button_action = self.side.currentData()
        for key, cb in self.checks.items():
            setattr(c, key, cb.isChecked())
        c.autosave_delay_ms = self.autosave.value() * 1000
        c.save()
