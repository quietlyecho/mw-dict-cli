#!/bin/bash

set -e

INSTALL_DIR="$HOME/.local/bin"
REPO_URL="https://raw.githubusercontent.com/quietlyecho/mw-dict-cli/main/lookup_mw_dict.py"

mkdir -p "$INSTALL_DIR"
curl -fsSL "$REPO_URL" -o "$INSTALL_DIR/mw"
chmod +x "$INSTALL_DIR/mw"

echo "Installed to $INSTALL_DIR/mw"
echo "Make sure $INSTALL_DIR is in your PATH"
