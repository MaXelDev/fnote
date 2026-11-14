"""Écran d'accueil : premiers pas, actions principales, notes récentes."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
                               QWidget)

from . import icons

LOGO = Path(__file__).resolve().parent.parent / "resources" / "plume.svg"


class Welcome(QWidget):
    action = Signal(str)       # "vault", "new", "open", "import"
    openRecent = Signal(Path)

    def __init__(self, config):
        super().__init__()
        self.config = config
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box = QVBoxLayout()
        box.setSpacing(14)
        logo = QLabel()
        pm = QPixmap(str(LOGO))
        if not pm.isNull():
            logo.setPixmap(pm.scaled(88, 88, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Plume")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("muted")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setWordWrap(True)
        self.subtitle.setFixedWidth(480)
        for w in (logo, title, self.subtitle):
            box.addWidget(w, 0, Qt.AlignmentFlag.AlignHCenter)

        self.vault_btn = QPushButton("Choisir mon dossier de notes")
        self.vault_btn.setDefault(True)
        self.vault_btn.clicked.connect(lambda: self.action.emit("vault"))
        box.addWidget(self.vault_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        row = QHBoxLayout()
        for key, label, icon in (("new", "Nouvelle note", "plus"), ("open", "Ouvrir", "note"),
                                 ("import", "Annoter un PDF", "pdf")):
            b = QPushButton(icons.icon(icon), "  " + label)
            b.setMinimumHeight(44)
            b.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            row.addWidget(b)
            if key == "new":
                b.setDefault(True)
        self.actions_row = QWidget()
        self.actions_row.setLayout(row)
        box.addWidget(self.actions_row)

        self.recent_title = QLabel("Notes récentes")
        self.recent_title.setObjectName("muted")
        self.recent = QListWidget()
        self.recent.setMaximumHeight(220)
        self.recent.setMinimumWidth(460)
        self.recent.itemActivated.connect(lambda it: self.openRecent.emit(Path(it.data(Qt.ItemDataRole.UserRole))))
        self.recent.itemClicked.connect(lambda it: self.openRecent.emit(Path(it.data(Qt.ItemDataRole.UserRole))))
        box.addWidget(self.recent_title)
        box.addWidget(self.recent)
        outer.addLayout(box)
        self.refresh()

    def refresh(self):
        has_vault = bool(self.config.vault_path) and Path(self.config.vault_path).is_dir()
        self.vault_btn.setVisible(not has_vault)
        self.actions_row.setVisible(has_vault)
        self.subtitle.setText(
            "Tes notes manuscrites, au stylet, dans ton vault Obsidian. Tout reste sur ton ordinateur."
            if has_vault else
            "Bienvenue ! Choisis le dossier où ranger tes notes (ton vault Obsidian, par exemple). "
            "Plume n'utilise ni compte ni Internet : tout reste sur ton ordinateur.")
        self.recent.clear()
        recents = [Path(p) for p in self.config.recent_files if Path(p).exists()]
        for p in recents:
            item = QListWidgetItem(icons.icon("note"), f"{p.stem}    —    {p.parent.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.recent.addItem(item)
        self.recent_title.setVisible(bool(recents) and has_vault)
        self.recent.setVisible(bool(recents) and has_vault)
