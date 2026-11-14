# Parité finale — v1.0.0

Date : 2026-11-14. Score calculé par `replica-diff/parity.py` sur `features.csv` (fonctions présentes dans l'original, hors `skip`, pondérées must 3 / should 2 / could 1).

| phase | parité | must faits |
|---|---|---|
| 0 — squelette | 3,1 | 1 / 44 |
| 1 — encre | 41,4 | 18 / 44 |
| 2 — outils | 62,0 | 28 / 44 |
| 3 — lasso, images | 78,1 | 34 / 44 |
| 4 — formes, règle | 83,0 | 36 / 44 |
| 5 — PDF | 90,4 | 40 / 44 |
| 6 — finition | **100,0** | **44 / 44** |

Les 7 correctifs issus des avis réels (`fixes.md`) et les fonctions propres à Plume (format `.plume`, export compagnon Obsidian, `--debug-tablet`, `--debug-perf`) sont aussi faits. Hors périmètre, volontairement : cloud, OCR, texte tapé, audio, assistant IA, collaboration, Windows/macOS.

**Verdict : meilleur que l'original sur la cible visée.** Toutes les fonctions indispensables sont là, et les défauts les plus cités des alternatives libres sont corrigés : encre en retard, curseur affiché, surligneur à opacité irrégulière, gomme qui saute des traits, outils éparpillés. S'y ajoute ce que l'original ne fait pas : règle virtuelle, fichiers dans le vault Obsidian, 100 % hors ligne.

**Ce qu'un score ne mesure pas** : la sensation d'écriture réelle au S Pen (latence perçue, calibrage de la pression) ne se vérifie qu'à la main, sur le matériel. Les réglages par défaut sont raisonnables ; la sensibilité se règle dans *Paramètres*.
