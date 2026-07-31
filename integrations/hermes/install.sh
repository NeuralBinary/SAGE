#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET_HOME=${1:-${HERMES_HOME:-$HOME/.hermes}}
TARGET="$TARGET_HOME/plugins/sage"
mkdir -p "$TARGET"
cp "$ROOT/sage/__init__.py" "$TARGET/__init__.py"
cp "$ROOT/sage/plugin.yaml" "$TARGET/plugin.yaml"
printf '%s\n' "Installed SAGE Hermes plugin to $TARGET"
printf '%s\n' "Enable it with: hermes plugins enable sage"
