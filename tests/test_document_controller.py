import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402

from fnote.controller.document_controller import DocumentController  # noqa: E402
from fnote.model import serialization  # noqa: E402
from fnote.model.config import Config  # noqa: E402
from fnote.model.document import Document  # noqa: E402
from fnote.model.elements import Stroke  # noqa: E402
from fnote.model.history import AddElements  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def test_autosave_after_delay(tmp_path):
    path = tmp_path / "n.fnote"
    ctl = DocumentController(Document(), path, Config(autosave_delay_ms=500))
    ctl.history.push(AddElements(ctl.doc.pages[0].id, [Stroke(points=[(1, 1, .5, 0)])]))
    ctl.on_changed()
    assert ctl.dirty and not path.exists()
    wait(200)
    assert not path.exists()  # pas avant le délai
    wait(600)
    assert path.exists() and not ctl.dirty
    assert len(serialization.load(path).pages[0].ink) == 1


def test_after_save_hooks(tmp_path):
    calls = []
    ctl = DocumentController(Document(), tmp_path / "h.fnote", Config())
    ctl.after_save.append(calls.append)
    assert ctl.save() and calls == [ctl]
