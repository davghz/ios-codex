#!/usr/bin/env python3
"""Build the rootless package from a published upstream Rust release tag."""

from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib

from rootless_version import package_name, package_revision


ROOT = Path(__file__).resolve().parents[1]
FORK = "openai-oss-forks/rusty_v8"
V8_REPO = "denoland/rusty_v8"
V8_TARGET = "aarch64-apple-ios"
VERSION = r"[0-9]+\.[0-9]+\.[0-9]+"
ABI_FILES = (".gn", "BUILD.gn", "build.rs", "src/binding.cc", "third_party", "tools", "v8")


def github(endpoint):
    return json.loads(subprocess.check_output(["gh", "api", endpoint]))


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(url, path):
    subprocess.run(["curl", "-fsSL", "--retry", "3", url, "-o", path], check=True)
    return sha256(path)


def unpack_source(repo, commit, archive, destination):
    digest = download(f"https://codeload.github.com/{repo}/tar.gz/{commit}", archive)
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(["tar", "-xzf", archive, "--strip-components=1", "-C", destination], check=True)
    return digest


def read_toml(path):
    return tomllib.loads(path.read_text())


def update_workspace_lockfile(path, version):
    # The release tag sets workspace.package.version while Cargo.lock still
    # carries 0.0.0 for local crates. Keep registry and Git entries untouched.
    pattern = r'^(\[\[package\]\]\nname = "[^"\n]+"\nversion = ")0\.0\.0("\n)(?!source = )'
    text = re.sub(pattern, rf'\g<1>{version}\g<2>', path.read_text(), flags=re.MULTILINE)
    path.write_text(text)


def prepare_v8(source, work, workspace):
    manifest = read_toml(workspace / "Cargo.toml")
    v8 = manifest["patch"]["crates-io"]["v8"]
    fork_url = f"https://github.com/{FORK}.git"
    if v8.get("git") != fork_url or not re.fullmatch(r"[0-9a-f]{40}", v8.get("rev", "")):
        raise ValueError("Expected the upstream Rusty V8 fork at a pinned commit")
    revision = v8["rev"]
    lockfile = workspace / "Cargo.lock"
    source_url = f"git+{fork_url}?rev={revision}#{revision}"
    version, = [
        package["version"] for package in read_toml(lockfile)["package"]
        if package["name"] == "v8" and package.get("source") == source_url
    ]
    if not re.fullmatch(VERSION, version):
        raise ValueError(f"Expected a stable Rusty V8 version, got {version}")

    # The fork can change Rust code, but the distributed iOS library must
    # match its native build inputs and C++ bindings.
    def abi(repo, ref):
        tree = github(f"repos/{repo}/git/trees/{ref}?recursive=1")["tree"]
        return {entry["path"]: entry["sha"] for entry in tree if entry["path"] in ABI_FILES}

    fork_abi = abi(FORK, revision)
    if set(fork_abi) != set(ABI_FILES) or fork_abi != abi(V8_REPO, f"v{version}"):
        raise ValueError(f"Rusty V8 {version} does not match the fork's native build inputs")

    release = github(f"repos/{V8_REPO}/releases/tags/v{version}")
    assets = {asset["name"]: asset.get("digest") or "" for asset in release["assets"]}
    names = (f"librusty_v8_release_{V8_TARGET}.a.gz", f"src_binding_release_{V8_TARGET}.rs")
    for name in names:
        digest = assets.get(name, "")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise ValueError(f"Missing published SHA256 for Rusty V8 asset {name}")
        if download(f"https://github.com/{V8_REPO}/releases/download/v{version}/{name}", work / name) != digest[7:]:
            raise ValueError(f"Rusty V8 asset checksum mismatch for {name}")

    fork_digest = unpack_source(FORK, revision, work / "v8-source.tar.gz", source / "vendor/rusty_v8")
    # Keep Cargo's existing versions and checksums when changing the V8 source to a local path.
    manifest_path = workspace / "Cargo.toml"
    original_patch = f'v8 = {{ git = "{fork_url}", rev = "{revision}" }}'
    original_lock = f'source = "{source_url}"\n'
    for path, before, after in (
        (manifest_path, original_patch, 'v8 = { path = "../vendor/rusty_v8" }'),
        (lockfile, original_lock, ""),
    ):
        text = path.read_text()
        if text.count(before) != 1:
            raise ValueError(f"Expected one Rusty V8 source entry in {path.name}")
        path.write_text(text.replace(before, after))

    archive, binding = names
    return {
        "RUSTY_V8_ARCHIVE": str(work / archive),
        "RUSTY_V8_ARCHIVE_SHA256": assets[archive][7:],
        "RUSTY_V8_SRC_BINDING_PATH": str(work / binding),
    }, f"Rusty V8 version: {version}\nRusty V8 commit: {revision}\nRusty V8 source SHA256: {fork_digest}\n"


