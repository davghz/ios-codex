# iOS Codex (arm64) Port

Latest OpenAI Codex CLI patched for `process.platform=ios` with a native `aarch64-apple-ios` binary and packaged as a `.deb` for jailbroken iOS devices.

## What This Repo Includes

- `dist/com.openai.codex-ios_0.0.0-1_iphoneos-arm.deb`
- Upstream patch set: `patches/0001-ios-codex.patch`
- Modified source files (for transparency):
  - `source/codex-rs/Cargo.toml`
  - `source/codex-rs/process-hardening/src/lib.rs`
  - `source/codex-rs/cli/src/main.rs`
- Build scripts:
  - `scripts/build-ios-binary.sh`
  - `scripts/build-deb.sh`

## Source Base

Upstream repository: `https://github.com/openai/codex`

Base commit used for this port is in `UPSTREAM_COMMIT.txt`.

## Device Requirements

- Jailbroken iOS arm64 device (tested on iOS 13.x)
- Node.js installed on-device
- Latest npm Codex installed on-device:

```bash
npm install -g @openai/codex@latest
```

## Install `.deb` on iOS

Copy the package:

```bash
scp dist/com.openai.codex-ios_0.0.0-1_iphoneos-arm.deb root@<DEVICE_IP>:/var/root/
```

Install on device:

```bash
ssh root@<DEVICE_IP>
dpkg -i /var/root/com.openai.codex-ios_0.0.0-1_iphoneos-arm.deb
```

Verify as `mobile` (NewTerm2 user):

```bash
su mobile -c 'codex --version'
su mobile -c 'codex --help'
```

## Build iOS Binary From Source

On macOS with Xcode + Rust toolchain:

```bash
git clone https://github.com/openai/codex codex-upstream
cd codex-upstream
# Checkout the commit from ../ios-codex/UPSTREAM_COMMIT.txt
```

Apply patch and build:

```bash
cd /path/to/ios-codex
./scripts/build-ios-binary.sh /path/to/codex-upstream
```

Binary output:

`/path/to/codex-upstream/codex-rs/target/aarch64-apple-ios/release/codex`

## Build `.deb`

After placing the built binary at:

`packaging/debian/usr/local/lib/node_modules/@openai/codex/vendor/aarch64-apple-ios/codex/codex`

Build package:

```bash
./scripts/build-deb.sh
```

Output:

`dist/com.openai.codex-ios_0.0.0-1_iphoneos-arm.deb`

## How the Package Works

`postinst` patches:

- `/usr/local/lib/node_modules/@openai/codex/bin/codex.js`

Changes applied:

- Adds target mapping for `aarch64-apple-ios`
- Adds `case "ios"` platform dispatch
- Installs local vendor binary path used by launcher fallback

## Notes

- This repo only ports **Codex**. It does not make Claude Code stable on iOS 13.
- `path/rg` in this package is a minimal shim (`grep`) to satisfy tool path expectations.
