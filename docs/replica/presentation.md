# Fiche de présentation (format type Flathub / GNOME Logiciels)

Adapté de `replica-launch` : pas de prix, pas de boutique mobile, pas de plan de lancement. Ce qui reste : la fiche telle qu'elle apparaîtrait dans GNOME Logiciels, et les éléments d'un futur `metainfo.xml`.

| champ | valeur | limite |
|---|---|---|
| Nom | Plume | ≤ 30 car. ✔ |
| Résumé | Notes manuscrites et PDF annotés, au stylet | ≤ 35 car. (Flathub conseille ~35) ✔ |
| Identifiant | `io.github.maxeldev.Plume` (proposé ; le lanceur actuel s'appelle `plume.desktop`) | — |
| Catégorie | Office | — |
| Licence | MIT (code) ; distribution liée à l'AGPL-3.0 via PyMuPDF | — |
| Contenu | aucun réseau, aucun compte, aucune télémétrie | OARS : tout « none » |

## Description

Plume est une application de prise de notes manuscrites pensée pour les PC portables convertibles à stylet sous Linux.

L'encre suit la pointe sans retard, le curseur disparaît pendant l'écriture et la paume posée sur l'écran ne dessine pas : on écrit comme sur une feuille.

Fonctionnalités :
- stylo à pression, bille et crayon ; cinq stylos favoris ;
- surligneur qui passe sous l'encre, option ligne droite ;
- gomme entière ou partielle, accessible au bouton du stylet ;
- lasso pour déplacer, redimensionner, pivoter, recolorer ;
- formes parfaites en gardant le stylet immobile ;
- règle virtuelle graduée, pivotable aux deux doigts ;
- annotation de PDF et export PDF vectoriel ;
- images collées depuis le presse-papiers ;
- notes rangées dans votre dossier (compatible Obsidian), avec un PDF à côté de chaque note.

Plume fonctionne entièrement hors ligne.

## Captures (dans l'ordre)

1. `docs/screenshots/note.png` — une note de cours manuscrite
2. `docs/screenshots/pdf.png` — un sujet de TD annoté et surligné
3. `docs/screenshots/regle.png` — formes auto-corrigées et règle
4. `docs/screenshots/lasso.png` — sélection au lasso
5. `docs/screenshots/accueil.png` — accueil et notes récentes

Régénérer : `QT_QPA_PLATFORM=offscreen .venv/bin/python tools/captures.py docs/screenshots`.

## Mots-clés

notes ; manuscrit ; stylet ; PDF ; annoter ; surligneur ; tablette ; Wacom ; Obsidian ; hors ligne

## Vérifications faites

- Aucun nom, logo, couleur ni texte de l'original dans la fiche ni dans l'application (`docs/replica/marque.md`, balayage propre).
- Aucune « preuve » inventée : pas de témoignage, de note ni de nombre d'utilisateurs.
- Le fichier `packaging/plume.desktop` passe `desktop-file-validate`.

## Non fait (et pourquoi)

- **Tarifs, Stripe, plan de lancement** : hors sujet pour une application personnelle et libre.
- **Publication Flathub** : il faudrait générer les modules Python (PySide6, PyMuPDF) avec `flatpak-pip-generator` et faire valider l'identifiant et la licence AGPL. Faisable plus tard ; l'installation locale suffit pour l'usage visé.
