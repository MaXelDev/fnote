"""Interface hors écran : barre d'outils, popovers, pages, onglets."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from plume.model.config import Config  # noqa: E402
from plume.model.document import Document, Page  # noqa: E402
from plume.model import serialization  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    from plume.view.main_window import MainWindow
    path = tmp_path / "Cours.plume"
    serialization.save(Document(pages=[Page(), Page()]), path)
    w = MainWindow(Config(vault_path=str(tmp_path)), str(path))
    w.show()
    app.processEvents()
    yield w
    w.close()


def test_tools_switch_and_popovers(window):
    from plume.controller.tools.eraser import EraserTool
    from plume.view.popovers import EraserPopover, HighlighterPopover, PenPopover
    tb = window.toolbar
    tb.buttons["eraser"].click()
    assert window.tools.mode == "eraser"
    assert isinstance(window.current_tab().canvas.tool, EraserTool)
    tb.favorites[2].click()
    assert window.tools.mode == "pen" and window.config.active_favorite == 2
    for cls in (PenPopover, HighlighterPopover, EraserPopover):
        cls(window.tools).close()
    window.tools.update_pen(color="#00838fff", width=3.0)
    assert window.config.favorites[2]["color"] == "#00838fff"


def test_pages_panel_actions(window):
    window.pages_dock.show()
    app.processEvents()
    panel, canvas = window.pages_panel, window.current_tab().canvas
    assert panel.list.count() == 2
    panel.list.setCurrentRow(0)
    panel.insert_page()
    assert len(canvas.doc.pages) == 3 and panel.list.count() == 3
    panel.bg.setCurrentIndex(panel.bg.findData("grid"))
    panel.set_background(all_pages=True)
    assert all(p.background["kind"] == "grid" for p in canvas.doc.pages)
    panel.delete_page()
    assert len(canvas.doc.pages) == 2
    canvas.undo()
    assert len(canvas.doc.pages) == 3


def test_undo_button_state(window):
    window._sync_undo()
    assert not window.toolbar.buttons["undo"].isEnabled()


def test_color_palette_recent(window):
    from plume.view.color_picker import ColorPalette
    pal = ColorPalette(window.config, ["#1a1a1a", "#1f5fd1"], "#1a1a1aff")
    got = []
    pal.colorPicked.connect(got.append)
    pal._pick("#1f5fd1")
    assert got == ["#1f5fd1ff"] and window.config.recent_colors[0] == "#1f5fd1ff"


def test_import_pdf_creates_annotated_note(window, tmp_path):
    import pymupdf
    d = pymupdf.open()
    d.new_page().insert_text((72, 72), "Sujet de TD")
    d.save(tmp_path / "TD1.pdf")
    window.import_pdf(tmp_path / "TD1.pdf")
    tab = window.current_tab()
    assert tab.ctl.path.name == "TD1 (annoté).plume" and tab.canvas.renderer.pdf_source is not None
    assert (tmp_path / "TD1.pdf").exists()
    img = tab.canvas.renderer.render_page(tab.ctl.doc.pages[0], 0.5)
    assert not img.isNull()
