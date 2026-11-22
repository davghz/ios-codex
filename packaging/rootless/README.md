# Rootless iOS installation

The native package targets `aarch64-apple-ios` with an iOS 15 deployment target.
It installs under `/var/jb` with package architecture `iphoneos-arm64`. The
[latest release](https://github.com/davghz/ios-codex/releases/latest) includes
the `.deb` and its SHA256 checksum. Each package contains its upstream build
provenance at `/var/jb/usr/share/doc/com.openai.codex-ios/UPSTREAM.txt`.

## Install and use

In the download folder, run `sudo apt install ./FILE.deb` using the downloaded
package filename. APT resolves the rootless package dependencies.

Open NewTerm as `mobile` and verify the installation.

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

## Build Codex 0.168.0 from source

The pinned release tag, commit, archive checksum, and Rust version are recorded
in `UPSTREAM.txt`. On macOS, install Xcode, rustup, `dpkg-deb`, and `ldid`. Set
`SDKROOT` to an iPhoneOS device SDK such as Theos `iPhoneOS18.5.sdk`.

```sh
export SDKROOT=/path/to/iPhoneOS18.5.sdk
bash scripts/build-rootless-ios-from-source.sh
bash scripts/build-ios-code-mode-host.sh .build/codex-rust-v0.168.0
bash scripts/build-rootless-deb.sh \
  .build/codex-rust-v0.168.0/codex-rs/target/aarch64-apple-ios/release/codex \
  .build/codex-rust-v0.168.0/codex-rs/target/aarch64-apple-ios/release/codex-code-mode-host
```

The package is written to `dist/com.openai.codex-ios_0.168.0-2+rootless_iphoneos-arm64.deb`.
The build verifies the pinned source checksums and uses Rust 1.95.0. The
earlier 0.103.0 package is archived in `dist`.

## Platform features

On iOS, Codex polls watched paths every five seconds. Recursive skill and
workspace watches can cover more files than the shell's open-file limit.
Polling lets Codex monitor those trees while retaining the shell's limit.

The complete package requires the matching native iOS `codex-code-mode-host`
executable alongside the CLI, because modern model catalogs can require code
mode even when experimental feature flags are disabled. The package builder
checks that both inputs target iOS and installs them as sibling executables.
The helper uses a separate entitlement plist enabling extended virtual
addressing, which its V8 heap reservation requires on the tested iPhone X.
The foreground terminal handles the iOS pasteboard. NewTerm's iOS 15 input
build sends text as a bracketed paste and passes pasted images to the composer
as local PNG paths. The port does not provide macOS
Seatbelt sandboxing on iOS.

No TLS certificate-validation bypass or binary version-string replacement is
used by this build.

Codex 0.168.0 version/help output and recognition of existing ChatGPT
authentication were verified as `mobile` on an iPhone X running rootless
iOS 15.6.1. A live
authenticated model request completed without WebSocket certificate errors or
HTTPS fallback. A read-only tool request executed `python3 --version` and a
fixed marker command successfully through the native Code Mode host. The
helper also passed JavaScript, persistent-state, and asynchronous tool callback
protocol tests on that device; see `CODE-MODE-HOST.md`.
