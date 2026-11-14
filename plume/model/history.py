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


class History:
    def __init__(self, doc: Document):
        self.doc = doc
        self._undo: list[Command] = []
        self._redo: list[Command] = []

    def push(self, cmd: Command) -> set[str]:
        """Exécute la commande et l'enregistre ; vide la pile « rétablir »."""
        touched = cmd.do(self.doc)
        self._undo.append(cmd)
        self._redo.clear()
        return touched

    def undo(self) -> set[str]:
        if not self._undo:
            return set()
        cmd = self._undo.pop()
        self._redo.append(cmd)
        return cmd.undo(self.doc)

    def redo(self) -> set[str]:
        if not self._redo:
            return set()
        cmd = self._redo.pop()
        self._undo.append(cmd)
        return cmd.do(self.doc)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)
