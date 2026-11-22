#!/usr/bin/env python3
"""Discover missing stable packages and publish completed release artifacts."""

from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

from rootless_version import package_name, package_revision


SEMVER = r"[0-9]+\.[0-9]+\.[0-9]+"
UPSTREAM = "openai/codex"
UPSTREAM_TAG = re.compile(f"rust-v({SEMVER})")
ROOTLESS_TAG = re.compile(f"v({SEMVER})-([0-9]+)-rootless")
PACKAGE_FILE = re.compile(rf"com\.openai\.codex-ios_({SEMVER})-([0-9]+)\+rootless_iphoneos-arm64\.deb")
BASE_VERSION = (0, 168, 0)
AUTOMATED_DRAFT = "<!-- Automated ios-codex rootless release -->"


def gh_json(*args):
    return json.loads(subprocess.check_output(["gh", *args]))


def semver(version):
    return tuple(map(int, version.split(".")))


def releases(repo):
    pages = gh_json("api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=50")
    return [release for page in pages for release in page]


def published_versions(local_releases):
    versions = {}
    for release in local_releases:
        tag = ROOTLESS_TAG.fullmatch(release["tag_name"])
        if not tag or release["draft"] or release["prerelease"]:
            continue
        name = package_name(tag[1], tag[2])
        assets = {asset["name"] for asset in release["assets"] if asset["state"] == "uploaded"}
        if {name, name + ".sha256"} <= assets:
            version = semver(tag[1])
            versions[version] = max(int(tag[2]), versions.get(version, 0))
    return versions


def discover(repo, requested_tag):
    if requested_tag:
        tag = UPSTREAM_TAG.fullmatch(requested_tag)
        if not tag or semver(tag[1]) <= BASE_VERSION:
            raise ValueError("Enter a stable upstream tag newer than rust-v0.168.0")
        release = gh_json("api", f"repos/{UPSTREAM}/releases/tags/{requested_tag}")
        if release["draft"] or release["prerelease"]:
            raise ValueError(f"{requested_tag} is not a published stable release")
        tags = [requested_tag]
    else:
        upstream = gh_json(
            "release", "list", "--repo", UPSTREAM, "--exclude-drafts", "--exclude-pre-releases",
            "--limit", "100", "--json", "tagName",
        )
        tags = [release["tagName"] for release in upstream]

    published = published_versions(releases(repo))
    missing = []
    for tag in tags:
        match = UPSTREAM_TAG.fullmatch(tag)
        if not match:
            continue
        number = semver(match[1])
        if number > BASE_VERSION and published.get(number, 0) < package_revision(match[1]):
            missing.append({"tag": tag, "version": match[1]})
    missing.sort(key=lambda release: semver(release["version"]))
    print("Pending upstream releases:", ", ".join(release["tag"] for release in missing) or "none")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"pending={json.dumps(missing, separators=(',', ':'))}\n")


def publish_release(repo, artifact, version, existing, latest):
    revision = package_revision(version)
    tag = f"v{version}-{revision}-rootless"
    package = artifact / package_name(version, revision)
    checksum = package.with_name(package.name + ".sha256")
    with package.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if checksum.read_text().strip() != f"{digest}  {package.name}":
        raise ValueError(f"Checksum mismatch for {package.name}")
    fields = subprocess.check_output([
        "dpkg-deb", "--show", "--showformat=${Package}\n${Version}\n${Architecture}\n", package,
    ], text=True).splitlines()
    if fields != ["com.openai.codex-ios", f"{version}-{revision}+rootless", "iphoneos-arm64"]:
        raise ValueError(f"Unexpected package metadata for {package.name}")

    provenance = (artifact / "UPSTREAM.txt").read_text()
    commit = re.search(r"^Upstream commit: ([0-9a-f]{40})$", provenance, re.MULTILINE)
    if not commit or f"Upstream tag: rust-v{version}" not in provenance.splitlines():
        raise ValueError(f"Unexpected upstream provenance in {artifact}")
    notes = (
        "Native arm64 package for rootless jailbroken iOS 15 or later. "
        "Includes the matching native Code Mode host.\n\n"
        f"Upstream commit `{commit[1]}`. "
        f"[Codex {version} release](https://github.com/{UPSTREAM}/releases/tag/rust-v{version})\n\n"
        f"{AUTOMATED_DRAFT}"
    )
    title = f"Codex {version} for Rootless iOS"
    target = os.environ["GITHUB_SHA"]
    latest_flag = f"--latest={'true' if latest else 'false'}"
    refs = gh_json("api", f"repos/{repo}/git/matching-refs/tags/{tag}")
    for ref in refs:
        if ref["ref"] == f"refs/tags/{tag}" and ref["object"]["sha"] != target:
            raise ValueError(f"Tag {tag} already points to another source commit")
    draft = existing.get(tag)
    if draft:
        if not draft["draft"] or AUTOMATED_DRAFT not in (draft["body"] or ""):
            raise ValueError(f"Release {tag} already exists and needs maintainer review")
        subprocess.run(["gh", "release", "upload", tag, package, checksum, "--repo", repo, "--clobber"], check=True)
        subprocess.run([
            "gh", "release", "edit", tag, "--repo", repo, "--draft=false",
            "--target", target, "--title", title, "--notes", notes, latest_flag,
        ], check=True)
    else:
        subprocess.run([
            "gh", "release", "create", tag, package, checksum, "--repo", repo,
            "--target", target, "--title", title, "--notes", notes, latest_flag,
        ], check=True)


def publish(repo, artifacts):
    local_releases = releases(repo)
    published = published_versions(local_releases)
    existing = {release["tag_name"]: release for release in local_releases}
    ready = []
    # download-artifact extracts a single artifact at the destination root.
    for package in artifacts.rglob("*.deb"):
        match = PACKAGE_FILE.fullmatch(package.name)
        if package.is_file() and match and int(match[2]) == package_revision(match[1]):
            ready.append((match[1], package.parent))
    if not ready:
        print("No completed packages to publish", file=sys.stderr)
        return 1

    failed = False
    for version, artifact in sorted(ready, key=lambda item: semver(item[0])):
        number = semver(version)
        if published.get(number, 0) >= package_revision(version):
            print(f"Codex {version} is already published")
            continue
        try:
            publish_release(repo, artifact, version, existing, number >= max(published, default=BASE_VERSION))
            published[number] = package_revision(version)
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            print(f"::error::Could not publish Codex {version}: {error}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    repo = os.environ["GITHUB_REPOSITORY"]
    if sys.argv[1:] == ["discover"]:
        discover(repo, os.environ.get("REQUESTED_TAG", ""))
    elif len(sys.argv) == 3 and sys.argv[1] == "publish":
        sys.exit(publish(repo, Path(sys.argv[2])))
    else:
        sys.exit("Usage: sync-rootless-releases.py discover | publish artifacts-directory")
