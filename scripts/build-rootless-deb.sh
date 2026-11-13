#!/usr/bin/env bash
# Repackage an existing native iOS build, preserving its reported version.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BINARY="${1:?Usage: build-rootless-deb.sh /path/to/native-ios-codex}"
TEMPLATE="$ROOT/packaging/rootless"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/codex-rootless.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

for tool in dpkg-deb ldid otool; do
    command -v "$tool" >/dev/null || { echo "Missing $tool" >&2; exit 1; }
done
[ -f "$BINARY" ] || { echo 'Missing native binary' >&2; exit 1; }
# macOS and simulator executables cannot run on a jailbroken iPhone.
otool -l "$BINARY" | awk '
    $1 == "cmd" { build = ($2 == "LC_BUILD_VERSION") }
    build && $1 == "platform" && $2 == 2 { ios = 1 }
    END { exit !ios }
' || { echo 'Expected an iOS device executable (platform 2)' >&2; exit 1; }

mkdir -p "$STAGE/DEBIAN" "$STAGE/var/jb/usr/bin" \
    "$STAGE/var/jb/usr/libexec/codex-ios"
cp "$TEMPLATE/DEBIAN/control" "$STAGE/DEBIAN/control"
cp "$TEMPLATE/codex" "$TEMPLATE/codex-update" "$STAGE/var/jb/usr/bin/"
cp "$BINARY" "$STAGE/var/jb/usr/libexec/codex-ios/codex"
ldid -S"$TEMPLATE/entitlements.plist" "$STAGE/var/jb/usr/libexec/codex-ios/codex"
chmod 755 "$STAGE/DEBIAN" "$STAGE/var/jb/usr/bin/"* \
    "$STAGE/var/jb/usr/libexec/codex-ios/codex"
chmod 644 "$STAGE/DEBIAN/control"

VERSION="$(awk '/^Version:/ {print $2; exit}' "$STAGE/DEBIAN/control")"
mkdir -p "$ROOT/dist"
OUTPUT="$ROOT/dist/com.openai.codex-ios_${VERSION}_iphoneos-arm64.deb"
# gzip is supported by older rootless bootstrap dpkg versions.
dpkg-deb --root-owner-group -Zgzip -b "$STAGE" "$OUTPUT"
echo "Built: $OUTPUT"
