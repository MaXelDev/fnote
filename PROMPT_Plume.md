# Projet « Plume » — application de prise de notes manuscrites pour Fedora

> Prompt à donner à Claude Code. Place ce fichier à la racine d'un dossier vide (ex. `~/Projets/plume/`), vérifie que `gh auth status` indique que tu es connecté à GitHub, lance `claude` dans ce dossier et dis : « Lis PROMPT_Plume.md et commence la phase 0. »

---

## 1. Contexte

Je suis étudiant ingénieur (INSA Lyon, Réseaux & Télécoms). J'utilise un **Samsung Galaxy Book 3 360** (écran tactile + stylet S Pen, numériseur Wacom) sous **Fedora, session Wayland (GNOME)**. Sous Windows, j'utilisais Samsung Notes pour tous mes cours manuscrits (maths, physique…). Je veux un équivalent sous Linux.

J'ai testé d'autres applis. Ce qui m'a fait fuir :
- **le manque de fluidité** : l'encre traîne derrière le stylet, les traits sont saccadés ;
- **le curseur de souris qui reste affiché pendant que j'écris** : je n'ai pas l'impression d'écrire sur une feuille.

Ces deux points sont **les critères n°1 du projet**. Une fonctionnalité de plus ne vaut rien si l'écriture n'est pas aussi agréable que sur Samsung Notes.

## 2. Contraintes non négociables

- **100 % local et hors ligne.** Aucun appel réseau, aucune télémétrie, aucun compte, aucun cloud. N'importe aucune bibliothèque réseau (`requests`, `urllib.request`, `QNetwork*`, etc.). Ajoute un test qui échoue si une de ces importations apparaît dans le code.
- **Open source** (licence MIT ou GPL-3.0), dépendances open source uniquement.
- **Linux / Fedora / Wayland uniquement.** La compatibilité Windows et macOS n'est pas un objectif : ne complexifie pas le code pour elles.
- **Les notes vivent dans mon vault Obsidian.** L'appli travaille sur un dossier racine configurable (mon vault) ; pas de base de données cachée ailleurs.

## 3. Stack technique imposée

