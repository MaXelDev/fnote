# Parité — fin de phase 0

Date : 2026-11-14. Aucune comparaison de captures (pas de capture de l'original dans le dépôt). Le score ne compte que les fonctions **présentes dans l'original** (`original` = yes/partial), hors `skip`, pondérées must 3 / should 2 / could 1.

## Score : 3,1 / 100

59 fonctions comptées ; must-haves : 1 sur 44.
**Verdict : pas encore utilisable** — attendu : la phase 0 pose les fondations, sans outil d'écriture.

## Fait en phase 0

Propre à Plume (hors score) : format `.plume` versionné, sauvegarde atomique, lecture sécurisée (liste blanche, plafonds de taille, validation), paramètres XDG, fenêtre `--debug-tablet` (pression, proximité, fréquence, échelle, décalage stylet/pointeur), garde-fou « aucun import réseau ».
Partiel : plein écran F11, thème suivant le système.

## Les cinq prochaines priorités (phase 1)

1. Stylo à pression avec courbe réglable
2. Tracé incrémental sans retard + cache par page
3. Curseur caché en proximité + point de survol + rejet de la paume
4. Défilement et zoom au doigt / à la souris
5. Undo/redo dans l'interface + sauvegarde automatique

Liste complète des manques, dans l'ordre : `python3 ~/.claude/skills/replica-diff/parity.py docs/replica/features.csv`.
