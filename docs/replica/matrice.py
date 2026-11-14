"""Régénère fonctionnalites.md depuis features.csv : python3 docs/replica/matrice.py"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = {0: "Phase 0 — Squelette", 1: "Phase 1 — Moteur d'encre", 2: "Phase 2 — Outils de base",
         3: "Phase 3 — Lasso et images", 4: "Phase 4 — Formes et règle", 5: "Phase 5 — PDF",
         6: "Phase 6 — Confort et finition", 9: "Hors périmètre (skip)"}


def phase(row):
    m = re.match(r"phase (\d)", row["notes"])
    return int(m.group(1)) if m else 9


rows = list(csv.DictReader(open(os.path.join(HERE, "features.csv"), encoding="utf-8")))
out = ["# Matrice de fonctionnalités — Plume", "",
       "Checklist du projet. Source de vérité : `features.csv` (colonne `clone` : `no` → `partial` → `yes`, lue par `replica-diff`). "
       "Ce fichier est généré par `matrice.py`.", "",
       "Priorités : **must** = indispensable, **should** = attendu, **could** = bonus, **skip** = hors périmètre. "
       "Colonne *Samsung* : `partial` = existe sous une autre forme, `no` = propre à Plume (ou correctif issu de `fixes.md`).", ""]
for p in sorted({phase(r) for r in rows}):
    out += [f"## {NAMES[p]}", "", "| Fonctionnalité | Zone | Priorité | Samsung | Plume | Notes |", "|---|---|---|---|---|---|"]
    for r in rows:
        if phase(r) == p:
            note = re.sub(r"^phase \d\s*(—|;)?\s*", "", r["notes"])
            out.append(f"| {r['feature']} | {r['area']} | {r['priority']} | {r['original']} | {r['clone']} | {note} |")
    out.append("")
open(os.path.join(HERE, "fonctionnalites.md"), "w", encoding="utf-8").write("\n".join(out))