- **Python 3.12+**, **PySide6 (Qt 6)** : Qt gère nativement les événements de tablette (`QTabletEvent` : pression, inclinaison, proximité) sous Wayland via le protocole tablet-v2.
- **PyMuPDF (fitz)** : rendu des pages PDF et export des annotations **en vectoriel** dans le PDF (le texte d'origine doit rester sélectionnable).
- **NumPy** si utile pour le lissage et la reconnaissance de formes.
- Environnement virtuel (`python -m venv .venv`), dépendances listées dans `pyproject.toml`.
- Architecture **MVC** claire (modèle de données ↔ vues Qt ↔ contrôleurs/outils), je connais ce pattern.
- Lancement forcé en Wayland natif : `QT_QPA_PLATFORM=wayland` (avec repli `xcb` si indisponible).

## 4. Architecture

```
plume/
├── app.py                  # point d'entrée, QApplication, config Wayland
├── model/
│   ├── document.py         # Document → Pages → Calques → Éléments
│   ├── elements.py         # Stroke, Highlight, Shape, ImageItem
│   ├── serialization.py    # lecture/écriture du format .plume
│   └── history.py          # undo/redo (pattern Command)
├── view/
│   ├── canvas.py           # widget de dessin principal (rendu + événements)
│   ├── page_renderer.py    # rendu d'une page, cache par page/tuile
│   ├── toolbar.py          # outils, palette, épaisseurs
│   ├── color_picker.py     # préréglages + roue/RGB/HEX + récents
│   ├── ruler.py            # règle virtuelle
│   └── vault_browser.py    # arborescence du vault (panneau latéral)
├── controller/
│   ├── input_router.py     # stylet / doigt / souris → bon comportement
│   └── tools/              # pen.py, highlighter.py, eraser.py, lasso.py, shape.py, image.py
├── engine/
│   ├── smoothing.py        # lissage du trait
│   ├── pressure.py         # courbe de pression
│   └── shape_recognition.py
├── pdf/
│   ├── importer.py         # PDF → pages avec fond PDF
│   └── exporter.py         # note → PDF vectoriel
└── tests/
```

### Modèle de données
- `Document` : liste de `Page` (format A4 par défaut, défilement vertical continu comme Samsung Notes), métadonnées, référence éventuelle à un PDF source.
- `Page` : fond (`blank`, `lined`, `grid`, `dots`, ou page N d'un PDF), et des calques dans cet ordre de rendu : **fond → surlignages → images → encre → formes**. Le surligneur passe toujours *sous* l'encre.
- `Stroke` : liste de points `(x, y, pression, timestamp)` en coordonnées de page (unités indépendantes du zoom), couleur RGBA, épaisseur de base, outil.

### Format de fichier `.plume`
- Une note = **un fichier `.plume`** = une archive ZIP contenant `document.json` (traits vectoriels, versionné avec un champ `format_version`), un dossier `assets/` (images insérées) et le PDF source s'il y en a un.
- **Sauvegarde atomique** (écrire dans un fichier temporaire puis `os.replace`) + sauvegarde automatique après quelques secondes d'inactivité. Jamais de perte de données en cas de crash.
- **Export compagnon pour Obsidian** : à chaque sauvegarde (option activable), générer `NomDeLaNote.pdf` à côté du `.plume`, pour que je puisse l'intégrer dans mes notes Obsidian avec `![[NomDeLaNote.pdf]]`.

## 5. Exigences de fluidité (critiques)

Mets en place et respecte ces règles dès la phase 1 :
- **Ne jamais redessiner toute la page pendant le tracé.** Le trait en cours est dessiné de façon incrémentale ; les traits terminés sont « cuits » dans un cache bitmap par page (ou par tuile), invalidé seulement là où quelque chose change.
- Ne rendre que les pages visibles dans le viewport ; recalcul du cache en arrière-plan au zoom (afficher d'abord une version mise à l'échelle, puis la version nette).
- Activer les événements de tablette haute fréquence et désactiver la compression d'événements (`Qt.AA_CompressTabletEvents` à False) pour ne perdre aucun point.
- Le lissage du trait ne doit pas ajouter de retard visible : léger filtre (type moyenne pondérée / Catmull-Rom) appliqué sur les derniers points, finalisé au lever du stylet.
- Épaisseur variable selon la pression, avec une **courbe de pression réglable** dans les paramètres.
- Objectif : latence perçue minimale, 60 fps au défilement d'une note de 30 pages. Ajoute un mode `--debug-perf` qui affiche fps et temps de rendu.

## 6. Comportement du stylet, du doigt et du curseur

- **Le curseur de souris est caché dès que le stylet est en proximité de l'écran** (`TabletEnterProximity`) et tant qu'il écrit. À la place, afficher optionnellement un **petit point discret** sous la pointe (couleur de l'outil actif) quand le stylet survole. Le curseur réapparaît quand la souris/le pavé tactile bouge.
- **Rejet de la paume** : quand le stylet est en proximité, ignorer tous les événements tactiles.
- **Doigt** : un doigt = défiler, deux doigts = zoom (pincement) et défilement. Le doigt ne dessine jamais (option à activer dans les paramètres seulement).
- **Bouton latéral du stylet** : maintenu = gomme temporaire (configurable : gomme ou lasso).
- **Souris** : peut dessiner (utile sans stylet), molette = défilement, Ctrl+molette = zoom.
- Ajoute une fenêtre de diagnostic (`--debug-tablet`) qui affiche en temps réel le type de périphérique, la pression, l'inclinaison et les événements de proximité, pour que je puisse vérifier que mon S Pen est bien reconnu.

## 7. Fonctionnalités

### 7.1 Stylo
- Pression, plusieurs types de pointe (stylo-plume, stylo bille à épaisseur constante, crayon).
- **3 à 5 « stylos favoris »** enregistrés (outil + couleur + épaisseur), changeables en un clic, comme dans Samsung Notes.

### 7.2 Couleurs
- Palette de couleurs prédéfinies (au moins 16, bien choisies pour la prise de notes).
- Sélecteur avancé : roue/carré HSV, champs **RGB** et **HEX**, opacité.
- Liste des couleurs récentes ; possibilité d'ajouter une couleur personnalisée à la palette.

### 7.3 Surligneur (très utilisé, à soigner)
- Translucide, mode de fusion qui ne masque pas l'encre (multiply), toujours rendu sous l'encre.
- Pas d'accumulation d'opacité quand on repasse dans un même trait.
- Option « surligneur droit » : le trait se redresse automatiquement en ligne horizontale.
- Couleurs de surligneur prédéfinies (jaune, vert, rose, bleu, orange) + couleur libre.

### 7.4 Gomme
- Mode « trait entier » (efface tout le trait touché) et mode « partielle » (coupe le trait).
- Taille réglable ; option « n'effacer que le surligneur ».

### 7.5 Lasso
- Sélection libre au tracé d'un contour (traits, surlignages, formes, images).
- Déplacer, redimensionner (poignées, avec option conserver les proportions), pivoter.
- Changer la couleur/l'épaisseur de la sélection, copier/couper/coller, dupliquer, supprimer.

### 7.6 Formes auto-corrigées
- **Dessiner puis maintenir le stylet immobile ~0,5 s** → le trait est remplacé par une forme parfaite : ligne droite, rectangle/carré, cercle/ellipse, triangle, flèche.
- Utile pour encadrer et entourer : la forme reprend la couleur et l'épaisseur du trait d'origine.
- La forme reste modifiable au lasso. Option pour désactiver la reconnaissance.

### 7.7 Règle virtuelle (fonctionnalité prioritaire)
- Bouton pour afficher/masquer une règle à l'écran (comme sur les applis iPad).
- Déplaçable et **pivotable avec deux doigts** (ou à la souris avec une poignée), affichage de l'angle, aimantation aux angles 0°, 15°, 30°, 45°, 90°…
- Quand on trace le long de son bord, **le trait s'aimante parfaitement au bord**, stylo comme surligneur.
- Graduations en cm.
- Objectif : faire facilement des traits droits, des tableaux, souligner proprement.

### 7.8 Images
- Insertion depuis un fichier, glisser-déposer et coller depuis le presse-papiers (captures d'écran).
- Déplacer/redimensionner/pivoter via le lasso, recadrage simple.

### 7.9 PDF
- **Importer un PDF** (sujet de TD, poly de cours) : chaque page devient une page de note avec le PDF en fond ; on écrit et surligne directement dessus.
- Possibilité d'**insérer des pages vierges** entre les pages du PDF (pour mes calculs).
- **Exporter en PDF** : pages d'origine conservées en vectoriel (texte sélectionnable), annotations ajoutées en vectoriel via PyMuPDF.
- Exporter aussi une note sans PDF source en PDF.

### 7.10 Pages et navigation
- Défilement vertical continu, ajout de page automatique en bas, réorganisation et suppression de pages, miniatures.
- Fonds de page : blanc, ligné, quadrillé (5 mm), pointillé. Fond choisi par défaut dans les paramètres.
- Zoom fluide, « ajuster à la largeur ».
- Annuler/Rétablir illimité dans la session (Ctrl+Z / Ctrl+Y + boutons dans la barre d'outils, accessibles au stylet).

### 7.11 Gestion des notes
- Panneau latéral montrant l'arborescence de mon vault (dossiers + fichiers `.plume` et `.pdf`), création de dossiers et de notes, renommage, déplacement, suppression (vers la corbeille système).
- Ouvrir plusieurs notes en onglets.
- Paramètres stockés dans `~/.config/plume/config.json` (chemin du vault, stylos favoris, palette, courbe de pression…).

### 7.12 Hors périmètre (ne pas faire)
Synchronisation/cloud, connexion entre appareils, recherche dans l'écriture manuscrite (OCR), texte tapé, compatibilité Windows/macOS, enregistrement audio.

## 8. Interface

- Interface épurée, proche de Samsung Notes : une barre d'outils compacte en haut, gros boutons utilisables au stylet, la feuille occupe tout l'écran.
- Mode plein écran (F11) pour écrire sans distraction.
- Thème clair/sombre suivant le système (les fonds de page restent blancs par défaut).
- Raccourcis clavier pour les outils principaux.

## 9. Méthode de travail attendue

Tu ne peux pas tester le stylet toi-même : **travaille par phases et arrête-toi à la fin de chaque phase** pour que je teste sur ma machine. À chaque fin de phase, donne-moi :
1. les commandes exactes pour lancer l'appli ;
2. une **checklist de test manuel** précise (ce que je dois faire et ce que je dois observer) ;
3. ce qui reste fragile ou non fait.

Ensuite, attends mon retour avant de passer à la phase suivante.

Écris des **tests automatisés** (pytest) pour tout ce qui ne dépend pas du matériel : modèle de données, sérialisation, undo/redo, reconnaissance de formes, aimantation à la règle, import/export PDF.

## 10. Dépôt GitHub et commits

Le projet vit dans un **dépôt GitHub dès la phase 0**, pour pouvoir revenir en arrière à tout moment si quelque chose casse.

- **Création** : `git init`, puis `gh repo create plume --source=. --push`. Demande-moi avant si le dépôt doit être **public** ou **privé**.
- **`.gitignore`** dès le premier commit : `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, fichiers de config locale. **Ne jamais committer de notes, de PDF de cours ni le chemin de mon vault.**
- **Commits petits et fréquents** : un commit = **un seul changement cohérent** (une classe, un outil, un correctif, un test), jamais plusieurs fonctionnalités mélangées. Si un commit touche plus de ~200 lignes, découpe-le.
- **Avant chaque commit** : les tests passent (`pytest`) et l'appli se lance. On ne committe jamais du code cassé sur `main`.
- **Messages en français, format Conventional Commits** : `feat(encre): courbe de pression réglable`, `fix(lasso): rotation autour du centre`, `test(pdf): export vectoriel`, `refactor`, `docs`, `chore`…
- **Une branche par phase** (`phase-1-encre`, `phase-2-outils`…), poussée régulièrement (au moins après chaque petite série de commits). En fin de phase, et **seulement après ma validation**, ouvre une Pull Request avec `gh pr create` (résumé + checklist de test), fusionne-la dans `main`, puis pose un **tag** (`v0.1-phase1`, `v0.2-phase2`…) pour avoir des points de retour faciles.
- Si une modification casse quelque chose que j'avais validé, propose-moi de revenir en arrière (`git revert` du commit fautif) plutôt que d'empiler des correctifs.

## 11. Skills à utiliser

J'ai des skills installés dans Claude Code. **Utilise-les aux étapes indiquées** (charge-les avec l'outil Skill). Si un skill n'est pas disponible, dis-le-moi et continue sans.

### 11.1 Le pack Replica est la colonne vertébrale du projet

Ce projet est une réplique fonctionnelle de Samsung Notes. **Utilise le pack Replica en priorité et le plus possible, à chaque étape où il s'applique.** Les autres skills (11.2) viennent en complément, pas à la place.

Règles communes à tous les skills Replica :
- Le périmètre est celui de la **section 7**. Tout ce qui est en 7.12 (hors périmètre) est ignoré.
- On réplique **les usages et le comportement**, jamais le code, les icônes, le nom, les visuels ou les textes de Samsung.
- Ces skills sont conçus pour des applis web/mobiles avec serveur : **adapte-les** à une appli de bureau Qt 100 % locale. Quand une partie du skill ne s'applique pas (SQL, API web, Stripe, auth, domaine, stores mobiles), saute-la et dis-moi ce que tu as adapté.
- Range tous leurs livrables dans `docs/replica/` et committe-les.

| Skill | Quand | Ce que j'attends, adapté à Plume |
|---|---|---|
| `replica-recon` | Phase 0, en premier | Cartographie de Samsung Notes : écrans, parcours (créer une note, annoter un PDF, surligner, lasso…), modèle de données, **matrice de fonctionnalités** priorisée (`docs/replica/fonctionnalites.md`). Cette matrice devient la checklist de tout le projet. |
| `replica-entrepreneur` | Phase 0, juste après | Analyse des avis d'utilisateurs de Samsung Notes, Xournal++, Rnote et AirNote : ce qu'ils adorent, ce qu'ils détestent (fluidité, curseur, PDF…). Ignore le positionnement commercial. Sers-t'en pour ajuster les priorités de la matrice et me signaler des pièges à éviter. |
| `replica-architect` | Phase 0 | Stack et modèle de données. Remplace le « schéma SQL » par le **schéma JSON versionné du format `.plume`**, et l'« API » par les **interfaces entre modèle, vues et contrôleurs** (section 4). Rédige-le dans `docs/replica/architecture.md`. |
| `replica-design` | Phase 0 (tokens), phases 2 et 6 | Design system adapté à Qt : couleurs, palette d'encre et de surligneur, tailles de boutons utilisables au stylet, icônes, contraste WCAG, thème clair/sombre. Les tokens doivent être appliqués dans un fichier de style Qt (QSS) centralisé. |
| `replica-backend` | Phases 0, 1 et 5 | Pas de serveur ici : utilise-le uniquement pour la **couche de persistance locale** (lecture/écriture `.plume`, sauvegarde atomique, sauvegarde automatique) et les **tâches en arrière-plan** (export PDF compagnon, rendu des caches). Ignore auth, base de données distante, Stripe, emails. |
| `replica-build` | Toutes les phases | Construction écran par écran et outil par outil, **dans l'ordre des phases (section 12)** et en suivant la matrice. Chaque élément construit = un ou plusieurs petits commits (section 10). |
| `replica-diff` | **Fin de chaque phase** et fin du projet | Score de parité avec la matrice (périmètre section 7) et liste de ce qui manque ou diffère. Mets le résultat dans la description de la PR de la phase. |
| `replica-brand` | Phase 6 (et vérification en fin de chaque phase) | Nom définitif, palette, logo simple et ton de l'appli, et surtout **recherche des restes de l'original** : aucune référence à Samsung ne doit rester (noms, icônes, textes, commentaires). |
| `replica-launch` | Phase 6 | Pas de prix ni de store : adapte-le pour produire la **page GitHub du projet** (README soigné avec captures d'écran, description, mots-clés) et une **fiche de présentation type Flathub** (`docs/replica/presentation.md`). |
| `replica-deploy` | Phase 6 | Pas de domaine ni de serveur : adapte-le pour la **distribution locale** : fichier `.desktop` et icône, script d'installation pour Fedora, et une **GitHub Release** taguée. Si c'est simple, ajoute un manifeste Flatpak. |

### 11.2 Autres skills en complément

**Démarrage (phase 0)**
- `init` : génère le `CLAUDE.md` du projet ; recopies-y les règles essentielles de ce prompt (contraintes, fluidité, règles de commit, usage du pack Replica) pour qu'elles restent en mémoire d'une session à l'autre.
- `claude-code-setup:claude-automation-recommender` : propose les hooks utiles (ex. lancer `pytest` avant chaque commit, vérifier l'absence d'import réseau). Montre-moi ses recommandations avant de les appliquer.
- `engineering:architecture` : rédige un ADR (`docs/adr/0001-stack.md`) justifiant PySide6 + PyMuPDF + format `.plume`, en s'appuyant sur le livrable de `replica-architect`.
- `engineering:testing-strategy` : plan de tests (`docs/tests.md`) : ce qui est testé automatiquement et ce qui passe par mes checklists manuelles.

**Pendant chaque phase**
- `ponytail` : approche « plus petit changement complet », parfaitement adaptée aux petits commits.
- `run` : lance l'appli pour vérifier qu'elle démarre après chaque changement significatif.
- `engineering:debug` : dès qu'un bug n'est pas évident (surtout tablette/Wayland et performances de rendu).
- `frontend-design` : en complément de `replica-design` pour la direction visuelle. Ignore la partie web : l'appli est en Qt.
- `dataviz` : uniquement si tu fais un affichage des performances (`--debug-perf`).

**Fin de chaque phase (avant la PR)**
- `replica-diff` (voir 11.1).
- `simplify` : nettoie le code modifié.
- `code-review` (ou `ponytail-review`) : revue du diff de la branche.
- `ponytail-debt` : liste les raccourcis `shortcut:` laissés, à mettre dans la description de la PR.
- `security-review` : vérifie notamment qu'aucun accès réseau ne s'est glissé et que la lecture des fichiers (ZIP `.plume`, PDF importés) est sûre.

**Fin du projet (phase 6)**
- `replica-diff`, `replica-brand`, `replica-launch`, `replica-deploy` (voir 11.1).
- `ponytail-audit` puis `engineering:tech-debt` : audit qualité du dépôt.
- `engineering:documentation` : README d'installation et d'utilisation, en complément de `replica-launch`.

**À ne pas utiliser** : `web-artifacts-builder`, `webapp-testing` (l'appli n'est pas une appli web), et aucun connecteur MCP **dans le code de l'appli** (elle doit rester 100 % hors ligne). Tu peux par contre faire des recherches web pendant le développement (ex. pour `replica-recon` et `replica-entrepreneur`).

## 12. Phases

Chaque phase se construit avec `replica-build` et se termine par `replica-diff` (score de parité dans la PR).

- **Phase 0 — Recon et squelette** : dépôt GitHub (section 10) ; `replica-recon` → `replica-entrepreneur` → `replica-architect` → `replica-design` (tokens) ; `init`, `claude-automation-recommender`, ADR et plan de tests ; structure du projet, venv, `pyproject.toml`, fenêtre principale, choix du vault, format `.plume` (sauvegarde/chargement, avec `replica-backend` pour la persistance), fenêtre `--debug-tablet`, test « aucun import réseau ». **Montre-moi la matrice de fonctionnalités et l'analyse des avis avant d'écrire le code.**
- **Phase 1 — Moteur d'encre (le plus important)** : canevas multi-pages, stylo avec pression, lissage, cache de rendu (tâches de fond via `replica-backend`), curseur caché + point de survol, rejet de la paume, défilement/zoom au doigt, undo/redo, sauvegarde auto. **Ne passe pas à la suite tant que je n'ai pas validé que l'écriture est fluide.**
- **Phase 2 — Outils de base** : couleurs (palette + RGB/HEX + récents), stylos favoris, surligneur, gomme (deux modes), fonds de page, gestion des pages. Barre d'outils construite avec les tokens de `replica-design`.
- **Phase 3 — Lasso et images**.
- **Phase 4 — Formes auto-corrigées et règle virtuelle**.
- **Phase 5 — PDF** : import, pages insérées, export vectoriel, export compagnon pour Obsidian (tâche de fond via `replica-backend`).
- **Phase 6 — Confort et finition** : panneau du vault, onglets, paramètres, thème final (`replica-design` + `frontend-design`), raccourcis, plein écran ; puis `replica-diff` final, `replica-brand`, `replica-launch` (README / page GitHub), `replica-deploy` (installation Fedora + GitHub Release).

Avant de commencer la phase 0, résume-moi en quelques lignes ton plan, les skills que tu vas utiliser à chaque phase (en particulier ceux du pack Replica et comment tu les adaptes) et les points techniques que tu juges risqués (notamment le support des événements de tablette sous Wayland), puis lance-toi.
