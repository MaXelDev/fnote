# Matrice de fonctionnalités — Plume

Checklist du projet. Source de vérité : `features.csv` (colonne `clone` : `no` → `partial` → `yes`, lue par `replica-diff`).

Priorités : **must** = indispensable, **should** = attendu, **could** = bonus, **skip** = hors périmètre.
Colonne *Samsung* : la fonction existe-t-elle dans l'original (`partial` = existe sous une autre forme, `no` = propre à Plume).

## Phase 0 — Squelette

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Fenêtre de diagnostic --debug-tablet | stylet | must | no | no | spécifique Plume |
| Sauvegarde atomique (aucune perte sur crash) | fichiers | must | partial | no |  |
| Format .plume (ZIP + document.json versionné + assets) | fichiers | must | no | no | Samsung utilise .sdocx |
| Paramètres dans ~/.config/plume/config.json | paramètres | must | no | no |  |

## Phase 1 — Moteur d'encre

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Écriture au stylet avec pression (épaisseur variable) | encre | must | yes | no | critère n°1 |
| Tracé incrémental sans retard visible (latence minimale) | encre | must | yes | no | critère n°1 ; cache bitmap par page |
| Lissage du trait sans retard (finalisé au lever) | encre | must | yes | no |  |
| Courbe de pression réglable | encre | must | partial | no | Samsung n'expose qu'un réglage de sensibilité |
| Curseur caché quand le stylet est en proximité | stylet | must | yes | no | critère n°1 |
| Point discret de survol sous la pointe | stylet | should | yes | no | option |
| Rejet de la paume (tactile ignoré si stylet proche) | stylet | must | yes | no |  |
| Un doigt = défiler / deux doigts = zoom | navigation | must | yes | no |  |
| Le doigt ne dessine pas (option pour l'activer) | stylet | must | yes | no |  |
| Souris dessine / molette défile / Ctrl+molette zoome | navigation | must | partial | no |  |
| Mode --debug-perf (fps et temps de rendu) | encre | should | no | no | spécifique Plume |
| Annuler / rétablir illimité (Ctrl+Z / Ctrl+Y + boutons) | édition | must | yes | no |  |
| Sauvegarde automatique après inactivité | fichiers | must | yes | no |  |
| Défilement vertical continu multi-pages A4 | pages | must | yes | no |  |
| Ajout automatique de page en bas | pages | must | yes | no |  |
| Rendu des seules pages visibles | encre | must | yes | no | 60 fps sur 30 pages |
| Zoom fluide (aperçu mis à l'échelle puis net) | navigation | must | yes | no |  |

## Phase 2 — Outils de base

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Bouton latéral maintenu = gomme temporaire (ou lasso) | stylet | must | yes | no | configurable |
| Ajuster à la largeur | navigation | should | yes | no |  |
| Types de pointe : plume / bille / crayon | stylo | should | yes | no | Samsung en propose plus (pinceau calligraphie…) |
| 3 à 5 stylos favoris (outil+couleur+épaisseur) | stylo | must | yes | no |  |
| Palette prédéfinie ≥ 16 couleurs | couleurs | must | yes | no |  |
| Sélecteur avancé HSV + RGB + HEX + opacité | couleurs | must | yes | no |  |
| Couleurs récentes + ajout à la palette | couleurs | should | yes | no |  |
| Surligneur translucide en multiply sous l'encre | surligneur | must | yes | no |  |
| Surligneur sans accumulation d'opacité dans un trait | surligneur | must | yes | no |  |
| Surligneur droit (redressement horizontal) | surligneur | should | yes | no |  |
| Couleurs de surligneur prédéfinies + libre | surligneur | must | yes | no |  |
| Gomme trait entier | gomme | must | yes | no |  |
| Gomme partielle (coupe le trait) | gomme | must | yes | no |  |
| Taille de gomme réglable | gomme | should | yes | no |  |
| Gomme « surligneur seulement » | gomme | should | yes | no |  |
| Fonds de page : blanc / ligné / quadrillé 5 mm / pointillé | pages | must | yes | no |  |
| Fond par défaut dans les paramètres | pages | should | yes | no |  |
| Réorganiser / supprimer des pages + miniatures | pages | must | yes | no |  |
| Barre d'outils compacte à gros boutons pour stylet | interface | must | yes | no |  |

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
| Images : recadrage simple | images | could | yes | no |  |

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
| Plein écran F11 | interface | should | yes | no |  |
| Thème clair/sombre suivant le système | interface | should | yes | no | fonds de page restent blancs |
| Raccourcis clavier des outils | interface | should | yes | no |  |

## Hors périmètre (skip)

| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |
|---|---|---|---|---|---|
| Synchronisation / cloud / compte Samsung | hors périmètre | skip | yes | no | 7.12 — 100 % local |
| Recherche dans l'écriture manuscrite (OCR) | hors périmètre | skip | yes | no | 7.12 |
| Texte tapé / zones de texte | hors périmètre | skip | yes | no | 7.12 |
| Enregistrement audio synchronisé | hors périmètre | skip | yes | no | 7.12 |
| Assistant IA (résumé / correction / mise en forme) | hors périmètre | skip | yes | no | service distant ; non demandé |
| Notes partagées / collaboration | hors périmètre | skip | yes | no | réseau |
| Compatibilité Windows / macOS | hors périmètre | skip | yes | no | 7.12 |
