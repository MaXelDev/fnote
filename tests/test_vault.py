"""Vault : renommer/déplacer (onglets et PDF compagnon suivent), corbeille, paramètres, accueil."""
import os
import shutil

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from fnote.engine.pressure import PressureCurve  # noqa: E402
from fnote.model import serialization  # noqa: E402
from fnote.model.config import Config  # noqa: E402
from fnote.model.document import Document  # noqa: E402
from fnote.pdf.exporter import export_to_file  # noqa: E402
from fnote.view import vault_browser as vb  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    vault = tmp_path / "Vault"
    (vault / "Maths").mkdir(parents=True)
    note = vault / "Cours.fnote"
    serialization.save(Document(), note)
    export_to_file(Document(), PressureCurve(), vault / "Cours.pdf")  # compagnon produit par FNote
    trash = tmp_path / "Trash"
    trash.mkdir()

    class FakeQFile:
        @staticmethod
        def moveToTrash(path):
            shutil.move(path, trash / os.path.basename(path))
            return True
    monkeypatch.setattr(vb, "QFile", FakeQFile)
    monkeypatch.setattr(vb.QMessageBox, "question", lambda *a, **k: vb.QMessageBox.StandardButton.Yes)
    from fnote.view.main_window import MainWindow
    w = MainWindow(Config(vault_path=str(vault)), str(note))
    w.show()
    app.processEvents()
    yield w, vault, trash
    w.close()


def test_move_note_with_companion_and_tab_follows(env):
    w, vault, _ = env
    w.vault_browser.move_paths([vault / "Cours.fnote"], vault / "Maths")
    assert (vault / "Maths" / "Cours.fnote").exists() and (vault / "Maths" / "Cours.pdf").exists()
    assert w.current_tab().ctl.path == (vault / "Maths" / "Cours.fnote").resolve()
    assert w.current_tab().ctl.save()
    assert not (vault / "Cours.fnote").exists()  # pas recréé à l'ancien endroit


def test_rename_folder_updates_open_tab(env):
    w, vault, _ = env
    w.vault_browser.move_paths([vault / "Cours.fnote"], vault / "Maths")
    w.vault_browser._move(vault / "Maths", vault / "Analyse")
    assert w.current_tab().ctl.path == (vault / "Analyse" / "Cours.fnote").resolve()


def test_trash_closes_tab_and_companion(env):
    w, vault, trash = env
    w.vault_browser.trash(vault / "Cours.fnote")
    assert not (vault / "Cours.fnote").exists() and (trash / "Cours.fnote").exists() and (trash / "Cours.pdf").exists()
    assert w.note_tabs() == []


def test_foreign_pdf_never_moved_as_companion(env, tmp_path):
    w, vault, _ = env
    import pymupdf
    d = pymupdf.open()
    d.new_page()
    serialization.save(Document(), vault / "TD.fnote")
    d.save(vault / "TD.pdf")  # PDF d'origine, pas produit par FNote
    w.vault_browser.move_paths([vault / "TD.fnote"], vault / "Maths")
    assert (vault / "TD.pdf").exists() and not (vault / "Maths" / "TD.pdf").exists()


def test_settings_apply(env):
    w, vault, _ = env
    from fnote.view.settings_dialog import SettingsDialog
    dlg = SettingsDialog(w.config, w)
    dlg.sens.setValue(100)
    dlg.checks["finger_draws"].setChecked(True)
    dlg.side.setCurrentIndex(dlg.side.findData("lasso"))
    dlg.apply()
    assert w.config.finger_draws and w.config.side_button_action == "lasso"
    assert w.config.pressure_curve[0][1] > 0.2


def test_welcome_recent(env):
    w, vault, _ = env
    w.empty.refresh()
    assert w.empty.recent.count() == 1 and "Cours" in w.empty.recent.item(0).text()


def test_safe_name():
    assert vb.safe_name(" ../a/b ") == "-a-b" and vb.safe_name(".cache") == "cache"


def test_old_plume_note_keeps_its_companion(tmp_path):
    import pymupdf
    note = tmp_path / "Ancienne.plume"
    serialization.save(Document(), note)
    d = pymupdf.open()
    d.new_page()
    d.set_metadata({"producer": "Plume"})  # PDF compagnon écrit avant le changement de nom
    d.save(tmp_path / "Ancienne.pdf")
    assert vb.companion_of(note) == tmp_path / "Ancienne.pdf"
