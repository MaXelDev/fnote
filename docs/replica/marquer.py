"""Met à jour la colonne clone de features.csv : python3 docs/replica/marquer.py yes "préfixe 1" "préfixe 2" …"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(HERE, "features.csv")
value, prefixes = sys.argv[1], sys.argv[2:]
rows = list(csv.DictReader(open(path, encoding="utf-8")))
hit = set()
for r in rows:
    for p in prefixes:
        if r["feature"].startswith(p):
            r["clone"] = value
            hit.add(p)
missing = set(prefixes) - hit
w = csv.DictWriter(open(path, "w", newline="", encoding="utf-8"), fieldnames=rows[0].keys())
w.writeheader()
w.writerows(rows)
print(f"{len(hit)} préfixes appliqués" + (f" ; introuvables : {sorted(missing)}" if missing else ""))
