# Carte de reconnaissance : Samsung Notes (Windows / Android) → FNote (Linux, Qt)

Périmètre : l'écriture manuscrite au stylet et l'annotation de PDF (section 7 de `PROMPT_FNote.md`), sans 7.12.
Pour : un étudiant ingénieur qui prend tous ses cours au S Pen sur un Galaxy Book 3 360 sous Fedora/Wayland.
Date : 2026-11-14

> On réplique des **usages et des comportements**, pas le code, les icônes, les textes ni le nom de Samsung.
> Sources : pages d'aide publiques uniquement, sans compte, sans binaire, sans capture réseau.

## Sources

| # | source | URL | notes |
| --- | --- | --- | --- |
| 1 | aide Samsung (PC) | https://www.samsung.com/us/support/answer/ANS10001469/ | modes Stylo / Surligneur / Gomme, réglages type-taille-couleur-opacité |
| 2 | aide Samsung (stylet) | https://www.samsung.com/us/support/answer/ANS10003634 | bouton du S Pen maintenu = gomme temporaire |
| 3 | aide Samsung (réglages) | https://www.samsung.com/us/support/answer/ANS10001384/ | fonctions et paramètres, modules de la barre d'outils |
| 4 | aide Samsung (PDF) | https://www.samsung.com/us/support/answer/ANS10002404/ | import/export PDF, écriture sur le PDF |
| 5 | FAQ Samsung Notes | https://www.samsung.com/us/support/answer/ANS00077061 | gomme « par trait » par défaut, Write on PDF |
| 6 | blog Samsung Insights (2025) | https://insights.samsung.com/2025/03/27/10-tips-for-increased-productivity-with-samsung-notes/ | astuces : formes, lasso, pages |
| 7 | communauté Samsung (déc. 2025) | https://us.community.samsung.com/t5/Global-Content/Dec-25-Samsung-Notes-Updated-Features-Improvements-and-Tips/ba-p/3457468 | « Auto-fix Shapes » : dessiner puis maintenir |
| 8 | Wikipédia | https://en.wikipedia.org/wiki/Samsung_Notes | plateformes, historique |
| 9 | expérience de l'utilisateur | `PROMPT_FNote.md` §1 et §7 | usage réel quotidien sur Galaxy Book 3 360 |

## Boucle principale

Ouvrir une note (ou un PDF de cours), écrire et surligner au stylet aussi fluidement que sur papier, et retrouver la note dans son vault.

## Écrans

| ID | écran | accès | rôle | composants clés | états |
| --- | --- | --- | --- | --- | --- |
| S01 | Éditeur (canevas) | ouvrir une note | écrire, surligner, annoter | pages A4 en défilement continu, curseur caché, point de survol | vide (1 page blanche), rempli, fond PDF, zoomé, plein écran |
| S02 | Barre d'outils | en haut de S01 | changer d'outil en un geste | stylos favoris, surligneur, gomme, lasso, règle, image, annuler/rétablir | outil actif, désactivé (rien à annuler) |
| S03 | Réglages du stylo | 2e tap sur l'outil stylo | pointe, épaisseur, couleur | aperçu du trait, curseur d'épaisseur, pointes, palette | — |
| S04 | Sélecteur de couleur | « + » dans la palette | couleur précise | carré/roue HSV, champs RGB/HEX, opacité, récents | valeur HEX invalide |
| S05 | Réglages du surligneur | 2e tap sur surligneur | couleur, épaisseur, mode droit | 5 couleurs, couleur libre, interrupteur « droit » | — |
| S06 | Réglages de la gomme | 2e tap sur gomme | mode, taille | trait entier / partielle, taille, « surligneur seulement » | — |
| S07 | Sélection lasso | outil lasso + contour | modifier une sélection | cadre, poignées, rotation, menu contextuel | rien de sélectionné, sélection multiple |
| S08 | Règle virtuelle | bouton règle | traits droits | règle graduée en cm, angle affiché, poignée | masquée, affichée, aimantée |
| S09 | Gestion des pages | bouton pages | réordonner, supprimer, insérer | miniatures, glisser-déposer | 1 page, nombreuses pages |
| S10 | Panneau du vault | panneau latéral | trouver et organiser les notes | arborescence dossiers + `.fnote` + `.pdf`, menu contextuel | vault vide, vault non choisi |
| S11 | Paramètres | menu | préférences | vault, courbe de pression, fond par défaut, bouton latéral, doigt dessine | — |
| S12 | Choix du vault (1er lancement) | premier démarrage | définir le dossier racine | sélecteur de dossier | aucun vault, dossier introuvable |
| S13 | Import PDF | menu / glisser un PDF | créer une note sur un PDF | sélecteur de fichier, progression | PDF chiffré ou corrompu |
| S14 | Export PDF | menu | partager / intégrer à Obsidian | chemin de sortie, progression | erreur d'écriture |
| S15 | Diagnostic tablette | `--debug-tablet` | vérifier le S Pen | type de périphérique, pression, inclinaison, proximité, bouton | aucun stylet détecté |

## Parcours

