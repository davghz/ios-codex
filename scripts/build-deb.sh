#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKGROOT="$ROOT/packaging/debian"
OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"

VERSION="$(/bin/grep '^Version:' "$PKGROOT/DEBIAN/control" | /bin/sed -n '1s/^Version:[[:space:]]*//p')"
if [ -z "$VERSION" ]; then
  echo "Unable to parse Version from $PKGROOT/DEBIAN/control" >&2
  exit 1
fi
PKG="com.openai.codex-ios_${VERSION}_iphoneos-arm.deb"
dpkg-deb -b "$PKGROOT" "$OUTDIR/$PKG"

echo "Built: $OUTDIR/$PKG"
