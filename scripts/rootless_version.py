"""Debian revisions for upstream versions rebuilt after their first release."""


def package_revision(version):
    return 2 if version == "0.171.0" else 1


def package_name(version, revision):
    return f"com.openai.codex-ios_{version}-{revision}+rootless_iphoneos-arm64.deb"
