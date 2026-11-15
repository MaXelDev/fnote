# Plan de tests — FNote

Principe : **tout ce qui ne dépend pas du matériel est testé automatiquement** (pytest, rapide, à chaque commit). Ce qui dépend du stylet, de l'écran tactile ou de la sensation d'écriture passe par une **checklist manuelle** que l'utilisateur déroule sur son Galaxy Book en fin de phase.

```
         ┌──────────────────────────┐
         │ Checklists manuelles     │  stylet, latence ressentie, paume, curseur
         ├──────────────────────────┤
         │ Smoke tests Qt offscreen │  la fenêtre s'ouvre, une capture est rendue
         ├──────────────────────────┤
         │ Tests unitaires pytest   │  modèle, format, moteur, PDF, garde-fous
         └──────────────────────────┘
```

Commande : `.venv/bin/pytest -q`. Objectif : < 5 s pour toute la suite, pour qu'elle tourne avant chaque commit.

## 1. Tests automatiques

| zone | type | fichier | cas clés | phase |
|---|---|---|---|---|
| Modèle (calques, ordre de rendu) | unitaire | `test_model.py` | surligneur rangé sous l'encre ; ordre fond → surlignages → images → encre → formes ; `bounds` | 0 ✅ |
| Undo / redo | unitaire | `test_model.py` | ajout/suppression avec réinsertion à l'indice d'origine ; nouvelle action vide « rétablir » ; 500 annulations | 0 ✅ |
| Format `.fnote` | unitaire | `test_serialization.py` | aller-retour complet ; PDF source ; arrondis ; version future refusée | 0 ✅ |
| Sauvegarde atomique | unitaire | `test_serialization.py` | crash simulé pendant l'écriture → ancien fichier intact, pas de temporaire oublié | 0 ✅ |
| Lecture sécurisée (fichier non fiable) | unitaire | `test_serialization.py` | entrées `../` ignorées et jamais écrites ; entrée trop grosse refusée ; NaN, couleur, outil, fond invalides → `FNoteFormatError` ; fichier non ZIP | 0 ✅ |
| Paramètres | unitaire | `test_config.py` | valeurs par défaut ; mauvais types ; fichier corrompu ; `XDG_CONFIG_HOME` | 0 ✅ |
| Hors ligne | garde-fou | `test_no_network.py` | AST de `fnote/` sans import réseau ; le détecteur attrape `requests`, `urllib`, `QtNetwork`, `__import__('socket')` | 0 ✅ |
| Lancement | unitaire | `test_app.py` | Wayland + repli xcb ; choix utilisateur respecté ; arguments | 0 ✅ |
| Courbe de pression | unitaire | `test_pressure.py` | monotone, bornes 0/1, interpolation | 1 |
| Lissage | unitaire | `test_smoothing.py` | ligne droite inchangée ; bruit réduit ; aucun point « en retard » de plus de N échantillons ; finalisation conserve début et fin | 1 |
| Contour d'un trait à pression | unitaire | `test_geometry.py` | polygone fermé, largeur ∝ pression | 1 |
| Mise en page / conversions écran ↔ page | unitaire | `test_layout.py` | aller-retour exact à zoom 0,5 / 1 / 2,37 et échelle 1,25 (correctif #3) | 1 |
| Cache de page | smoke Qt offscreen | `test_canvas.py` | ajouter un trait n'invalide que sa page ; rendu d'une page identique avant/après « cuisson » | 1 |
| Sauvegarde auto | Qt offscreen | `test_autosave.py` | une modification → sauvegarde après le délai, pas avant | 1 |
| Gomme | unitaire | `test_eraser.py` | trait entier ; partielle coupe en 2 ; segment rapide qui traverse sans point dedans efface quand même (correctif #4) ; « surligneur seulement » | 2 |
| Surligneur | unitaire | `test_highlighter.py` | redressement horizontal ; opacité appliquée une fois (un seul chemin) | 2 |
| Couleurs | unitaire | `test_colors.py` | HEX ↔ RGB ↔ HSV ; récents sans doublon, plafonnés | 2 |
| Pages | unitaire | `test_pages.py` | insérer, déplacer, supprimer + undo | 2 |
| Lasso | unitaire | `test_lasso.py` | sélection par polygone ; déplacer / redimensionner / pivoter autour du centre ; copier-coller garde de nouveaux id | 3 |
| Images | unitaire | `test_images.py` | asset dédupliqué par hash ; recadrage ; type refusé | 3 |
| Reconnaissance de formes | unitaire | `test_shape_recognition.py` | jeux de traits synthétiques bruités : ligne, rectangle, cercle, ellipse, triangle, flèche reconnus ; gribouillis → `None` ; couleur/épaisseur conservées | 4 |
| Règle | unitaire | `test_ruler.py` | aimantation au bord à 0°, 37°, 90° ; angles 0/15/30/45/90 ; hors zone → pas d'aimantation | 4 |
| Import PDF | intégration | `test_pdf_import.py` | PDF de fixture 3 pages → 3 pages aux bonnes dimensions ; PDF chiffré/corrompu → erreur claire | 5 |
| Export PDF | intégration | `test_pdf_export.py` | le texte d'origine reste extractible ; les traits sont des chemins vectoriels (pas d'image) ; page vierge insérée ; note sans PDF | 5 |
| Export compagnon | intégration | `test_companion.py` | `Nom.pdf` écrit à côté du `.fnote`, atomiquement | 5 |
| Vault | intégration | `test_vault.py` | créer, renommer, déplacer ; suppression vers la corbeille | 6 |

Fixtures PDF : générées par PyMuPDF dans les tests (aucun PDF de cours réel dans le dépôt).

## 2. Checklists manuelles (stylet, fin de chaque phase)

Elles figurent dans le message de fin de phase et dans la PR. Socle commun, repris à chaque phase :

- [ ] `fnote --debug-tablet` : le stylet apparaît comme *Stylus* ; la pression varie de 0 à ~1 ; l'entrée/sortie de proximité est journalisée ; le bouton latéral apparaît dans *Boutons* ; fréquence ≥ 100 Hz.
- [ ] Le curseur disparaît quand le stylet approche, réapparaît quand la souris bouge.
- [ ] Main posée sur l'écran pendant l'écriture : aucun trait parasite, pas de défilement.
- [ ] Écriture rapide d'une ligne de texte : pas de retard visible de l'encre, pas de segments anguleux.
- [ ] Un crash (`kill -9`) pendant l'écriture ne perd rien de ce qui a été sauvegardé et ne corrompt pas le fichier.

Mesures chiffrées (phase 1, `--debug-perf`) : fps au défilement d'une note de 30 pages (objectif 60), temps de rendu d'une page.

## 3. Lacunes connues

- Pas de mesure automatique de la **latence stylet → pixel** (nécessiterait une caméra) : on s'en remet au ressenti et au temps de `paintEvent` mesuré.
- Les événements tablette réels (`QTabletEvent`) ne sont pas injectés dans les tests ; les outils sont testés sur leurs fonctions pures, le routage d'entrée manuellement.
