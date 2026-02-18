# iOS Codex (arm64) Port

Latest OpenAI Codex CLI patched for `process.platform=ios` with a native `aarch64-apple-ios` binary and packaged as a `.deb` for jailbroken iOS devices.

## What This Repo Includes

- `dist/com.openai.codex-ios_0.0.0-6_iphoneos-arm.deb`
- Upstream patch set: `patches/0001-ios-codex.patch`
- Modified source files (for transparency):
  - `source/codex-rs/Cargo.toml`
  - `source/codex-rs/process-hardening/src/lib.rs`
  - `source/codex-rs/cli/src/main.rs`
  - `source/codex-rs/tui/src/terminal_palette.rs`
- Build scripts:
  - `scripts/build-ios-binary.sh`
  - `scripts/build-deb.sh`

## Source Base

Upstream repository: `https://github.com/openai/codex`

Base commit used for this port is in `UPSTREAM_COMMIT.txt`.

## Build Requirements

- macOS host
- Rust toolchain (required to compile Codex):

```bash
curl https://sh.rustup.rs -sSf | sh
rustup toolchain install 1.93.0
rustup target add --toolchain 1.93.0 aarch64-apple-ios
```

- Theos with a device SDK for the iOS version you are targeting (for jailbroken hardware builds, not simulator builds), for example:
  - `iPhoneOS13.7.sdk`
  - `iPhoneOS14.8.sdk`
  - `iPhoneOS15.x.sdk`

## Device Requirements

- Jailbroken iOS arm64 device (tested on iOS 13.x; may also work on other iOS versions)
- Node.js installed on-device
- Latest npm Codex installed on-device:

```bash
npm install -g @openai/codex@latest
```

## Install `.deb` on iOS

Copy the package:

```bash
scp dist/com.openai.codex-ios_0.0.0-6_iphoneos-arm.deb root@<DEVICE_IP>:/var/root/
```

Install on device:

```bash
ssh root@<DEVICE_IP>
dpkg -i /var/root/com.openai.codex-ios_0.0.0-6_iphoneos-arm.deb
```

Verify as `mobile` (NewTerm2 user):

```bash
su mobile -c 'codex --version'
su mobile -c 'codex --help'
```

## Build iOS Binary From Source (Theos SDK Workflow)

Use this workflow for real jailbroken-device targets. It uses a Theos `iPhoneOS*.sdk` sysroot instead of simulator tooling.

Clone upstream source:

```bash
git clone https://github.com/openai/codex codex-upstream
cd codex-upstream
# Checkout the commit from ../ios-codex/UPSTREAM_COMMIT.txt
```

Build with Rust + Theos SDK:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
export THEOS="/path/to/theos"
export SDKROOT="$THEOS/sdks/iPhoneOS<MAJOR.MINOR>.sdk"
export IPHONEOS_DEPLOYMENT_TARGET="<MAJOR.MINOR>"

cd /path/to/ios-codex
./scripts/build-ios-binary.sh /path/to/codex-upstream
```

Notes:

- Pick the `iPhoneOS<MAJOR.MINOR>.sdk` version that matches your device target version.
- This repository targets jailbroken devices; treat Theos SDK builds as the default path.

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

`dist/com.openai.codex-ios_0.0.0-6_iphoneos-arm.deb`

## How the Package Works

`postinst` runs `/usr/local/libexec/codex-ios-repair` which patches/configures:

- `/usr/local/lib/node_modules/@openai/codex/bin/codex.js`
- `/usr/local/bin/node` (forces iOS-safe Node flags)
- `/usr/local/bin/codex` (stable launcher with paste-safe config defaults)
- `/usr/bin/codex` (shim for minimal PATH shells)
- `/usr/local/bin/codex-update` (safe update helper)
- `/usr/local/lib/codex-ios/codex` (canonical iOS binary backup outside npm paths)

Changes applied:

- Adds target mapping for `aarch64-apple-ios`
- Adds `case "ios"` platform dispatch
- Forces `--no-alt-screen` and `disable_paste_burst=true` to reduce NewTerm2 TUI/paste glitches
- Signs `codex` and `node22` with `ldid -S` when available

## Future Updates (Safe Path)

Do not run plain `npm install -g @openai/codex@latest` directly.

Use:

```bash
su -c '/usr/local/bin/codex-update'
```

What `codex-update` does:

- Updates npm Codex with retries under stable Node flags
- Replays all iOS patches automatically
- Restores stable launch wrappers if npm replaced symlinks
- Preserves/repairs the iOS native binary payload
- Makes `codex --version` report the npm package version (instead of stale `0.0.0`)

You can also specify an explicit package/version:

```bash
su -c '/usr/local/bin/codex-update @openai/codex@0.103.0'
```

## Notes

- This repo only ports **Codex**. It does not make Claude Code stable on iOS 13.
- `path/rg` in this package is a minimal shim (`grep`) to satisfy tool path expectations.
- Compatibility note: iOS 13.x is the validated baseline. Other jailbreakable iOS versions may work, but are not yet exhaustively tested.
