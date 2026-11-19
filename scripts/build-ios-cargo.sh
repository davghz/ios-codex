#!/usr/bin/env bash
set -euo pipefail

SOURCE="${1:?Provide a prepared Codex source directory}"
RUST_TOOLCHAIN="${2:?Provide a Rust toolchain version}"
PACKAGE="${3:?Provide a Cargo package name}"
BINARY="${4:?Provide a Cargo binary name}"
shift 4

export SDKROOT="${SDKROOT:-${THEOS:-$HOME/theos}/sdks/iPhoneOS18.5.sdk}"
[ -d "$SDKROOT" ] || { echo 'Set SDKROOT to an iPhoneOS device SDK.' >&2; exit 1; }
SDKROOT="$(cd "$SDKROOT" && pwd -P)"
CLANG="$(xcrun --sdk macosx -f clang)"
# Bypass the system cc shim when a custom Theos SDK is used.
export CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER="$CLANG"
export CARGO_TARGET_AARCH64_APPLE_IOS_LINKER="$CLANG"
export IPHONEOS_DEPLOYMENT_TARGET=15.0
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"
export CARGO_PROFILE_RELEASE_LTO=false
export CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16
export CARGO_PROFILE_RELEASE_DEBUG=0

if ! rustup target list --installed --toolchain "$RUST_TOOLCHAIN" 2>/dev/null | grep -qx aarch64-apple-ios; then
    rustup toolchain install "$RUST_TOOLCHAIN" --profile minimal --target aarch64-apple-ios
fi
export RUSTC="$(rustup which --toolchain "$RUST_TOOLCHAIN" rustc)"
export RUSTDOC="$(rustup which --toolchain "$RUST_TOOLCHAIN" rustdoc)"
cd "$SOURCE"
rustup run "$RUST_TOOLCHAIN" cargo build --release --target aarch64-apple-ios \
    --manifest-path codex-rs/Cargo.toml -p "$PACKAGE" --bin "$BINARY" "$@"
