#!/usr/bin/env bash
# Désinstalle FNote. Tes notes (.fnote) et tes paramètres ne sont PAS supprimés.
set -euo pipefail
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -rf "$DATA/fnote"
rm -f "$HOME/.local/bin/fnote" "$DATA/applications/fnote.desktop" \
      "$DATA/icons/hicolor/scalable/apps/fnote.svg" "$DATA/mime/packages/fnote.xml"
update-mime-database "$DATA/mime" >/dev/null 2>&1 || true
update-desktop-database "$DATA/applications" >/dev/null 2>&1 || true
echo "✓ FNote est désinstallé (notes et paramètres conservés dans ~/.config/fnote et ton vault)."
