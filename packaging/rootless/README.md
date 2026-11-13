# Rootless iOS installation

This package builds **Codex 0.168.0** from the actual upstream release source
for `aarch64-apple-ios`, with an iOS 15 deployment target. It installs under
`/var/jb` with package architecture `iphoneos-arm64`. Node.js and npm are
unnecessary for the native CLI.

The release tag, commit, archive checksum, and Rust version are recorded in
`UPSTREAM.txt`. The iOS patch is `patches/rootless/codex-0.168.0-ios.patch`.
The earlier 0.103.0 package remains archived in `dist`.

## Build

On macOS, install Xcode, rustup, `dpkg-deb`, and `ldid`. Point `SDKROOT` to an
iPhoneOS device SDK, such as a Theos `iPhoneOS18.5.sdk`:

```sh
SDKROOT=/path/to/iPhoneOS18.5.sdk bash scripts/build-rootless-ios-from-source.sh
SDKROOT=/path/to/iPhoneOS18.5.sdk bash scripts/build-ios-code-mode-host.sh \
  .build/codex-rust-v0.168.0
bash scripts/build-rootless-deb.sh \
  .build/codex-rust-v0.168.0/codex-rs/target/aarch64-apple-ios/release/codex \
  .build/codex-rust-v0.168.0/codex-rs/target/aarch64-apple-ios/release/codex-code-mode-host
```

The source builder verifies pinned source archive checksums, applies the iOS
patch, and installs Rust 1.95.0 with iOS standard libraries. It limits builds
to two jobs by default and disables LTO to reduce memory use. The standalone
code-mode host's unchanged V8 source is supplied from its exact pinned archive
for Cargo workspace metadata; that separate binary is not linked into the CLI.

Output: `dist/com.openai.codex-ios_0.168.0-2+rootless_iphoneos-arm64.deb`.

## Install and use

Copy the package to the phone, then run as root:

```sh
export PATH=/var/jb/usr/bin:/var/jb/bin:/var/jb/usr/sbin:/var/jb/sbin:$PATH
apt-get install git ripgrep ca-certificates
dpkg -i /var/tmp/com.openai.codex-ios_0.168.0-2+rootless_iphoneos-arm64.deb
```

Open NewTerm as `mobile`:

```sh
codex --version
codex login --device-auth
codex
```

For future native iOS packages, use `codex-update /absolute/path/to/package.deb`.
The helper checks package identity and rootless architecture and uses sudo if
needed. npm updates do not rebuild the native iOS executable. Upstream startup
update checks are disabled because official binary updates do not target iOS.
The launcher reports the actual compiled CLI version.

The launcher supplies the rootless bootstrap's maintained CA bundle at
`/var/jb/etc/ssl/cert.pem` when no certificate override is configured. This
lets both WebSocket and HTTPS transports verify their peer certificates.
Explicit `CODEX_CA_CERTIFICATE`, `SSL_CERT_FILE`, and `SSL_CERT_DIR` settings
remain unchanged.

## Platform features

The complete package requires the matching native iOS `codex-code-mode-host`
executable alongside the CLI, because modern model catalogs can require code
mode even when experimental feature flags are disabled. The package builder
checks that both inputs target iOS and installs them as sibling executables.
The helper uses a separate entitlement plist enabling extended virtual
addressing, which its V8 heap reservation requires on the tested iPhone X.
Native clipboard image paste is unavailable because arboard does not support
iOS. Terminal text paste remains available. The port does not provide macOS
Seatbelt sandboxing on iOS.

No TLS certificate-validation bypass or binary version-string replacement is
used by this build.

Native version/help output and recognition of existing ChatGPT authentication
were verified as `mobile` on an iPhone X running rootless iOS 15.6.1. A live
authenticated model request completed without WebSocket certificate errors or
HTTPS fallback. A read-only tool request executed `python3 --version` and a
fixed marker command successfully through the native Code Mode host. The
helper also passed JavaScript, persistent-state, and asynchronous tool callback
protocol tests on that device; see `CODE-MODE-HOST.md`.
