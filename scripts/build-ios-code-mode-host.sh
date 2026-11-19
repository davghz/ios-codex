#!/usr/bin/env bash
# Build the actual upstream Code Mode host with its published native iOS V8.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="${1:?Usage: build-ios-code-mode-host.sh /path/to/prepared/codex-rust-v0.168.0}"
SOURCE="$(cd "$SOURCE" && pwd -P)"
ARTIFACTS="${CODEX_HOST_ARTIFACT_DIR:-$ROOT/.build/code-mode-host}"
V8_VERSION=152.2.0
V8_ARCHIVE=librusty_v8_release_aarch64-apple-ios.a.gz
V8_BINDING=src_binding_release_aarch64-apple-ios.rs
V8_ARCHIVE_SHA256=9d2e64a2409a4b812e3d1d29da3e0a06b020c8ab1e0fed6fd9342523ba8b757c
V8_BINDING_SHA256=b9d5652ebca515eb2bf4c2ee4a6551b2567117b5aa720f430d2032616dd7e3b5
PATCH="$ROOT/patches/rootless/codex-code-mode-host-0.168.0-ios.patch"

for tool in curl shasum rustup git xcrun ldid; do
    command -v "$tool" >/dev/null || { echo "Missing $tool" >&2; exit 1; }
done
if [ ! -f "$SOURCE/vendor/rusty_v8/Cargo.toml" ]; then
    echo 'First prepare the pinned release with scripts/build-rootless-ios-from-source.sh.' >&2
    exit 1
fi
mkdir -p "$ARTIFACTS"
ARTIFACTS="$(cd "$ARTIFACTS" && pwd -P)"
for file in "$V8_ARCHIVE" "$V8_BINDING"; do
    if [ ! -f "$ARTIFACTS/$file" ]; then
        curl -fL --retry 3 "https://github.com/denoland/rusty_v8/releases/download/v$V8_VERSION/$file" \
            -o "$ARTIFACTS/$file"
    fi
done
printf '%s  %s\n' "$V8_ARCHIVE_SHA256" "$ARTIFACTS/$V8_ARCHIVE" | shasum -a 256 -c -
printf '%s  %s\n' "$V8_BINDING_SHA256" "$ARTIFACTS/$V8_BINDING" | shasum -a 256 -c -

if git -C "$SOURCE" apply --reverse --check "$PATCH" >/dev/null 2>&1; then
    : # The compatibility patch is already applied.
elif git -C "$SOURCE" apply --check "$PATCH"; then
    git -C "$SOURCE" apply "$PATCH"
else
    echo 'Source does not match the pinned Code Mode runtime compatibility patch.' >&2
    exit 1
fi

export RUSTY_V8_ARCHIVE="$ARTIFACTS/$V8_ARCHIVE"
export RUSTY_V8_ARCHIVE_SHA256="$V8_ARCHIVE_SHA256"
export RUSTY_V8_SRC_BINDING_PATH="$ARTIFACTS/$V8_BINDING"
bash "$ROOT/scripts/build-ios-cargo.sh" \
    "$SOURCE" 1.95.0 codex-code-mode-host codex-code-mode-host
ldid -S"$ROOT/packaging/rootless/code-mode-host.entitlements.plist" \
    "$SOURCE/codex-rs/target/aarch64-apple-ios/release/codex-code-mode-host"
echo "Built: $SOURCE/codex-rs/target/aarch64-apple-ios/release/codex-code-mode-host"
