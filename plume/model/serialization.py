"""Format .plume : archive ZIP = document.json (versionné) + assets/ + source.pdf.

Lecture défensive (fichier non fiable) : noms d'entrées en liste blanche, rien
n'est extrait sur disque, tailles plafonnées, JSON validé champ par champ.
Écriture atomique : fichier temporaire du même dossier, fsync, puis os.replace.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import zipfile
from pathlib import Path

from .document import BACKGROUNDS, Document, Page
from .elements import SHAPE_KINDS, TOOLS, ImageItem, Shape, Stroke

FORMAT_VERSION = 1
DOC_NAME = "document.json"
PDF_NAME = "source.pdf"
ASSET_RE = re.compile(r"^assets/[0-9a-f]{8,64}\.(png|jpg|jpeg|webp)$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{8}$")

MAX_JSON = 256 * 2**20
MAX_ASSET = 64 * 2**20
MAX_PDF = 512 * 2**20
MAX_TOTAL = 1024 * 2**20


class PlumeFormatError(ValueError):
    """Fichier .plume illisible, corrompu ou d'une version future."""


# ---------- écriture ----------

def _r(v: float) -> float:
    return round(float(v), 2)


def _element_to_dict(e) -> dict:
    if isinstance(e, Stroke):
        return {"id": e.id, "type": "stroke", "tool": e.tool, "color": e.color, "width": _r(e.width),
                "points": [[_r(x), _r(y), round(p, 3), _r(t)] for x, y, p, t in e.points]}
    if isinstance(e, Shape):
        return {"id": e.id, "type": "shape", "kind": e.kind, "color": e.color, "width": _r(e.width),
                "rotation": _r(e.rotation), "geometry": [[_r(x), _r(y)] for x, y in e.geometry]}
    return {"id": e.id, "type": "image", "asset": e.asset, "rect": [_r(v) for v in e.rect],
            "rotation": _r(e.rotation), "crop": [round(v, 4) for v in e.crop]}


def to_dict(doc: Document) -> dict:
    return {
        "format_version": FORMAT_VERSION,
        "app": "plume",
        "metadata": {"title": doc.title, "created": doc.created, "modified": doc.modified},
        "source_pdf": PDF_NAME if doc.source_pdf else None,
        "pages": [{
            "id": p.id, "width": _r(p.width), "height": _r(p.height), "background": p.background,
            "highlights": [_element_to_dict(e) for e in p.highlights],
            "images": [_element_to_dict(e) for e in p.images],
            "ink": [_element_to_dict(e) for e in p.ink],
            "shapes": [_element_to_dict(e) for e in p.shapes],
        } for p in doc.pages],
    }


