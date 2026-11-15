---
name: fin-de-phase
description: Clôture une phase de FNote avant la PR — parité Replica, nettoyage, revue de code, dettes, revue de sécurité, puis bilan pour l'utilisateur (commandes, checklist stylet, points fragiles). À lancer à la fin de chaque phase, avant toute PR.
disable-model-invocation: true
---

# Fin de phase FNote

Argument : numéro de la phase (ex. `/fin-de-phase 1`). Branche courante = `phase-N-…`.

1. **Matrice** : mettre à jour la colonne `clone` de `docs/replica/features.csv` (`yes` / `partial` + note / `no`), puis `python3 docs/replica/matrice.py`.
2. **Parité** : skill `replica-diff` → `docs/replica/parite-phaseN.md` (score honnête, 5 priorités suivantes).
3. **Nettoyage** : skill `simplify` sur le diff de la branche (`git diff main...HEAD`).
4. **Revue** : skill `code-review` (ou `ponytail:ponytail-review`) sur le diff de la branche ; corriger ce qui est confirmé, en petits commits.
5. **Dettes** : skill `ponytail:ponytail-debt` → liste des `shortcut:` pour la PR.
6. **Sécurité** : skill `security-review` — vérifier en priorité : aucun import réseau, lecture des ZIP `.fnote` et des PDF importés sûre, aucune note/PDF/chemin de vault dans le dépôt (`git ls-files | grep -E '\.(fnote|pdf)$'`).
7. **Vérifs finales** : `.venv/bin/pytest -q` vert ; `QT_QPA_PLATFORM=offscreen timeout 4 .venv/bin/fnote` démarre ; `git push`.
8. **Bilan à l'utilisateur** (puis S'ARRÊTER et attendre son retour) :
   - commandes exactes pour lancer l'appli ;
   - checklist de test manuel précise (quoi faire, quoi observer) — socle commun dans `docs/tests.md` §2 + points propres à la phase ;
   - ce qui reste fragile ou non fait ;
   - score de parité et dettes.
9. **Seulement après validation explicite** : `gh pr create` (résumé + checklist + parité + dettes), merge dans `main`, tag `v0.N-phaseN`, push du tag.
