#!/usr/bin/env bash
# Installe FNote pour l'utilisateur courant (Fedora / GNOME), sans droits root.
# Le téléchargement des dépendances (PySide6, PyMuPDF, NumPy) n'a lieu qu'ici ;
# l'application elle-même ne se connecte jamais à Internet.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APPDIR="$DATA/fnote"
BIN="$HOME/.local/bin"

PY="${PYTHON:-python3}"
if ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
    echo "FNote a besoin de Python 3.12 ou plus récent (sudo dnf install python3)." >&2
    exit 1
fi

# Ancienne installation sous le nom « Plume » : remplacée par FNote (notes et paramètres gardés).
rm -rf "$DATA/plume"
rm -f "$BIN/plume" "$DATA/applications/plume.desktop" \
      "$DATA/icons/hicolor/scalable/apps/plume.svg" "$DATA/mime/packages/plume.xml"

echo "→ Environnement Python dans $APPDIR/venv"
"$PY" -m venv "$APPDIR/venv"
"$APPDIR/venv/bin/pip" install --quiet --upgrade pip
"$APPDIR/venv/bin/pip" install --quiet "$SRC"

echo "→ Lanceur, icône et type de fichier .fnote"
mkdir -p "$BIN" "$DATA/applications" "$DATA/icons/hicolor/scalable/apps" "$DATA/mime/packages"
ln -sf "$APPDIR/venv/bin/fnote" "$BIN/fnote"
install -m644 "$SRC/fnote/resources/fnote.svg" "$DATA/icons/hicolor/scalable/apps/fnote.svg"
sed "s|@EXEC@|$APPDIR/venv/bin/fnote|" "$SRC/packaging/fnote.desktop" > "$DATA/applications/fnote.desktop"
install -m644 "$SRC/packaging/fnote-mime.xml" "$DATA/mime/packages/fnote.xml"
update-mime-database "$DATA/mime" >/dev/null 2>&1 || true
update-desktop-database "$DATA/applications" >/dev/null 2>&1 || true
gtk-update-icon-cache -q -t "$DATA/icons/hicolor" >/dev/null 2>&1 || true

echo "✓ FNote est installé : cherche « FNote » dans les applications GNOME, ou lance « fnote »."