def atomic_write(path: str | os.PathLike, write) -> None:
    """Appelle write(fichier_binaire) sur un temporaire, puis remplace path d'un coup."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            write(fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def save(doc: Document, path: str | os.PathLike) -> None:
    payload = json.dumps(to_dict(doc), ensure_ascii=False, separators=(",", ":")).encode()

    def write(fh):
        with zipfile.ZipFile(fh, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(DOC_NAME, payload)
            for name, data in doc.assets.items():
                z.writestr(name, data, compress_type=zipfile.ZIP_STORED)  # déjà compressées
            if doc.source_pdf:
                z.writestr(PDF_NAME, doc.source_pdf)

    atomic_write(path, write)


# ---------- lecture ----------

def _num(v, what: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or abs(v) > 1e7:
        raise PlumeFormatError(f"nombre invalide pour {what}")
    return float(v)


def _color(v) -> str:
    if not isinstance(v, str) or not COLOR_RE.match(v):
        raise PlumeFormatError(f"couleur invalide : {v!r}")
    return v.lower()


def _id(d) -> str:
    v = d.get("id")
    if not isinstance(v, str) or not 0 < len(v) <= 64:
        raise PlumeFormatError("identifiant d'élément invalide")
    return v


def _stroke(d: dict) -> Stroke:
    if d.get("tool") not in TOOLS:
        raise PlumeFormatError(f"outil inconnu : {d.get('tool')!r}")
    pts = d.get("points")
    if not isinstance(pts, list) or not pts:
        raise PlumeFormatError("trait sans points")
    points = []
    for p in pts:
        if not isinstance(p, list) or len(p) != 4:
            raise PlumeFormatError("point de trait invalide")
        points.append(tuple(_num(v, "point") for v in p))
    return Stroke(points=points, color=_color(d.get("color")), width=_num(d.get("width"), "épaisseur"),
                  tool=d["tool"], id=_id(d))


def _shape(d: dict) -> Shape:
    if d.get("kind") not in SHAPE_KINDS:
        raise PlumeFormatError(f"forme inconnue : {d.get('kind')!r}")
    geo = d.get("geometry")
    if not isinstance(geo, list) or not geo or any(not isinstance(p, list) or len(p) != 2 for p in geo):
        raise PlumeFormatError("géométrie de forme invalide")
    return Shape(kind=d["kind"], geometry=[(_num(x, "x"), _num(y, "y")) for x, y in geo],
                 color=_color(d.get("color")), width=_num(d.get("width"), "épaisseur"),
                 rotation=_num(d.get("rotation", 0), "rotation"), id=_id(d))


def _image(d: dict, assets: dict) -> ImageItem:
    asset = d.get("asset")
    if asset not in assets:
        raise PlumeFormatError(f"image manquante dans l'archive : {asset!r}")
    rect, crop = d.get("rect"), d.get("crop", [0, 0, 1, 1])
    if not isinstance(rect, list) or len(rect) != 4 or not isinstance(crop, list) or len(crop) != 4:
        raise PlumeFormatError("cadre d'image invalide")
    return ImageItem(asset=asset, rect=tuple(_num(v, "cadre") for v in rect),
                     rotation=_num(d.get("rotation", 0), "rotation"),
                     crop=tuple(_num(v, "recadrage") for v in crop), id=_id(d))


def _layer(page: dict, name: str, parse, kind: str) -> list:
    items = page.get(name, [])
    if not isinstance(items, list) or any(not isinstance(e, dict) or e.get("type") != kind for e in items):
        raise PlumeFormatError(f"calque {name} invalide")
    return [parse(e) for e in items]


def from_dict(data: dict, assets: dict[str, bytes] | None = None, source_pdf: bytes | None = None) -> Document:
    assets = assets or {}
    if not isinstance(data, dict):
        raise PlumeFormatError("document.json n'est pas un objet")
    version = data.get("format_version")
    if not isinstance(version, int) or version < 1:
        raise PlumeFormatError("format_version absent ou invalide")
    if version > FORMAT_VERSION:
        raise PlumeFormatError(f"note créée par une version plus récente de Plume (format {version})")
    meta = data.get("metadata") or {}
    pages = []
    for p in data.get("pages") or []:
        if not isinstance(p, dict):
            raise PlumeFormatError("page invalide")
        bg = p.get("background") or {"kind": "blank"}
        if not isinstance(bg, dict) or bg.get("kind") not in BACKGROUNDS:
            raise PlumeFormatError(f"fond de page inconnu : {bg!r}")
        if bg["kind"] == "pdf" and (source_pdf is None or not isinstance(bg.get("pdf_page"), int)):
            raise PlumeFormatError("page PDF sans PDF source")
        pages.append(Page(
            width=_num(p.get("width"), "largeur"), height=_num(p.get("height"), "hauteur"),
            background=dict(bg), id=_id(p),
            highlights=_layer(p, "highlights", _stroke, "stroke"),
            images=_layer(p, "images", lambda d: _image(d, assets), "image"),
            ink=_layer(p, "ink", _stroke, "stroke"),
            shapes=_layer(p, "shapes", _shape, "shape"),
        ))
    if not pages:
        raise PlumeFormatError("note sans page")
    ids = [p.id for p in pages] + [e.id for p in pages for e in p.elements()]
    if len(ids) != len(set(ids)):
        raise PlumeFormatError("identifiants en double")
    return Document(pages=pages, title=str(meta.get("title", "")), created=str(meta.get("created", "")),
                    modified=str(meta.get("modified", "")), source_pdf=source_pdf, assets=assets)


def _read(z: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int, budget: list[int]) -> bytes:
    """Lit une entrée en plafonnant sa taille ET le total réellement décompressé (budget partagé)."""
    limit = min(limit, budget[0])
    if info.file_size > limit:
        raise PlumeFormatError(f"entrée trop volumineuse : {info.filename}")
    with z.open(info) as fh:
        data = fh.read(limit + 1)  # ne fait pas confiance à la taille déclarée
    if len(data) > limit:
        raise PlumeFormatError(f"entrée trop volumineuse : {info.filename}")
    budget[0] -= len(data)
    return data


def load(path: str | os.PathLike) -> Document:
    try:
        with zipfile.ZipFile(path) as z:
            infos = {i.filename: i for i in z.infolist() if not i.is_dir()}
            if DOC_NAME not in infos:
                raise PlumeFormatError("document.json absent")
            budget = [MAX_TOTAL]
            data = json.loads(_read(z, infos[DOC_NAME], MAX_JSON, budget))
            assets = {n: _read(z, i, MAX_ASSET, budget) for n, i in infos.items() if ASSET_RE.match(n)}
            pdf = _read(z, infos[PDF_NAME], MAX_PDF, budget) if PDF_NAME in infos else None
            # Toute autre entrée (y compris « ../ ») est ignorée : rien n'est extrait sur disque.
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, EOFError) as exc:
        raise PlumeFormatError(f"fichier .plume corrompu ({exc.__class__.__name__})") from exc
    return from_dict(data, assets, pdf)
