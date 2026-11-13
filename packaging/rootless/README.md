# Rootless installation

This packaging uses the existing native **Codex 0.103.0** iOS build. It does
not rebuild Codex from current upstream source. The rootless package revision
is `0.103.0-1+rootless`, with architecture `iphoneos-arm64` and files under
`/var/jb`. Node.js and npm are unnecessary for this installation.

Build on macOS with `dpkg-deb` and `ldid` installed:

```sh
bash scripts/build-rootless-deb.sh /path/to/native-ios-codex
```

The input must be an arm64 iOS device executable. For this revision, use the
0.103.0 binary from the existing local `0.0.0-9` package. Update the control
file version when packaging a different native build. The build signs the
executable with the standard Procursus CLI entitlements and sets package
ownership to root.

Copy `dist/com.openai.codex-ios_0.103.0-1+rootless_iphoneos-arm64.deb` to the
phone, then run as root:

```sh
export PATH=/var/jb/usr/bin:/var/jb/bin:/var/jb/usr/sbin:/var/jb/sbin:$PATH
apt-get install git ripgrep ca-certificates
dpkg -i /var/tmp/com.openai.codex-ios_0.103.0-1+rootless_iphoneos-arm64.deb
```

Open NewTerm as `mobile`:

```sh
codex --version
codex login --device-auth
codex
```

For a future native iOS package, run `codex-update /absolute/path/to/package.deb`.
The helper checks package identity and rootless architecture, then uses sudo
if necessary. Updating the npm wrapper does not replace the iOS executable.
The launcher disables upstream startup update checks because upstream updates
do not supply an iOS binary; it does not change the reported native version.

Validated on an iPhone X running iOS 15.6.1 with a rootless palera1n bootstrap.
