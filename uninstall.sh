#!/usr/bin/env bash
# Désinstalle Plume. Tes notes (.plume) et tes paramètres ne sont PAS supprimés.
set -euo pipefail
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -rf "$DATA/plume"
rm -f "$HOME/.local/bin/plume" "$DATA/applications/plume.desktop" \
      "$DATA/icons/hicolor/scalable/apps/plume.svg" "$DATA/mime/packages/plume.xml"
update-mime-database "$DATA/mime" >/dev/null 2>&1 || true
update-desktop-database "$DATA/applications" >/dev/null 2>&1 || true
echo "✓ Plume est désinstallé (notes et paramètres conservés dans ~/.config/plume et ton vault)."