```
F01 Prendre une nouvelle note de cours
    S10 nouvelle note -> S01 écrire
    clics (parcours heureux) : 2
    cas limites : vault non choisi (S12), plantage pendant l'écriture (sauvegarde auto)

F02 Annoter un sujet de TD en PDF
    S13 importer -> S01 écrire / surligner sur le PDF -> S09 insérer une page vierge -> S14 exporter
    clics (parcours heureux) : 4
    cas limites : PDF chiffré, PDF de 200 pages, pages au format paysage

F03 Surligner un passage
    S02 surligneur -> S01 trait (droit si option) ; l'encre reste lisible au-dessus
    clics : 1
    cas limites : repasser deux fois dans le même trait (pas d'accumulation)

F04 Corriger une erreur
    bouton latéral maintenu -> gomme -> relâcher -> retour au stylo
    clics : 0
    cas limites : gomme partielle qui coupe un trait en deux

F05 Déplacer / redimensionner un bloc de calculs
    S02 lasso -> S07 contour -> glisser / poignées
    clics : 2
    cas limites : sélection qui couvre deux pages, rotation + redimensionnement

F06 Tracer un tableau proprement
    S02 règle -> S08 placer et pivoter -> tracer le long du bord
    clics : 1
    cas limites : règle à 45°, surligneur le long de la règle

F07 Encadrer un résultat
    dessiner un rectangle à main levée -> maintenir 0,5 s -> rectangle parfait
    clics : 0
    cas limites : forme non reconnue (on garde le trait), reconnaissance désactivée

F08 Coller une capture d'écran
    Ctrl+V dans S01 -> image placée -> S07 ajuster
    clics : 1

F09 Changer de stylo favori
    S02 tap sur un favori
    clics : 1

F10 Retrouver une note dans Obsidian
    sauvegarde -> NomDeLaNote.pdf écrit à côté -> ![[NomDeLaNote.pdf]] dans Obsidian
    clics : 0 (automatique)
```

## Composants

| composant | variantes | états | utilisé sur |
| --- | --- | --- | --- |
| Bouton d'outil (gros, adapté au stylet) | outil, stylo favori, action | normal, survol, actif, désactivé | S02 |
| Popover de réglages | stylo, surligneur, gomme | ouvert, fermé | S03, S05, S06 |
| Pastille de couleur | palette, récente, ajouter | normale, sélectionnée | S03, S04, S05 |
| Curseur (slider) d'épaisseur | épaisseur, taille de gomme, opacité | — | S03, S05, S06, S04 |
| Interrupteur | surligneur droit, formes auto, doigt dessine | on, off | S05, S11 |
| Cadre de sélection | poignées de coin, rotation | inactif, en cours de déplacement | S07 |
| Menu contextuel | sélection, vault | — | S07, S10 |
| Miniature de page | — | normale, sélectionnée, en déplacement | S09 |
| Arborescence | dossier, note, PDF | ouvert, fermé, renommage | S10 |
| Onglet de note | — | actif, modifié (non sauvegardé) | S01 |
| Barre de progression | import, export | en cours, erreur | S13, S14 |

## Modèle de données déduit

```
Document   format_version, pages[], metadata (title, created, modified), source_pdf (chemin interne, optionnel)
           preuves : S01, S13, F02 ; confiance : haute

Page       width, height (A4 en points par défaut), background (blank | lined | grid | dots | pdf:N),
           layers : highlights[], images[], ink[], shapes[]  (ordre de rendu fixe)
           preuves : S01, S09, aide 1 ; confiance : haute

Stroke     points[(x, y, pressure, t)], color RGBA, width, tool (fountain | ballpoint | pencil | highlighter)
           preuves : S03, aide 1 ; confiance : haute

Shape      kind (line | rect | ellipse | triangle | arrow), géométrie, color, width, rotation
           preuves : F07, source 7 ; confiance : moyenne (Samsung convertit en trait « propre »)

ImageItem  asset (chemin dans assets/), rect, rotation, crop
           preuves : F08, aide 4 ; confiance : haute

Settings   vault_path, favorites[], palette[], recent_colors[], pressure_curve, default_background,
           side_button_action, finger_draws, shape_recognition, companion_pdf
           preuves : S11 ; confiance : haute (imposé par le cahier des charges)
```

Relations : Document 1-n Page ; Page 1-n Stroke / Shape / ImageItem ; Document 0-1 PDF source ; ImageItem n-1 asset.

## Matrice de fonctionnalités

Voir `features.csv` (source) et `fonctionnalites.md` (vue lisible par phase).
must : 51, should : 18, could : 1, skip : 7.

## Hors périmètre (ne peut pas ou ne doit pas être répliqué)

- Synchronisation, compte Samsung, partage, collaboration : services réseau, interdits par la contrainte 100 % local.
- Assistant IA (résumé, mise en forme) : service distant.
- OCR et recherche dans l'écriture manuscrite, texte tapé, audio : exclus par §7.12.
- Format `.sdocx` de Samsung : format propriétaire, pas d'import prévu.
- Icônes, nom, textes d'interface et visuels Samsung : on recrée tout.

## Taille

Écrans : 15. Parcours : 10. Entités : 6.
Parties difficiles : (1) latence de l'encre en Python/Qt sous Wayland, (2) gomme partielle et lasso avec rotation sur des traits à pression variable, (3) export PDF vectoriel fidèle (contour des traits à pression).
Taille : **L** (plusieurs mois en solo, découpés en 7 phases).
