#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKGROOT="$ROOT/packaging/debian"
OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"

PKG="com.openai.codex-ios_0.0.0-2_iphoneos-arm.deb"
dpkg-deb -b "$PKGROOT" "$OUTDIR/$PKG"

echo "Built: $OUTDIR/$PKG"
