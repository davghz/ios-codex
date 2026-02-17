#!/usr/bin/env bash
set -euo pipefail

# Build iOS Codex binary from upstream source + this repo patch.
# Usage:
#   scripts/build-ios-binary.sh /path/to/codex-upstream

UPSTREAM_DIR="${1:-}"
if [[ -z "$UPSTREAM_DIR" ]]; then
  echo "Usage: $0 /path/to/codex-upstream" >&2
  exit 1
fi

PATCH_FILE="$(cd "$(dirname "$0")/.." && pwd)/patches/0001-ios-codex.patch"

cd "$UPSTREAM_DIR"
git apply --check "$PATCH_FILE" || true
git apply "$PATCH_FILE" || true

cd codex-rs
rustup target add --toolchain 1.93.0-aarch64-apple-darwin aarch64-apple-ios || true
cargo build -p codex-cli --release --target aarch64-apple-ios

echo "Built: $UPSTREAM_DIR/codex-rs/target/aarch64-apple-ios/release/codex"
