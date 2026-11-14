"""Annuler / rétablir illimité (pattern Command).

Chaque commande renvoie l'ensemble des pages qu'elle touche, pour que la vue
n'invalide que leurs caches.
"""
from __future__ import annotations

from .document import Document, Page
from .elements import Element


class Command:
    def do(self, doc: Document) -> set[str]:
        raise NotImplementedError

    def undo(self, doc: Document) -> set[str]:
        raise NotImplementedError


class AddElements(Command):
    def __init__(self, page_id: str, elements: list[Element]):
        self.page_id, self.elements = page_id, list(elements)

    def do(self, doc):
        page = doc.page(self.page_id)
        for e in self.elements:
            page.add(e)
        return {self.page_id}

    def undo(self, doc):
        page = doc.page(self.page_id)
        for e in reversed(self.elements):
            page.remove(e)
        return {self.page_id}


class RemoveElements(Command):
    def __init__(self, page_id: str, elements: list[Element]):
        self.page_id, self.elements = page_id, list(elements)
        self._indices: list[int] = []

    def do(self, doc):
        page = doc.page(self.page_id)
        self._indices = [page.remove(e) for e in self.elements]
        return {self.page_id}

    def undo(self, doc):
        page = doc.page(self.page_id)
        # Réinsère dans l'ordre inverse pour retrouver les indices d'origine.
        for e, i in reversed(list(zip(self.elements, self._indices))):
            page.add(e, i)
        return {self.page_id}


class ReplaceElements(Command):
    """Remplace des éléments par d'autres (gomme partielle, forme reconnue, lasso)."""

    def __init__(self, page_id: str, old: list[Element], new: list[Element]):
        self._remove = RemoveElements(page_id, old)
        self._add = AddElements(page_id, new)

    def do(self, doc):
        return self._remove.do(doc) | self._add.do(doc)

    def undo(self, doc):
        return self._add.undo(doc) | self._remove.undo(doc)


class AddPage(Command):
    def __init__(self, index: int, page: Page | None = None):
        self.index, self.page = index, page or Page()

    def do(self, doc):
        doc.pages.insert(self.index, self.page)
        return {self.page.id}

    def undo(self, doc):
        doc.pages.remove(self.page)
        return {self.page.id}


class RemovePage(Command):
    def __init__(self, page: Page):
        self.page, self.index = page, 0

    def do(self, doc):
        self.index = doc.pages.index(self.page)
        doc.pages.remove(self.page)
        return {self.page.id}

    def undo(self, doc):
        doc.pages.insert(self.index, self.page)
        return {self.page.id}


class MovePage(Command):
    def __init__(self, src: int, dst: int):
        self.src, self.dst = src, dst

    def do(self, doc):
        doc.pages.insert(self.dst, doc.pages.pop(self.src))
        return {doc.pages[self.dst].id}

    def undo(self, doc):
        doc.pages.insert(self.src, doc.pages.pop(self.dst))
        return {doc.pages[self.src].id}


class SetBackground(Command):
    def __init__(self, pages: list[Page], background: dict):
        self.pages, self.new = list(pages), dict(background)
        self.old = [dict(p.background) for p in self.pages]

    def do(self, doc):
        for p in self.pages:
            p.background = dict(self.new)
        return {p.id for p in self.pages}

    def undo(self, doc):
        for p, bg in zip(self.pages, self.old):
            p.background = bg
        return {p.id for p in self.pages}


class Group(Command):
    """Plusieurs commandes annulées d'un coup (ex. un geste de gomme)."""

    def __init__(self, commands: list[Command]):
        self.commands = commands

    def do(self, doc):
        touched: set[str] = set()
        for c in self.commands:
            touched |= c.do(doc)
        return touched

    def undo(self, doc):
        touched: set[str] = set()
        for c in reversed(self.commands):
            touched |= c.undo(doc)
        return touched


class History:
    def __init__(self, doc: Document):
        self.doc = doc
        self._undo: list[Command] = []
        self._redo: list[Command] = []
        self._group: list[Command] | None = None
        self.revision = 0  # change à chaque modification : sert à savoir s'il faut sauvegarder

    def push(self, cmd: Command) -> set[str]:
        """Exécute la commande et l'enregistre ; vide la pile « rétablir »."""
        touched = cmd.do(self.doc)
        if self._group is not None:
            self._group.append(cmd)
        else:
            self._undo.append(cmd)
        self._redo.clear()
        self.revision += 1
        return touched

    def begin_group(self) -> None:
        self.end_group()
        self._group = []

    def end_group(self) -> None:
        group, self._group = self._group, None
        if group:
            self._undo.append(group[0] if len(group) == 1 else Group(group))

    def undo(self) -> set[str]:
        self.end_group()
        if not self._undo:
            return set()
        cmd = self._undo.pop()
        self._redo.append(cmd)
        self.revision += 1
        return cmd.undo(self.doc)

    def redo(self) -> set[str]:
        self.end_group()
        if not self._redo:
            return set()
        cmd = self._redo.pop()
        self._undo.append(cmd)
        self.revision += 1
        return cmd.do(self.doc)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)
