# Design system — Plume (phase 0 : tokens)

Source unique des valeurs : `plume/resources/tokens.json`. Le style Qt est **généré** à partir des tokens par `plume/view/style.py` (un seul QSS centralisé) : aucun code de couleur en dur dans les widgets.

Adapté pour Qt : pas de CSS ni de Tailwind ; `tokens.css` est remplacé par le QSS généré, et les « primitives » sont des widgets Qt stylés par `objectName`/propriétés.

## Principes

- **La feuille d'abord.** L'interface est discrète : une barre d'outils fine en haut, un « bureau » gris autour de pages blanches. Les pages restent blanches en thème sombre (option future).
- **Pensé pour le stylet.** Cibles ≥ 40 px, boutons d'outil de 44 px, pastilles de couleur de 32 px, pas de menus imbriqués pour les outils courants.
- **Une seule barre** (correctif #6) : tout outil est à un geste ; ses réglages s'ouvrent dans un popover sous le bouton.
- **Rien de Samsung** : couleurs, libellés et icônes originaux. Icônes prévues : **Lucide** (licence ISC), copiées en SVG dans `plume/resources/icons/` en phase 2.

## Couleurs (rôles)

| rôle | clair | sombre | usage |
|---|---|---|---|
| bg | #f4f5f7 | #16181c | fond de fenêtre |
| surface | #ffffff | #1f2227 | barre d'outils, popovers, panneaux |
| border | #dde1e6 | #30353d | séparateurs |
| border-input | #7b8490 | #7e8792 | champs, contours de contrôles (≥ 3:1) |
| text / text-muted | #15181d / #565f6b | #e8eaed / #a3aab3 | texte |
| accent / on-accent | #26686c / #fff | #7cc4c7 / #0d1a1b | outil actif, focus — bleu-vert « encre », provisoire jusqu'à replica-brand |
| accent-soft | #dcecec | #24393b | fond du bouton d'outil actif |
| danger / success | #b3261e / #1e6b45 | #f2a29b / #7fd1a3 | suppression / confirmation |
| desk / page | #e6e8eb / #fff | #0f1114 / #fff | autour des pages / les pages |

Contraste (`contrast.py`) : **20 paires, 0 échec AA**.

## Palette d'encre (16)

noir #1a1a1a, graphite #4a4f57, ardoise #37474f, bleu-nuit #1b2a6b, bleu #1f5fd1, cyan #00838f, vert #2e7d32, vert-forêt #1b4d2b, olive #6b6b00, rouge #d32f2f, bordeaux #8e1b3a, orange #e65100, brun #6d4321, violet #6a3fb5, prune #5b2160, magenta #c2185b.
Choix : 3 neutres, 3 bleus (cours / définitions), 3 verts, 2 rouges (corrections), chaudes et violets pour distinguer les parties. Toutes ≥ 3,79:1 sur la page blanche.

## Surligneur (5 + libre)

jaune #ffe066, vert #9be58a, rose #ff9ecb, bleu #8fd0ff, orange #ffbf73, à **45 % d'opacité** appliquée **une seule fois au trait entier** (correctif #5), composés en *multiply* sous l'encre.

## Tailles et espacements

tool-button 44 px · icon 24 px · toolbar-height 56 px · swatch 32 px · touch-min 40 px · point de survol 4 px.
Espacements 4/8/12/16/24/32. Rayons 6/10/14.
Fonds de page : interligne 8 mm, quadrillage 5 mm, points 5 mm, lignes #c9d3df / grille #dfe5ec.

## Composants

```
ToolButton (QToolButton#tool)
  tailles   44×44, icône 24
  états     normal, survol (surface → accent-soft 50 %), actif (accent-soft + liseré accent 2 px),
            focus clavier (anneau accent 2 px), désactivé (opacité 40 %)
  a11y      toolTip + accessibleName avec raccourci ; activable au clavier
  utilisé   S02

FavoritePen (QToolButton#favorite)
  rendu     pastille de la couleur + trait d'aperçu de l'épaisseur
  états     comme ToolButton ; 2e appui sur le favori actif → popover de réglages
  utilisé   S02

Swatch (QToolButton#swatch)
  32×32, rond ; sélectionné = anneau text 2 px + anneau surface 2 px ; « + » ouvre S04
  utilisé   S03, S04, S05

Popover (QFrame#popover, fenêtre Qt.Popup)
  surface, bordure border, rayon lg, ombre ; se ferme au tap extérieur ou Échap
  utilisé   S03, S05, S06

Slider (QSlider)
  poignée 20 px pour le stylet, piste 4 px accent ; valeur affichée à côté
  utilisé   S03, S04, S05, S06

Switch (QCheckBox#switch)  utilisé S05, S11
SelectionFrame (peint par le canevas) : contour accent pointillé, poignées 12 px, poignée de rotation   S07
Thumbnail (S09), Tree (S10), Tab (S01), ProgressBar (S13/S14) : styles Qt par défaut + tokens
HoverDot (peint par le canevas) : disque 4 px couleur de l'outil, 70 % d'opacité, seulement en survol stylet
```

Thème : suit le système via `QStyleHints.colorScheme()` (Qt ≥ 6.5), changement à chaud.
