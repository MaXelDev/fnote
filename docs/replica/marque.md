# Marque — Plume

## Nom

**Plume** : l'outil d'écriture par excellence, court, prononçable en français comme en anglais, sans lien de son ni de sens avec l'original. Identifiant technique : `plume` (app_id Wayland, fichier `.desktop`, type MIME `application/x-plume`).

| contrôle | résultat |
|---|---|
| ressemblance avec l'original | aucune (son, sens, graphie) |
| marques (USPTO, EUIPO, WIPO) | **à faire** — « Plume » est un mot courant ; des marques existent dans d'autres domaines (ex. réseau Wi-Fi, capteurs d'air). Sans enjeu pour un usage personnel et open source ; à vérifier par un juriste avant toute diffusion commerciale |
| dépôt GitHub | `MaXelDev/plume` (privé) — pris |
| Flathub / boutiques | **à faire** si publication |

Ce sont des contrôles de repérage, pas un avis juridique.

## Palette

Couleur de marque **bleu-vert « encre »** `#26686c` (sombre : `#7cc4c7`), famille différente du bleu vif de l'original. Accent secondaire : le jaune du surligneur `#ffe066`. Rôles et valeurs dans `plume/resources/tokens.json` ; contraste vérifié : **0 échec AA** (`contrast.py`).

## Logo

`plume/resources/plume.svg` — création originale : une page lignée portant un trait manuscrit bleu, et une plume jaune à pointe noire, sur un carré arrondi bleu-vert.
Lisible à 16 px (silhouette page + plume), vectoriel pour toutes les tailles. Aucune forme, paire de couleurs ni lettre empruntée à l'original. Les icônes d'outils sont dessinées en code (`plume/view/icons.py`), sans jeu d'icônes tiers.

## Ton

**Simple, chaleureux, précis.**
- simple, pas simpliste : des mots du quotidien (« Mettre à la corbeille », pas « Supprimer définitivement l'entrée »)
- chaleureux, pas familier à l'excès : tutoiement d'étudiant à étudiant
- précis, pas technique : on dit ce qui se passe (« Plume n'utilise ni compte ni Internet : tout reste sur ton ordinateur »)

Chaînes réécrites dans ce ton : accueil, choix du vault, « Annoter un PDF », messages d'erreur d'import (« PDF protégé par mot de passe : retire la protection puis réessaie »), avertissement du PDF compagnon, désinstallation (« notes et paramètres conservés »).

## Balayage des restes de l'original

`brand.json` liste les noms, domaine et couleurs à proscrire. Résultat (2026-11-14) :

```
plume/      Clean. Nothing of the original's name, domain or colours found.
packaging/  Clean.
tests/      Clean.
```

L'original n'est cité que dans `docs/` et `PROMPT_Plume.md` (recherche et cahier des charges), jamais dans l'application.
