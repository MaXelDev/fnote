from fnote.model.document import Document, Page
from fnote.model.elements import ImageItem, Shape, Stroke
from fnote.model.history import AddElements, AddPage, History, RemoveElements, ReplaceElements


def stroke(tool="fountain", x=10.0):
    return Stroke(points=[(x, 10.0, 0.5, 0.0), (x + 20, 30.0, 0.6, 8.0)], tool=tool)


def test_layers_and_render_order():
    page = Page()
    ink, hl = stroke(), stroke("highlighter")
    img = ImageItem(asset="assets/a.png", rect=(0, 0, 10, 10))
    shp = Shape(kind="rect", geometry=[(0, 0), (5, 0), (5, 5), (0, 5)])
    for e in (shp, ink, img, hl):
        page.add(e)
    assert page.highlights == [hl] and page.ink == [ink]
    # fond → surlignages → images → encre → formes
    assert list(page.elements()) == [hl, img, ink, shp]


def test_bounds_include_half_width():
    s = Stroke(points=[(10, 10, 1, 0), (20, 30, 1, 1)], width=4)
    assert s.bounds() == (8, 8, 22, 32)


def test_undo_redo_add_and_remove():
    doc = Document()
    h = History(doc)
    page = doc.pages[0]
    a, b = stroke(x=1), stroke(x=2)
    assert h.push(AddElements(page.id, [a, b])) == {page.id}
    h.push(RemoveElements(page.id, [a]))
    assert page.ink == [b]
    h.undo()
    assert page.ink == [a, b]  # réinséré à sa place d'origine
    h.undo()
    assert page.ink == [] and not h.can_undo
    h.redo()
    h.redo()
    assert page.ink == [b] and not h.can_redo


def test_new_action_clears_redo():
    doc = Document()
    h = History(doc)
    pid = doc.pages[0].id
    h.push(AddElements(pid, [stroke()]))
    h.undo()
    h.push(AddElements(pid, [stroke()]))
    assert not h.can_redo


def test_replace_and_add_page():
    doc = Document()
    h = History(doc)
    pid = doc.pages[0].id
    old, new1, new2 = stroke(x=1), stroke(x=2), stroke(x=3)
    h.push(AddElements(pid, [old]))
    h.push(ReplaceElements(pid, [old], [new1, new2]))
    assert doc.pages[0].ink == [new1, new2]
    h.undo()
    assert doc.pages[0].ink == [old]
    h.push(AddPage(1))
    assert len(doc.pages) == 2
    h.undo()
    assert len(doc.pages) == 1


def test_many_undos_unlimited():
    doc = Document()
    h = History(doc)
    pid = doc.pages[0].id
    for i in range(500):
        h.push(AddElements(pid, [stroke(x=i)]))
    while h.can_undo:
        h.undo()
    assert doc.pages[0].ink == []


def test_group_is_one_undo_step():
    doc = Document()
    h = History(doc)
    pid = doc.pages[0].id
    a, b = stroke(x=1), stroke(x=2)
    h.push(AddElements(pid, [a, b]))
    h.begin_group()
    h.push(RemoveElements(pid, [a]))
    h.push(RemoveElements(pid, [b]))
    h.end_group()
    assert doc.pages[0].ink == []
    h.undo()
    assert doc.pages[0].ink == [a, b]
    h.redo()
    assert doc.pages[0].ink == []


def test_page_commands_and_revision():
    from fnote.model.history import MovePage, RemovePage, SetBackground
    doc = Document(pages=[Page(), Page(), Page()])
    first, second, third = doc.pages
    h = History(doc)
    rev = h.revision
    h.push(MovePage(0, 2))
    assert doc.pages == [second, third, first] and h.revision > rev
    h.push(RemovePage(third))
    assert doc.pages == [second, first]
    h.push(SetBackground([first], {"kind": "grid"}))
    h.undo(); h.undo(); h.undo()
    assert doc.pages == [first, second, third] and first.background == {"kind": "blank"}