def build(tag, output):
    match = re.fullmatch(f"rust-v({VERSION})", tag)
    if not match:
        raise ValueError("Use an upstream stable tag such as rust-v0.170.0")
    version = match[1]
    release = github(f"repos/openai/codex/releases/tags/{tag}")
    if release["draft"] or release["prerelease"] or release["tag_name"] != tag:
        raise ValueError(f"{tag} is not a published stable upstream release")
    commit = github(f"repos/openai/codex/commits/{tag}")["sha"]
    revision = package_revision(version)
    package_version = f"{version}-{revision}+rootless"
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="codex-ios-") as tmp:
        work = Path(tmp)
        source = work / "codex"
        workspace = source / "codex-rs"
        digest = unpack_source("openai/codex", commit, work / "source.tar.gz", source)
        if read_toml(workspace / "Cargo.toml")["workspace"]["package"]["version"] != version:
            raise ValueError(f"The source version does not match {tag}")
        toolchain = read_toml(workspace / "rust-toolchain.toml")["toolchain"]["channel"]
        v8_env, v8_provenance = prepare_v8(source, work, workspace)
        update_workspace_lockfile(workspace / "Cargo.lock", version)
        patches = ROOT / "patches/rootless"
        subprocess.run([
            "git", "-C", source, "apply", patches / "codex-ios.patch",
            patches / "ios-file-watcher.patch",
            patches / "codex-code-mode-host-0.168.0-ios.patch",
        ], check=True)

        env = os.environ.copy()
        env.pop("GH_TOKEN", None)
        env.update(v8_env, CARGO_TARGET_DIR=str(work / "target"))
        provenance = work / "UPSTREAM.txt"
        provenance.write_text(
            f"Codex version: {version}\nUpstream tag: {tag}\nUpstream commit: {commit}\n"
            f"Source archive SHA256: {digest}\nRust toolchain: {toolchain}\n"
            f"Target: {V8_TARGET}\nDeployment target: iOS 15.0\n"
            f"{v8_provenance}Rusty V8 archive SHA256: {env['RUSTY_V8_ARCHIVE_SHA256']}\n"
            f"Rusty V8 binding SHA256: {sha256(Path(env['RUSTY_V8_SRC_BINDING_PATH']))}\n"
        )
        for package, binary in (("codex-cli", "codex"), ("codex-code-mode-host", "codex-code-mode-host")):
            subprocess.run([
                "bash", ROOT / "scripts/build-ios-cargo.sh", source, toolchain, package, binary, "--locked",
            ], env=env, check=True)

        binaries = Path(env["CARGO_TARGET_DIR"]) / V8_TARGET / "release"
        subprocess.run([
            "bash", ROOT / "scripts/build-rootless-deb.sh", binaries / "codex",
            binaries / "codex-code-mode-host", package_version, provenance,
        ], env={**env, "CODEX_PACKAGE_OUTPUT_DIR": str(output)}, check=True)
        package = output / package_name(version, revision)
        output.joinpath(package.name + ".sha256").write_text(f"{sha256(package)}  {package.name}\n")
        output.joinpath(provenance.name).write_text(provenance.read_text())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: build-rootless-release.py rust-vX.Y.Z output-directory")
    try:
        build(sys.argv[1], Path(sys.argv[2]).resolve())
    except (KeyError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"Rootless build failed: {error}")
