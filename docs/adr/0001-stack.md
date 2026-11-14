# ADR-0001 : PySide6 + PyMuPDF + format `.plume`

**Statut :** Accepté (stack imposée par le cahier des charges, justifiée ici)
**Date :** 2026-11-14
**Décideurs :** l'utilisateur (propriétaire du projet), Claude (implémentation)

## Contexte

Plume doit offrir une écriture au stylet aussi fluide que Samsung Notes, sur un Galaxy Book 3 360 (numériseur Wacom) sous Fedora / GNOME **Wayland**, 100 % hors ligne, avec des notes rangées dans un vault Obsidian. Les avis analysés (`docs/replica/fixes.md`) montrent que les échecs des alternatives viennent surtout de la **gestion du stylet** (pression ignorée, curseur affiché, décalage à l'échelle 200 %) et de la **latence**. L'utilisateur connaît Python et le pattern MVC.

Contraintes :
- pression, inclinaison, **proximité** du stylet sous Wayland ;
- annoter des PDF et les ré-exporter **en vectoriel** (texte sélectionnable) ;
- licences open source ; aucune bibliothèque réseau ;
- un format de fichier robuste (aucune perte en cas de crash), lisible des années plus tard.

## Décision

1. **UI : PySide6 (Qt 6)**, canevas `QWidget` + `QPainter` maison avec cache bitmap par page.
2. **PDF : PyMuPDF** pour le rendu des fonds et l'export vectoriel.
3. **Format : `.plume` = ZIP** contenant `document.json` versionné (`format_version`), `assets/` et le PDF source, écrit de façon atomique.

## Options envisagées

### UI

| Option | Complexité | Stylet sous Wayland | Perf. du tracé | Familiarité |
|---|---|---|---|---|
| **PySide6 / Qt 6** | Moyenne | `QTabletEvent` natif via tablet-v2 (pression, tilt, proximité) ; vérifié : le stylet `WCOM016C` est listé | Bonne (raster C++, Python seulement pour la logique) | Python ✔ |
| GTK 4 (PyGObject) | Moyenne | Bon (`GdkDevice`, utilisé par Rnote/Xournal++) | Bonne | Python ✔, mais API de dessin moins directe |
| Tauri / Electron (web) | Élevée | Pointer Events : regroupement des événements (« choppy », cf. HN 43884012), pas de proximité fiable | Moyenne | ✘ |
| Rust natif | Élevée | Excellent | Excellente | ✘ (hors compétences) |

**PySide6** retenu : meilleur compromis entre API tablette complète, rendu performant et langage connu. Licence LGPL-3.0, compatible avec une appli MIT utilisée en lien dynamique.

`QGraphicsView` écarté : une scène de milliers d'items sur 30 pages coûte en mémoire et rend difficile le contrôle fin de ce qui est redessiné.

### PDF

| Option | Rendu | Export vectoriel + texte conservé | Licence |
|---|---|---|---|
| **PyMuPDF** | Rapide (MuPDF) | ✔ `show_pdf_page` / dessin vectoriel sur la page d'origine | AGPL-3.0 |
| QtPdf (`QPdfDocument`) | Bon | ✘ (lecture seule) | LGPL |
| pypdf + reportlab | ✘ pas de rendu | ✔ mais deux bibliothèques, rendu absent | BSD |

**PyMuPDF** retenu : seul à couvrir rendu **et** écriture vectorielle. Conséquence de licence : le code de Plume reste MIT, mais **toute distribution qui embarque PyMuPDF est soumise à l'AGPL-3.0** (à rappeler dans le README et la release ; sans effet pour un usage personnel).

### Format de fichier

| Option | Robustesse | Ouverture / débogage | Images et PDF |
|---|---|---|---|
| **ZIP + JSON versionné** | ✔ atomique, validable | ✔ `unzip` + lecture du JSON | ✔ dans l'archive |
| SQLite | ✔ transactions | Moyen | ✔ BLOB, mais un fichier SQLite dans un vault synchronisé se corrompt facilement |
| JSON seul | ✔ | ✔✔ | ✘ base64 lourd |
| SVG / PDF comme format natif | Moyen | ✔ | Perte des données de pression / outils |

**ZIP + JSON** retenu : un seul fichier par note (adapté à un vault), versionné, inspectable, assets dédupliqués par hash.

## Analyse des compromis

- Python est plus lent que Rust ou C++ pour le rendu : on compense par l'**architecture** (dessin incrémental, cache par page, calcul NumPy, tâches de fond) plutôt que par le langage. Si la latence mesurée en phase 1 reste insuffisante, le chemin d'évolution est `QOpenGLWidget` ou un module natif ciblé pour le rendu des traits, sans changer le modèle.
- JSON est plus volumineux qu'un format binaire : on arrondit à 2 décimales et le ZIP compresse ; acceptable pour des notes de cours.

## Conséquences

- ✔ Modèle, format et moteur testables sans matériel (pytest, sans Qt).
- ✔ Export PDF direct : coordonnées de page en points PDF.
- ✘ Licence AGPL héritée de PyMuPDF pour les distributions.
- ✘ Dépendance au support tablet-v2 du compositeur (GNOME Mutter) : à surveiller via `--debug-tablet`.
- À revoir : perf du rendu après mesure en phase 1 (`--debug-perf`) ; migration de format via `MIGRATIONS` dès la version 2.

## Actions

1. [x] Squelette, modèle, `.plume` atomique et sécurisé, diagnostic stylet (phase 0)
2. [ ] Mesurer latence et fps en phase 1 ; décider si `QOpenGLWidget` est nécessaire
3. [ ] Mention de licence AGPL (PyMuPDF) dans README et release (phase 6)
