#!/usr/bin/env bash
# Installe Plume pour l'utilisateur courant (Fedora / GNOME), sans droits root.
# Le téléchargement des dépendances (PySide6, PyMuPDF, NumPy) n'a lieu qu'ici ;
# l'application elle-même ne se connecte jamais à Internet.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APPDIR="$DATA/plume"
BIN="$HOME/.local/bin"

PY="${PYTHON:-python3}"
if ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
    echo "Plume a besoin de Python 3.12 ou plus récent (sudo dnf install python3)." >&2
    exit 1
fi

echo "→ Environnement Python dans $APPDIR/venv"
"$PY" -m venv "$APPDIR/venv"
"$APPDIR/venv/bin/pip" install --quiet --upgrade pip
"$APPDIR/venv/bin/pip" install --quiet "$SRC"

echo "→ Lanceur, icône et type de fichier .plume"
mkdir -p "$BIN" "$DATA/applications" "$DATA/icons/hicolor/scalable/apps" "$DATA/mime/packages"
ln -sf "$APPDIR/venv/bin/plume" "$BIN/plume"
install -m644 "$SRC/plume/resources/plume.svg" "$DATA/icons/hicolor/scalable/apps/plume.svg"
sed "s|@EXEC@|$APPDIR/venv/bin/plume|" "$SRC/packaging/plume.desktop" > "$DATA/applications/plume.desktop"
install -m644 "$SRC/packaging/plume-mime.xml" "$DATA/mime/packages/plume.xml"
update-mime-database "$DATA/mime" >/dev/null 2>&1 || true
update-desktop-database "$DATA/applications" >/dev/null 2>&1 || true
gtk-update-icon-cache -q -t "$DATA/icons/hicolor" >/dev/null 2>&1 || true

echo "✓ Plume est installé : cherche « Plume » dans les applications GNOME, ou lance « plume »."
