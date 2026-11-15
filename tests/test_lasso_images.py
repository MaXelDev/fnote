"""Lasso (sélection, déplacer, redimensionner, pivoter, actions) et images, sur le canevas hors écran."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402

from fnote.controller import images  # noqa: E402
from fnote.controller.tools.lasso import CLIPBOARD, LassoTool, paste  # noqa: E402
from fnote.model.config import Config  # noqa: E402
from fnote.model.document import Document, Page  # noqa: E402
from fnote.model.elements import ImageItem, Stroke  # noqa: E402
from fnote.model.history import AddElements, History  # noqa: E402
from fnote.view.canvas import Canvas  # noqa: E402
from fnote.view.crop_dialog import combine_crop  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def setup():
    doc = Document(pages=[Page(), Page()])
    s = Stroke(points=[(100, 100, .5, 0), (200, 100, .5, 1)], width=2)
    doc.pages[0].add(s)
    c = Canvas(doc, History(doc), Config())
    c.resize(800, 900)
    c.show()
    app.processEvents()
    tool = LassoTool(c)
    c.set_tool(tool)
    return c, tool, s


def view(c, x, y):
    return c.page_to_view(0, x, y)


def drag(tool, a, b, steps=5):
    tool.press(a, .5, 0)
    for k in range(1, steps + 1):
        tool.move(a + (b - a) * (k / steps), .5, k)
    tool.release(b, .5, steps + 1)


def lasso_all(c, tool):
    pts = [view(c, 80, 80), view(c, 230, 80), view(c, 230, 130), view(c, 80, 130), view(c, 80, 80)]
    tool.press(pts[0], .5, 0)
    for p in pts[1:]:
        tool.move(p, .5, 1)
    tool.release(pts[-1], .5, 2)


def test_select_and_move_then_undo(setup):
    c, tool, s = setup
    lasso_all(c, tool)
    assert [e.id for e in tool.selection] == [s.id] and s.id in c.hidden_ids
    drag(tool, view(c, 150, 100), view(c, 170, 130))
    moved = c.doc.pages[0].ink[0]
    assert moved.id == s.id and abs(moved.points[0][0] - 120) < 0.5 and abs(moved.points[0][1] - 130) < 0.5
    c.undo()
    assert c.doc.pages[0].ink[0].points[0][:2] == (100, 100) and c.hidden_ids == set()


def test_scale_with_ratio_and_rotate(setup):
    c, tool, s = setup
    lasso_all(c, tool)
    x0, y0, x1, y1 = tool.box
    drag(tool, view(c, x1, y1), view(c, x0 + (x1 - x0) * 2, y1))  # coin bas-droit, double la largeur
    e = c.doc.pages[0].ink[0]
    length = e.points[-1][0] - e.points[0][0]
    assert 190 < length < 215 and e.width > 3  # proportions gardées : l'épaisseur suit
    tool.select([e], 0)
    cx = (tool.box[0] + tool.box[2]) / 2
    rh = tool._rotate_handle()
    center = view(c, cx, (tool.box[1] + tool.box[3]) / 2)
    drag(tool, rh, QPointF(center.x() + (rh.y() - center.y()) * -1, center.y()))  # quart de tour
    r = c.doc.pages[0].ink[0]
    assert abs(r.points[0][0] - r.points[-1][0]) < 2  # devenu vertical (aimanté à 90°)


def test_duplicate_delete_copy_paste(setup):
    c, tool, s = setup
    lasso_all(c, tool)
    tool.action("duplicate")
    assert len(c.doc.pages[0].ink) == 2
    tool.action("copy")
    tool.action("delete")
    assert len(c.doc.pages[0].ink) == 1
    assert CLIPBOARD["elements"] and paste(c, tool)
    assert len(c.doc.pages[c.current_page()].ink) >= 1


def test_recolor_and_thicker(setup):
    c, tool, s = setup
    lasso_all(c, tool)
    tool.recolor("#d32f2f")
    assert c.doc.pages[0].ink[0].color == "#d32f2fff"
    tool.action("thicker")
    assert c.doc.pages[0].ink[0].width > 2


def test_add_image_dedup_and_select(setup):
    c, tool, s = setup
    img = QImage(400, 200, QImage.Format.Format_RGB32)
    img.fill(QColor("#ff0000"))
    a = images.add_image(c, img)
    b = images.add_image(c, img)
    assert a.asset == b.asset and len(c.doc.assets) == 1
    page = c.doc.pages[c.current_page()]
    assert sum(isinstance(e, ImageItem) for e in page.images) == 2
    assert images.to_png(QImage()) is None


def test_huge_image_downscaled():
    img = QImage(5000, 100, QImage.Format.Format_RGB32)
    img.fill(QColor("#000000"))
    back = QImage.fromData(images.to_png(img))
    assert back.width() == images.MAX_SIDE


def test_combine_crop():
    assert combine_crop((0, 0, 1, 1), (0.25, 0.5, 0.75, 1)) == (0.25, 0.5, 0.75, 1)
    assert combine_crop((0.5, 0, 1, 0.5), (0, 0, 0.5, 1)) == (0.5, 0, 0.75, 0.5)


def _pen(c, kind, pos, button):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QPointingDevice, QTabletEvent
    dev = QPointingDevice("stylet", 1, QPointingDevice.DeviceType.Stylus, QPointingDevice.PointerType.Pen,
                          QPointingDevice.Capability.Position | QPointingDevice.Capability.Pressure, 1, 3)
    ev = QTabletEvent(getattr(QEvent.Type, kind), dev, QPointF(pos), QPointF(pos), 0.5, 0, 0, 0, 0, 0,
                      Qt.KeyboardModifier.NoModifier, button, button)
    return c.viewportEvent(ev), ev


def test_pen_on_selection_bar_does_not_clear_selection(setup):
    from PySide6.QtCore import Qt
    c, tool, s = setup
    lasso_all(c, tool)
    bar = tool.bar
    assert bar.isVisible()
    b = bar.buttons["delete"]
    centre = QPointF(b.mapTo(c.viewport(), b.rect().center()))
    handled, ev = _pen(c, "TabletPress", centre, Qt.MouseButton.LeftButton)
    assert not handled and not ev.isAccepted()  # laissé au bouton (clic synthétisé par Qt)
    assert tool.selection and bar.isVisible()
    b.click()
    assert c.doc.pages[0].ink == []


def test_tap_selects_object_and_rect_mode(setup):
    c, tool, s = setup
    p = view(c, 150, 100)
    tool.press(p, .5, 0)
    tool.release(p, .5, 1)
    assert [e.id for e in tool.selection] == [s.id]
    c.config.lasso_mode = "rect"
    tool.clear()
    drag(tool, view(c, 90, 90), view(c, 210, 110))
    assert [e.id for e in tool.selection] == [s.id]


def test_side_handle_stretches_one_axis(setup):
    c, tool, s = setup
    lasso_all(c, tool)
    right = tool._side_handles()[1]
    drag(tool, right, right + QPointF(100, 0))
    e = c.doc.pages[0].ink[0]
    assert e.points[-1][0] - e.points[0][0] > 150 and abs(e.points[0][1] - 100) < 1  # plus large, même hauteur


def test_front_back_order(setup):
    c, tool, s = setup
    s2 = Stroke(points=[(100, 120, .5, 0), (200, 120, .5, 1)], width=2)
    c.apply(AddElements(c.doc.pages[0].id, [s2]))
    tool.select([s], 0)
    tool.action("front")
    assert c.doc.pages[0].ink[-1].id == s.id
    tool.action("back")
    assert c.doc.pages[0].ink[0].id == s.id


def test_pen_tap_on_image_selects_it():
    from fnote.controller.tools.ink import InkTool
    doc = Document(pages=[Page()])
    c = Canvas(doc, History(doc), Config())
    c.resize(800, 900)
    c.show()
    app.processEvents()
    img = QImage(200, 100, QImage.Format.Format_RGB32)
    img.fill(QColor("#3366ff"))
    item = images.add_image(c, img)
    c.set_tool(InkTool(c, {"tool": "fountain", "color": "#000000ff", "width": 2.0}))
    got = []
    c.imageTapped.connect(lambda i, it: got.append(it.id))
    x, y, w, h = item.rect
    p = c.page_to_view(0, x + w / 2, y + h / 2)
    c._start(c.tool, p, .5, 0)
    c._finish(p, .5, 1)
    assert got == [item.id] and c.doc.pages[0].ink == []  # pas de point d'encre


def test_long_press_opens_menu_without_ink(setup):
    from fnote.controller.tools.ink import InkTool
    c, _, s = setup
    c.set_tool(InkTool(c, {"tool": "fountain", "color": "#000000ff", "width": 2}))
    got = []
    c.longPressed.connect(lambda i, item, pos: got.append((i, item)))
    n = len(list(c.doc.pages[0].elements()))
    p = view(c, 300, 400)
    c._start(c.tool, p, .5, 0)
    c._move(p + QPointF(2, 1), .5, 1)  # tremblement toléré
    c._long.timeout.emit()
    assert got == [(0, None)] and c._active is None and c._held
    assert len(list(c.doc.pages[0].elements())) == n  # aucun point d'encre
    c._start(c.tool, view(c, 150, 100), .5, 0)  # sur un trait : il est renvoyé pour être sélectionné
    c._long.timeout.emit()
    assert got[-1] == (0, s)


def test_long_press_cancelled_by_movement(setup):
    from fnote.controller.tools.ink import InkTool
    c, _, _ = setup
    c.set_tool(InkTool(c, {"tool": "fountain", "color": "#000000ff", "width": 2}))
    c._start(c.tool, view(c, 300, 400), .5, 0)
    c._move(view(c, 340, 400), .5, 1)
    assert not c._long.isActive()


def test_paste_at_position(setup):
    c, tool, s = setup
    lasso_all(c, tool)
    tool.copy()
    paste(c, tool, at_view=view(c, 300, 500))
    x0, y0, _, _ = tool.selection[0].bounds()
    assert abs(x0 - 300) < 0.5 and abs(y0 - 500) < 0.5
