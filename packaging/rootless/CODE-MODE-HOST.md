# Native Code Mode host on iOS

Codex 0.168.0 Code Mode uses a separate `codex-code-mode-host` executable.
Models whose catalog entry requires Code Mode need this host; disabling its
feature does not select a Node.js backend. This port builds the genuine upstream
host and protocol implementation rather than changing model metadata.

Build the pinned CLI source first, then build the helper from that prepared source:

```sh
bash scripts/build-rootless-ios-from-source.sh
bash scripts/build-ios-code-mode-host.sh /path/to/codex-rust-v0.168.0
```

The helper builder verifies and uses the official Rusty V8 **152.2.0** native
`aarch64-apple-ios` archive and matching Rust bindings. The pinned OpenAI Rusty
V8 fork and that release have identical C++ bindings, V8 submodule commit, and
third-party source tree. Both downloaded artifacts are pinned by SHA256.

The published iOS archive contains 1,596 device Mach-O objects with a minimum
iOS version of 14.0. The Rust helper targets iOS 15.0. Its iOS dependency
configuration matches the artifact's uncompressed-pointer ABI and disables V8's
internal desktop heap sandbox feature on this target. Desktop targets keep their
original V8 sandbox feature. The iOS runtime defaults to the artifact's jitless
mode. Codex's tool protocol, approvals, and operating-system sandbox settings
remain unchanged.

The helper must be signed with `code-mode-host.entitlements.plist`. In addition
to standard CLI entitlements, it requests extended virtual addressing so V8's
Oilpan heap can reserve its address cage. On an iPhone X running iOS 15.6.1,
standard CLI signing alone aborted at the first cell with an Oilpan CagedHeap
reservation error; the extended-virtual-addressing entitlement resolved it.
No JIT entitlement is needed for this helper.

Install the helper beside the native CLI:

`/var/jb/usr/libexec/codex-ios/codex-code-mode-host`

The package builder must use the helper-specific entitlement file when signing
the packaged executable. Retain `code-mode-host-licenses/` in the package's
documentation directory when redistributing the helper.

On-device validation, as `mobile`, uses:

```sh
python3 scripts/smoke-ios-code-mode-host.py
```

The smoke test exercises actual framed protocol negotiation, session creation,
native V8 JavaScript execution, persistent session storage, an asynchronous
nested tool callback, and orderly session/host shutdown. It passed on an iPhone X
running rootless palera1n and iOS 15.6.1.
