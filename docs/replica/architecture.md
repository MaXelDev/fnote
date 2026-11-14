# Architecture — Plume

Lit : `recon.md`, `features.csv`, `fixes.md`. Adapté d'un modèle prévu pour le web : pas de SQL, pas d'API HTTP, pas d'auth, pas d'hébergement.
**Ce qui remplace quoi** : le schéma SQL → le **schéma JSON versionné du format `.plume`** ; l'API → les **interfaces entre modèle, vues et contrôleurs** ; les jobs serveur → des **tâches Qt en arrière-plan** (`QThreadPool`).

## 1. Stack

| couche | choix | pourquoi |
|---|---|---|
| langage | Python 3.12+ (3.14 sur la machine cible) | imposé ; NumPy pour les calculs géométriques |
| UI et entrée stylet | PySide6 (Qt 6), `QWidget` + `QPainter` | `QTabletEvent` (pression, inclinaison, proximité) via tablet-v2 sous Wayland ; rendu raster maîtrisé |
| PDF | PyMuPDF (`fitz`) | rendu des pages en fond + export vectoriel (`Page.draw_*`, `show_pdf_page`) en gardant le texte |
| calcul | NumPy | lissage, reconnaissance de formes, tests d'intersection |
| stockage | fichiers `.plume` (ZIP) dans le vault | pas de base cachée (contrainte §2) |
| config | `~/.config/plume/config.json` (`QStandardPaths`/XDG) | lisible, versionnée par un champ `config_version` |
| tests | pytest (+ `pytest-qt` seulement si nécessaire) | tout ce qui ne dépend pas du matériel |
| corbeille | `QFile.moveToTrash` | corbeille système sans dépendance (`send2trash` inutile) |

Pas de `QGraphicsView` : avec des milliers de traits sur 30 pages, une scène d'items Qt coûte cher en mémoire et en mise à jour. Un canevas maison avec cache bitmap par page donne la main sur ce qui est redessiné (règle de fluidité §5).

## 2. Unités et coordonnées

