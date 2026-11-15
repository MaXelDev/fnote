# Déploiement — FNote v1.0.0

Adapté de `replica-deploy` : une application de bureau 100 % locale, donc ni serveur, ni domaine, ni DNS, ni Stripe, ni OAuth, ni e-mail, ni boutique mobile. « Déployer » veut dire ici : installer sur le PC de l'utilisateur, et publier une version taguée sur GitHub.

## Contrôle préalable (2026-11-14)

| contrôle | résultat |
|---|---|
| tests automatiques (`pytest -q`) | ✅ 122 réussis |
| parité (`parity.py`) | ✅ 100/100, 44/44 indispensables |
| restes de l'original (`sweep.py`, `fnote/` et `packaging/`) | ✅ propre |
| lanceur (`desktop-file-validate`) | ✅ valide |
| aucun import réseau (`tests/test_no_network.py`) | ✅ |
| démarrage réel sous Wayland | ✅ sans erreur (seuls des avertissements Qt du portail, sans effet) |
| installation (`./install.sh`) | ✅ venv dans `~/.local/share/fnote`, lanceur GNOME, icône, type MIME `application/x-fnote` reconnu |
| version installée hors du dépôt | ✅ démarre et trouve ses ressources |
| aucune note, PDF ni chemin personnel dans git | ✅ |

## Distribution

- **Installation locale** : `./install.sh` (sans root), `./uninstall.sh` (garde notes et paramètres).
- **GitHub Release** : `v1.0.0` sur `MaXelDev/fnote` (dépôt privé), notes de version ci-dessous.
- **Flatpak** : non fait. Il faudrait générer les modules pip de PySide6 et PyMuPDF (`flatpak-pip-generator`), qui pèsent plusieurs centaines de Mo, et régler la question de l'AGPL de PyMuPDF. Ce n'est pas « simple », donc reporté ; l'installation locale couvre l'usage visé.

## À surveiller la première semaine

- **Sensation d'écriture au S Pen** : retard perçu, finesse des traits. Si besoin, *Paramètres → Sensibilité*. Lancer `fnote --debug-perf` pour voir les fps et le temps de rendu.
- **Proximité du stylet sous GNOME** : le curseur doit disparaître à l'approche. Sinon, `fnote --debug-tablet` montre si les événements de proximité arrivent.
- **Bouton latéral** : il doit activer la gomme quand on le maintient. Le diagnostic montre quel bouton Qt reçoit.
- **Grosses notes (30 pages et plus)** : fluidité du défilement (`--debug-perf`).
