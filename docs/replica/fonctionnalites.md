# Matrice de fonctionnalités — Plume

Checklist du projet. Source de vérité : `features.csv` (colonne `clone` : `no` → `partial` → `yes`, lue par `replica-diff`). Ce fichier est généré par `matrice.py`.

Priorités : **must** = indispensable, **should** = attendu, **could** = bonus, **skip** = hors périmètre. Colonne *Samsung* : `partial` = existe sous une autre forme, `no` = propre à Plume (ou correctif issu de `fixes.md`).

## Phase 0 — Squelette

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Fenêtre de diagnostic --debug-tablet | stylet | must | no | yes | spécifique Plume |
| Sauvegarde atomique (aucune perte sur crash) | fichiers | must | partial | yes |  |
| Format .plume (ZIP + document.json versionné + assets) | fichiers | must | no | yes | Samsung utilise .sdocx |
| Paramètres dans ~/.config/plume/config.json | paramètres | must | no | yes |  |
| --debug-tablet affiche l'échelle et le décalage stylet/pointeur | stylet | should | no | yes | fix #7 (Rnote #1543) |

## Phase 1 — Moteur d'encre

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Écriture au stylet avec pression (épaisseur variable) | encre | must | yes | yes | critère n°1 |
| Tracé incrémental sans retard visible (latence minimale) | encre | must | yes | yes | critère n°1 ; cache bitmap par page |
| Lissage du trait sans retard (finalisé au lever) | encre | must | yes | yes |  |
| Courbe de pression réglable | encre | must | partial | partial | Samsung n'expose qu'un réglage de sensibilité |
| Curseur caché quand le stylet est en proximité | stylet | must | yes | yes | critère n°1 |
| Point discret de survol sous la pointe | stylet | should | yes | yes | option |
| Rejet de la paume (tactile ignoré si stylet proche) | stylet | must | yes | yes |  |
| Un doigt = défiler / deux doigts = zoom | navigation | must | yes | yes |  |
| Le doigt ne dessine pas (option pour l'activer) | stylet | must | yes | yes |  |
| Souris dessine / molette défile / Ctrl+molette zoome | navigation | must | partial | yes |  |
| Mode --debug-perf (fps et temps de rendu) | encre | should | no | yes | spécifique Plume |
| Annuler / rétablir illimité (Ctrl+Z / Ctrl+Y + boutons) | édition | must | yes | partial |  |
| Sauvegarde automatique après inactivité | fichiers | must | yes | yes |  |
| Défilement vertical continu multi-pages A4 | pages | must | yes | yes |  |
| Ajout automatique de page en bas | pages | must | yes | yes |  |
| Rendu des seules pages visibles | encre | must | yes | yes | 60 fps sur 30 pages |
| Zoom fluide (aperçu mis à l'échelle puis net) | navigation | must | yes | yes |  |
| Zoom : cache mis à l'échelle pendant le geste puis rendu net | navigation | must | no | yes | fix #1 (Rnote #7) |
| Souris ignorée quand le stylet est proche (pas de saut de trait) | stylet | must | no | yes | fix #2 (Rnote #1440) |
| Coordonnées exactes à 125/150/200 % d'échelle Wayland | stylet | must | no | yes | fix #3 (Rnote #338) |

## Phase 2 — Outils de base

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Bouton latéral maintenu = gomme temporaire (ou lasso) | stylet | must | yes | partial | configurable |
| Ajuster à la largeur | navigation | should | yes | yes |  |
| Types de pointe : plume / bille / crayon | stylo | should | yes | no | Samsung en propose plus (pinceau calligraphie…) |
| 3 à 5 stylos favoris (outil+couleur+épaisseur) | stylo | must | yes | no |  |
| Palette prédéfinie ≥ 16 couleurs | couleurs | must | yes | no |  |
| Sélecteur avancé HSV + RGB + HEX + opacité | couleurs | must | yes | no |  |
| Couleurs récentes + ajout à la palette | couleurs | should | yes | no |  |
| Surligneur translucide en multiply sous l'encre | surligneur | must | yes | yes |  |
| Surligneur sans accumulation d'opacité dans un trait | surligneur | must | yes | yes |  |
| Surligneur droit (redressement horizontal) | surligneur | must | yes | partial |  |
| Couleurs de surligneur prédéfinies + libre | surligneur | must | yes | no |  |
| Gomme trait entier | gomme | must | yes | yes |  |
| Gomme partielle (coupe le trait) | gomme | must | yes | yes |  |
| Taille de gomme réglable | gomme | should | yes | no |  |
| Gomme « surligneur seulement » | gomme | should | yes | partial |  |
| Fonds de page : blanc / ligné / quadrillé 5 mm / pointillé | pages | must | yes | no |  |
| Fond par défaut dans les paramètres | pages | should | yes | no |  |
| Réorganiser / supprimer des pages + miniatures | pages | must | yes | no |  |
| Barre d'outils compacte à gros boutons pour stylet | interface | must | yes | no |  |
| Gomme par intersection de segments (aucun trait sauté) | gomme | must | no | yes | fix #4 (Rnote #1247) |
| Surligneur rendu en un seul chemin (opacité uniforme) | surligneur | must | no | yes | fix #5 (Rnote #106 #891) |
| Une seule barre d'outils + réglages en popover | interface | must | no | no | fix #6 (HN) |

## Phase 3 — Lasso et images

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Lasso libre (traits surlignages formes images) | lasso | must | yes | no |  |
| Lasso : déplacer | lasso | must | yes | no |  |
| Lasso : redimensionner (poignées + proportions) | lasso | must | yes | no |  |
| Lasso : pivoter | lasso | should | yes | no |  |
| Lasso : changer couleur / épaisseur | lasso | should | yes | no |  |
| Lasso : copier / couper / coller / dupliquer / supprimer | lasso | must | yes | no |  |
| Images : insertion depuis fichier | images | must | yes | no |  |
| Images : glisser-déposer | images | should | yes | no |  |
| Images : coller depuis le presse-papiers | images | must | yes | no | captures d'écran |
| Images : recadrage simple | images | should | yes | no |  |

## Phase 4 — Formes et règle

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Formes auto-corrigées (maintien ~0.5 s) | formes | must | yes | no | ligne rect cercle ellipse triangle flèche |
| Forme reprend couleur et épaisseur du trait | formes | must | yes | no |  |
| Option pour désactiver la reconnaissance | formes | should | yes | no |  |
| Règle virtuelle affichable | règle | must | no | no | prioritaire ; absente de Samsung Notes PC (présente sur iPad) |
| Règle déplaçable et pivotable deux doigts / poignée | règle | must | no | no |  |
| Règle : angle affiché + aimantation 0/15/30/45/90° | règle | must | no | no |  |
| Trait aimanté au bord de la règle (stylo et surligneur) | règle | must | no | no |  |
| Graduations en cm | règle | should | no | no |  |

## Phase 5 — PDF

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Import PDF (une page = une page avec fond PDF) | pdf | must | yes | no |  |
| Insérer des pages vierges entre pages PDF | pdf | must | yes | no |  |
| Export PDF vectoriel (texte d'origine sélectionnable) | pdf | must | partial | no | Samsung aplatit parfois |
| Export PDF d'une note sans PDF source | pdf | must | yes | no |  |
| Export compagnon NomDeLaNote.pdf pour Obsidian | fichiers | must | no | no | spécifique Plume |

## Phase 6 — Confort et finition

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Panneau arborescence du vault (.plume + .pdf) | notes | must | partial | no | Samsung a des dossiers internes |
| Créer / renommer / déplacer des notes et dossiers | notes | must | yes | no |  |
| Supprimer vers la corbeille système | notes | must | yes | no |  |
| Plusieurs notes en onglets | notes | should | no | no |  |
| Plein écran F11 | interface | should | yes | partial |  |
| Thème clair/sombre suivant le système | interface | should | yes | partial | fonds de page restent blancs |
| Raccourcis clavier des outils | interface | should | yes | no |  |

## Hors périmètre (skip)

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Synchronisation / cloud / compte Samsung | hors périmètre | skip | yes | skip | 7.12 — 100 % local |
| Recherche dans l'écriture manuscrite (OCR) | hors périmètre | skip | yes | skip | 7.12 |
| Texte tapé / zones de texte | hors périmètre | skip | yes | skip | 7.12 |
| Enregistrement audio synchronisé | hors périmètre | skip | yes | skip | 7.12 |
| Assistant IA (résumé / correction / mise en forme) | hors périmètre | skip | yes | skip | service distant ; non demandé |
| Notes partagées / collaboration | hors périmètre | skip | yes | skip | réseau |
| Compatibilité Windows / macOS | hors périmètre | skip | yes | skip | 7.12 |
