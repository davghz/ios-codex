#!/usr/bin/env bash
# Package the native iOS CLI and matching code-mode host without altering versions.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BINARY="${1:?Usage: build-rootless-deb.sh /path/to/native-ios-codex /path/to/native-ios-code-mode-host}"
CODE_MODE_HOST_BINARY="${2:?Provide the native iOS codex-code-mode-host executable}"
TEMPLATE="$ROOT/packaging/rootless"
VERSION="${3:-}"
PROVENANCE="${4:-$TEMPLATE/UPSTREAM.txt}"
OUTPUT_DIR="${CODEX_PACKAGE_OUTPUT_DIR:-$ROOT/dist}"
if [ "$#" -ne 2 ] && { [ "$#" -ne 4 ] || ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+-[0-9]+\+rootless$ ]]; }; then
    echo 'Provide a rootless Debian version and its upstream provenance file.' >&2
    exit 1
fi
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/codex-rootless.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

for tool in dpkg-deb ldid otool; do
    command -v "$tool" >/dev/null || { echo "Missing $tool" >&2; exit 1; }
done
# macOS and simulator executables cannot run on a jailbroken iPhone.
for PAYLOAD in "$BINARY" "$CODE_MODE_HOST_BINARY"; do
    [ -f "$PAYLOAD" ] || { echo "Missing native executable: $PAYLOAD" >&2; exit 1; }
    otool -l "$PAYLOAD" | awk '
    $1 == "cmd" { build = ($2 == "LC_BUILD_VERSION") }
    build && $1 == "platform" && $2 == 2 { ios = 1 }
    END { exit !ios }
' || { echo "Expected an iOS device executable (platform 2): $PAYLOAD" >&2; exit 1; }
done

mkdir -p "$STAGE/DEBIAN" "$STAGE/var/jb/usr/bin" \
    "$STAGE/var/jb/usr/libexec/codex-ios" \
    "$STAGE/var/jb/usr/share/doc/com.openai.codex-ios"
if [ -n "$VERSION" ]; then
    awk -v version="$VERSION" '/^Version:/ {$0 = "Version: " version} {print}' \
        "$TEMPLATE/DEBIAN/control" > "$STAGE/DEBIAN/control"
else
    cp "$TEMPLATE/DEBIAN/control" "$STAGE/DEBIAN/control"
fi
cp "$TEMPLATE/codex" "$TEMPLATE/codex-update" "$STAGE/var/jb/usr/bin/"
cp "$BINARY" "$STAGE/var/jb/usr/libexec/codex-ios/codex"
cp "$CODE_MODE_HOST_BINARY" "$STAGE/var/jb/usr/libexec/codex-ios/codex-code-mode-host"
cp "$TEMPLATE/LICENSE" "$TEMPLATE/NOTICE" \
    "$STAGE/var/jb/usr/share/doc/com.openai.codex-ios/"
cp "$PROVENANCE" "$STAGE/var/jb/usr/share/doc/com.openai.codex-ios/UPSTREAM.txt"
cp -R "$TEMPLATE/code-mode-host-licenses" \
    "$STAGE/var/jb/usr/share/doc/com.openai.codex-ios/"
ldid -S"$TEMPLATE/entitlements.plist" "$STAGE/var/jb/usr/libexec/codex-ios/codex"
ldid -S"$TEMPLATE/code-mode-host.entitlements.plist" "$STAGE/var/jb/usr/libexec/codex-ios/codex-code-mode-host"
chmod 755 "$STAGE/DEBIAN" "$STAGE/var/jb/usr/bin/"* \
    "$STAGE/var/jb/usr/libexec/codex-ios/"*
chmod 644 "$STAGE/DEBIAN/control"

VERSION="$(awk '/^Version:/ {print $2; exit}' "$STAGE/DEBIAN/control")"
mkdir -p "$OUTPUT_DIR"
OUTPUT="$OUTPUT_DIR/com.openai.codex-ios_${VERSION}_iphoneos-arm64.deb"
# Rootless bootstrap dpkg supports xz; compress both native executables so the
# distributable stays small enough for repository-hosted package artifacts.
dpkg-deb --root-owner-group -Zxz -z6 -b "$STAGE" "$OUTPUT"
echo "Built: $OUTPUT"
