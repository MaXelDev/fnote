# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**FNote** : appli de prise de notes manuscrites au stylet (réplique fonctionnelle de Samsung Notes) pour Fedora / GNOME Wayland, sur un Galaxy Book 3 360 (stylet Wacom `WCOM016C`). Cahier des charges complet : `PROMPT_FNote.md` — le relire en cas de doute. Réponses et commits **en français**.

## Commandes

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"   # installation
git config core.hooksPath .githooks     # active le pre-commit (pytest) après un clone
.venv/bin/fnote [note.fnote]            # lancer (Wayland natif, repli xcb)
.venv/bin/fnote --debug-tablet          # diagnostic du stylet (pression, proximité, Hz, échelle)
.venv/bin/pytest -q                     # tous les tests
.venv/bin/pytest tests/test_serialization.py::test_round_trip -q   # un test
QT_QPA_PLATFORM=offscreen .venv/bin/fnote   # démarrage sans écran (smoke test, captures via widget.grab())
python3 ~/.claude/skills/replica-design/contrast.py fnote/resources/tokens.json   # contraste WCAG des tokens
python3 docs/replica/matrice.py         # régénère fonctionnalites.md après modif de features.csv
```

Pour les essais, isoler la config : `XDG_CONFIG_HOME=<scratchpad>/cfg` (sinon on écrit dans le vrai `~/.config/fnote/config.json`).

## Contraintes non négociables

- **100 % hors ligne** : aucun module réseau (`socket`, `urllib`, `requests`, `QtNetwork`, `QtWebEngine`…). `tests/test_no_network.py` analyse l'AST de `fnote/` et échoue sinon.
- **Linux/Wayland uniquement** : pas de code pour Windows/macOS.
- **Les notes vivent dans le vault Obsidian** de l'utilisateur (`Config.vault_path`) ; aucune base cachée ailleurs. Paramètres : `~/.config/fnote/config.json`.
- **Fluidité = critère n°1** (avec le curseur caché pendant l'écriture) : ne jamais redessiner toute la page pendant le tracé ; trait en cours incrémental (`update(rect)` du dernier segment) ; traits finis « cuits » dans un cache bitmap par page ; seules les pages visibles sont peintes ; au zoom, cache mis à l'échelle puis rendu net en arrière-plan ; `AA_CompressTabletEvents` désactivé (fait dans `app.py`).
- Hors périmètre (§7.12) : cloud/sync, OCR, texte tapé, audio.

## Architecture

MVC, détaillée dans `docs/replica/architecture.md` (interfaces entre couches, schéma JSON, tâches de fond).

- `fnote/model/` — **sans Qt**. `Document → Page → calques → éléments` (`Stroke`, `Shape`, `ImageItem`). Calques dans un ordre de rendu fixe `LAYERS = highlights, images, ink, shapes` (le surligneur passe sous l'encre) ; `Page.add()` range l'élément dans le bon calque via `layer_for()`. Toute modification passe par une `Command` poussée dans `History` (undo illimité) ; chaque commande renvoie l'ensemble des `page.id` touchés → la vue n'invalide que ces caches.
- **Coordonnées en points PDF** (A4 = 595,28 × 841,89) indépendantes du zoom : l'export PDF est une copie directe. Ne jamais arrondir les positions en pixels (HiDPI/échelle fractionnaire).
- `fnote/model/serialization.py` — format `.fnote` = ZIP (`document.json` avec `format_version`, `assets/<hash>.png`, `source.pdf`). Écriture **atomique** (`atomic_write` : temporaire + fsync + `os.replace`, réutilisé par `config.py`). Lecture **défensive** : noms d'entrées en liste blanche, rien extrait sur disque, tailles plafonnées, chaque champ validé → `FNoteFormatError`. Une version de format supérieure est refusée, jamais écrasée. Tout nouveau champ doit être ajouté à `to_dict` **et** validé dans `from_dict`.
- `fnote/engine/` — calculs purs NumPy (lissage, pression, géométrie, reconnaissance de formes) : testables sans matériel.
- `fnote/view/` — Qt. `style.py` génère **le** QSS depuis `fnote/resources/tokens.json` (aucune couleur en dur dans les widgets ; thème clair/sombre suivi à chaud). Le canevas est un `QWidget` + `QPainter` maison (pas de `QGraphicsView`).
- `fnote/controller/` — `InputRouter` doit être un **filtre d'événements sur `QApplication`** : sous Wayland, `TabletEnterProximity/LeaveProximity` arrivent à l'application, pas au widget. Il gère curseur caché, rejet de la paume, doigt = défilement/zoom, souris ignorée quand le stylet est proche.
- PDF : utiliser `import pymupdf` (l'alias `fitz` est déprécié).

## Méthode de travail

- **Par phases** (§12 de `PROMPT_FNote.md`), une branche par phase (`phase-1-encre`, …). À la fin de chaque phase : s'arrêter et donner commandes de lancement, checklist de test manuel au stylet, points fragiles ; attendre le retour de l'utilisateur. PR (`gh pr create`), merge dans `main` et tag `v0.N-phaseN` **seulement après sa validation**.
- **Commits** : petits (un changement cohérent, ~200 lignes max), Conventional Commits en français (`feat(encre): …`, `fix(lasso): …`, `test(pdf): …`). Avant chaque commit : `pytest` vert et l'appli démarre. Ne jamais committer de notes, PDF de cours ni le chemin du vault (voir `.gitignore`). Si un changement casse ce qui était validé, proposer `git revert`.
- **Pack Replica** = colonne vertébrale : la matrice `docs/replica/features.csv` est la checklist du projet (colonne `clone` : `no`/`partial`/`yes`, à mettre à jour au fil du build) ; `replica-diff` en fin de phase (score dans la PR). Correctifs issus des avis réels : `docs/replica/fixes.md`. On réplique les usages, jamais le nom, les icônes ni les textes de Samsung.
- Fin de phase, avant la PR : `/fin-de-phase N` (enchaîne `replica-diff`, `simplify`, `code-review`, `ponytail-debt`, `security-review` et le bilan). Automatismes : `.githooks/pre-commit` lance pytest ; un hook Claude (`.claude/settings.json`) relance le test hors ligne après chaque édition de `fnote/**.py`.
- Tests pytest pour tout ce qui ne dépend pas du matériel (modèle, sérialisation, undo, formes, règle, PDF) ; ce qui dépend du stylet passe par les checklists manuelles (`docs/tests.md`).
