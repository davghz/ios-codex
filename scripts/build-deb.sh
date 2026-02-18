#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKGROOT="$ROOT/packaging/debian"
OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"

VERSION="$(awk '/^Version:/{print $2; exit}' "$PKGROOT/DEBIAN/control")"
PKG="com.openai.codex-ios_${VERSION}_iphoneos-arm.deb"
dpkg-deb -b "$PKGROOT" "$OUTDIR/$PKG"

echo "Built: $OUTDIR/$PKG"
