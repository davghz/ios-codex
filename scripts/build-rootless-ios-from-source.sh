#!/usr/bin/env bash
# Build the pinned upstream release as a genuine iOS device executable.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION=0.168.0
RUST_TOOLCHAIN=1.95.0
ARCHIVE_SHA256=db0dd491ff70089025d430647e846b251ccfae50ae63aebc766775350c5f1cb0
V8_REVISION=90a65f887a0c0f048f3784afbcb320b373c8a2e0
V8_ARCHIVE_SHA256=b0b188d1f1d851abd78337818a28a15e84f143b082ce966976e9206617684373
BUILD_ROOT="${CODEX_BUILD_ROOT:-$ROOT/.build}"
SOURCE="$BUILD_ROOT/codex-rust-v$VERSION"
ARCHIVE="$BUILD_ROOT/codex-$VERSION.tar.gz"
PATCH="$ROOT/patches/rootless/codex-$VERSION-ios.patch"

for tool in curl tar shasum rustup git xcrun; do
    command -v "$tool" >/dev/null || { echo "Missing $tool" >&2; exit 1; }
done
mkdir -p "$BUILD_ROOT"
if [ ! -f "$ARCHIVE" ]; then
    curl -fL --retry 3 "https://codeload.github.com/openai/codex/tar.gz/refs/tags/rust-v$VERSION" -o "$ARCHIVE"
fi
printf '%s  %s\n' "$ARCHIVE_SHA256" "$ARCHIVE" | shasum -a 256 -c -
if [ ! -d "$SOURCE" ]; then
    tar -xzf "$ARCHIVE" -C "$BUILD_ROOT"
fi
# The CLI does not link the separate code-mode host. Resolving the Cargo
# workspace still reads its V8 manifest; use the exact pinned source archive
# so Cargo need not clone unused Chromium submodules merely for that metadata.
if [ ! -d "$SOURCE/vendor/rusty_v8" ]; then
    V8_ARCHIVE="$BUILD_ROOT/rusty-v8-$V8_REVISION.tar.gz"
    curl -fL --retry 3 "https://codeload.github.com/openai-oss-forks/rusty_v8/tar.gz/$V8_REVISION" -o "$V8_ARCHIVE"
    printf '%s  %s\n' "$V8_ARCHIVE_SHA256" "$V8_ARCHIVE" | shasum -a 256 -c -
    mkdir -p "$SOURCE/vendor"
    tar -xzf "$V8_ARCHIVE" -C "$SOURCE/vendor"
    mv "$SOURCE/vendor/rusty_v8-$V8_REVISION" "$SOURCE/vendor/rusty_v8"
fi
if git -C "$SOURCE" apply --check "$PATCH"; then
    git -C "$SOURCE" apply "$PATCH"
elif ! git -C "$SOURCE" apply --reverse --check "$PATCH"; then
    echo 'Source does not match the pinned release and iOS patch.' >&2
    exit 1
fi

export SDKROOT="${SDKROOT:-${THEOS:-$HOME/theos}/sdks/iPhoneOS18.5.sdk}"
[ -d "$SDKROOT" ] || { echo 'Set SDKROOT to an iPhoneOS device SDK.' >&2; exit 1; }
SDKROOT="$(cd "$SDKROOT" && pwd -P)"
CLANG="$(xcrun --sdk macosx -f clang)"
# Explicit compiler paths avoid the system cc shim treating a custom Theos
# SDK symlink as an Xcode SDK identifier when linking host build scripts.
export CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER="$CLANG"
export CARGO_TARGET_AARCH64_APPLE_IOS_LINKER="$CLANG"
export IPHONEOS_DEPLOYMENT_TARGET=15.0
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"
export CARGO_PROFILE_RELEASE_LTO=false
export CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16
export CARGO_PROFILE_RELEASE_DEBUG=0
rustup toolchain install "$RUST_TOOLCHAIN" --profile minimal --target aarch64-apple-ios
export RUSTC="$(rustup which --toolchain "$RUST_TOOLCHAIN" rustc)"
export RUSTDOC="$(rustup which --toolchain "$RUST_TOOLCHAIN" rustdoc)"
(
    cd "$SOURCE"
    rustup run "$RUST_TOOLCHAIN" cargo build --release --target aarch64-apple-ios \
        --manifest-path codex-rs/Cargo.toml -p codex-cli --bin codex
)
echo "Built: $SOURCE/codex-rs/target/aarch64-apple-ios/release/codex"