- **Coordonnées de page en points PDF** (1/72 pouce). A4 = 595,28 × 841,89 pt. Avantage : l'export PDF est une copie directe, sans conversion, et un PDF importé garde ses dimensions exactes.
- Pression normalisée 0..1, temps en millisecondes depuis le début du trait.
- Zoom = pixels écran par point, multiplié par `devicePixelRatio` pour les caches (correctif #3 : positions toujours en `QPointF`, jamais arrondies).
- Mise en page continue : les pages s'empilent verticalement avec un espacement fixe ; `Layout` convertit écran ↔ (n° de page, coordonnées de page).

## 3. Schéma du format `.plume` (remplace le SQL)

Un fichier `.plume` est une archive ZIP :

```
NomDeLaNote.plume
├── document.json        # obligatoire
├── assets/<sha1>.png    # images insérées (nom = hash du contenu, dédupliqué)
└── source.pdf           # PDF importé, optionnel
```

`document.json` (version 1) :

```json
{
  "format_version": 1,
  "app": "plume",
  "metadata": {"title": "Analyse TD3", "created": "2026-11-14T18:00:00Z", "modified": "2026-11-14T18:30:00Z"},
  "source_pdf": "source.pdf",
  "pages": [
    {
      "id": "p-3f2a",
      "width": 595.28, "height": 841.89,
      "background": {"kind": "pdf", "pdf_page": 0},
      "highlights": [ {"id": "e-01", "type": "stroke", "tool": "highlighter", "color": "#FFE06680", "width": 14.0,
                       "points": [[72.0, 100.5, 0.5, 0], [140.2, 101.0, 0.5, 16]]} ],
      "images":     [ {"id": "e-02", "type": "image", "asset": "assets/9ab3….png",
                       "rect": [50, 400, 200, 120], "rotation": 0.0, "crop": [0, 0, 1, 1]} ],
      "ink":        [ {"id": "e-03", "type": "stroke", "tool": "fountain", "color": "#1A1A1AFF", "width": 1.6,
                       "points": [[80.1, 200.0, 0.42, 0], [80.9, 201.3, 0.55, 8]]} ],
      "shapes":     [ {"id": "e-04", "type": "shape", "kind": "rect", "color": "#D32F2FFF", "width": 1.6,
                       "geometry": [[60, 300], [300, 300], [300, 360], [60, 360]], "rotation": 0.0} ]
    }
  ]
}
```

Règles (équivalent des contraintes SQL) :
- `format_version` obligatoire ; lecture d'une version **supérieure** = refus avec message clair (jamais d'écrasement) ; version inférieure = migration en mémoire (`serialization.MIGRATIONS[n]`).
- `background.kind` ∈ `blank | lined | grid | dots | pdf` ; `pdf_page` requis si `pdf`, et `source_pdf` doit exister dans l'archive.
- `tool` ∈ `fountain | ballpoint | pencil | highlighter` ; `shape.kind` ∈ `line | rect | ellipse | triangle | arrow`.
- `color` = `#RRGGBBAA` ; `points` = liste de `[x, y, pression, t]`, au moins 1 point ; nombres arrondis à 2 décimales à l'écriture (taille de fichier).
- Ordre de rendu **fixe** : fond → `highlights` → `images` → `ink` → `shapes` (le surligneur toujours sous l'encre).
- `id` unique dans le document (sert à l'undo et au lasso).

**Sécurité de lecture** (archive non fiable) : on ne lit que les noms attendus (`document.json`, `assets/<hex>.<ext>`, `source.pdf`), jamais d'extraction sur disque (pas de *zip slip*), taille décompressée plafonnée (anti *zip bomb*), JSON validé champ par champ avant construction du modèle.

**Sauvegarde atomique** : écriture de l'archive complète dans `.<nom>.plume.tmp` du même dossier → `fsync` → `os.replace`. Un crash laisse soit l'ancien fichier, soit le nouveau, jamais un fichier tronqué.

## 4. Interfaces modèle ↔ vues ↔ contrôleurs (remplace l'API)

### Modèle (`plume/model/`, sans dépendance Qt sauf exception notée)

| module | interface publique | rôle |
|---|---|---|
| `elements.py` | `Stroke`, `Shape`, `ImageItem` (dataclasses) ; `bounds() -> (x0, y0, x1, y1)` ; `translated(dx, dy)` | données pures |
| `document.py` | `Document(pages, metadata, source_pdf)` ; `Page(width, height, background, highlights, images, ink, shapes)` ; `Page.layer_for(element)` ; `Page.add/remove(element)` ; `Document.add_page(index, page)` | arbre de données |
| `history.py` | `Command` (`do(doc)`, `undo(doc)`, `pages_touched`) ; `History.push(cmd)`, `undo()`, `redo()`, `can_undo/can_redo` ; commandes `AddElements`, `RemoveElements`, `ReplaceElements`, `AddPage`, `MovePage`… | undo illimité ; chaque commande renvoie les pages modifiées pour invalider leurs caches |
| `serialization.py` | `load(path) -> Document` ; `save(doc, path)` (atomique) ; `to_dict` / `from_dict` | format `.plume` |
| `config.py` | `Config.load()`, `Config.save()`, champs typés avec valeurs par défaut | paramètres |

### Moteur (`plume/engine/`, NumPy, sans Qt)

| module | interface |
|---|---|
| `pressure.py` | `PressureCurve(points)` ; `apply(p) -> width_factor` (courbe réglable, interpolée) |
| `smoothing.py` | `StreamSmoother.add(point) -> point lissé` (filtre léger sur les derniers points, sans retard visible) ; `finalize(points) -> points` (Catmull-Rom au lever) |
| `geometry.py` | `stroke_outline(points, width, curve) -> polygone` (contour du trait à pression : sert au rendu ET à l'export PDF) ; `segment_hits(stroke, a, b, radius)` (gomme, correctif #4) ; `split_stroke(...)` (gomme partielle) |
| `shape_recognition.py` | `recognize(points) -> Shape | None` |
| `ruler.py` (phase 4) | `snap(point, ruler) -> point` |

### Vues (`plume/view/`, Qt)

| module | interface | règles |
|---|---|---|
| `canvas.py` | `Canvas(QWidget)` ; `set_document(doc)` ; `zoom`, `scroll` ; signaux `zoomChanged`, `pageChanged` ; `invalidate(page_ids)` | ne peint que les pages visibles ; trait en cours dessiné à part et `update(rect)` du seul dernier segment |
| `page_renderer.py` | `PageCache.get(page, zoom) -> QImage` ; `bake(page, element)` (ajoute un trait fini sans tout repeindre) ; rendu complet en tâche de fond | cache par page ; au zoom : image mise à l'échelle d'abord, nette ensuite (correctif #1) |
| `toolbar.py` | `Toolbar(QToolBar)` ; signal `toolSelected(ToolSpec)` | une seule barre (correctif #6) ; gros boutons |
| `color_picker.py`, `ruler.py`, `vault_browser.py` | widgets | phases 2, 4, 6 |
| `debug_tablet.py` | `TabletDebugWindow` | phase 0 |

### Contrôleurs (`plume/controller/`)

| module | interface | rôle |
|---|---|---|
| `input_router.py` | `InputRouter(QObject)` installé comme **filtre d'événements sur `QApplication`** ; signaux `penProximity(bool)` | tablette → outil actif ; tactile → défilement/zoom ; rejet de la paume ; curseur caché en proximité ; souris ignorée quand le stylet est proche (correctif #2) |
| `tools/base.py` | `Tool` : `press(pos, pressure, t)`, `move(...)`, `release(...)`, `paint_preview(painter)` | interface commune |
| `tools/pen.py`, `highlighter.py`, `eraser.py`, `lasso.py`, `shape.py`, `image.py` | implémentent `Tool` | produisent des `Command` poussées dans `History` |
| `document_controller.py` | `open(path)`, `save()`, sauvegarde auto (`QTimer` à 3 s d'inactivité) | relie modèle, vue et disque |

Flux d'un trait : `QTabletEvent` → `InputRouter` → `PenTool.move()` (lissage + aperçu incrémental) → `release()` → `History.push(AddElements)` → `PageCache.bake()` → sauvegarde auto programmée.

## 5. Tâches en arrière-plan (remplace les jobs serveur)

| tâche | déclencheur | mécanisme |
|---|---|---|
| rendu net d'une page après zoom | fin de geste / 150 ms sans zoom | `QThreadPool` + `QRunnable`, `QImage` (thread-safe, contrairement à `QPixmap`) |
| rendu du fond PDF | première apparition de la page, changement de zoom | PyMuPDF dans un thread (un `fitz.Document` par thread) |
| sauvegarde auto | 3 s après la dernière modification | thread principal (rapide), sérialisation de l'instantané |
| export PDF compagnon (phase 5) | après chaque sauvegarde si l'option est active | thread de fond sur un instantané du document ; écriture atomique |

## 6. Points délicats

- **Tablette sous Wayland** : les événements de proximité arrivent à `QApplication`, pas au widget → filtre global. Pression et bouton latéral à vérifier avec `--debug-tablet` avant la phase 1.
- **Compression d'événements** : `QGuiApplication.setAttribute(Qt.AA_CompressTabletEvents, False)` avant la création de l'application.
- **HiDPI / mise à l'échelle fractionnaire** : caches à `zoom × devicePixelRatio`, positions flottantes.
- **Atomicité** : `os.replace` dans le même dossier (même système de fichiers) ; jamais d'écriture directe sur le `.plume`.
- **Fichiers non fiables** : ZIP et PDF importés lus de façon défensive (voir §3).
- **Aucun réseau** : test `test_no_network_imports.py` qui analyse l'AST de tout `plume/`.
- **Grosse note** : 30 pages × centaines de traits → seul le visible est peint, caches libérés pour les pages lointaines (LRU).

## 7. Ordre de construction

| jalon | écrans | modules |
|---|---|---|
| Phase 0 — tranche verticale technique | S01 vide, S12, S15 | `app.py`, `model/*`, `serialization`, `config`, `debug_tablet`, test réseau |
| Phase 1 — boucle principale (écrire et retrouver) | S01, S02 minimal | `canvas`, `page_renderer`, `input_router`, `pen`, `smoothing`, `pressure`, `history`, sauvegarde auto |
| Phase 2 — must des outils | S02–S06, S09 | couleurs, favoris, surligneur, gomme, fonds, pages |
| Phase 3 | S07 | lasso, images |
| Phase 4 | S08 | formes, règle |
| Phase 5 | S13, S14 | `pdf/importer`, `pdf/exporter` |
| Phase 6 | S10, S11 | vault, onglets, paramètres, thème, finition |

Les correctifs de `fixes.md` sont intégrés à leur phase (colonne *notes* de la matrice).
