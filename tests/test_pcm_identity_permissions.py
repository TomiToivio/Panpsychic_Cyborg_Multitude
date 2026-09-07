"""POSIX filesystem protections for the PCM node signing key."""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import multitude.pcm.identity as identity_module
from multitude.pcm.identity import generate_identity, load_identity


POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix",
    reason="POSIX mode-bit semantics are not available on this platform",
)


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


@POSIX_ONLY
def test_generate_identity_restricts_directory_and_key_file(tmp_path: Path) -> None:
    node_dir = tmp_path / "node"
    old_umask = os.umask(0)
    try:
        generate_identity(node_dir)
    finally:
        os.umask(old_umask)

    assert _mode(node_dir / "identity") == 0o700
    assert _mode(node_dir / "identity" / "pcm_identity.json") == 0o600


@POSIX_ONLY
def test_atomic_replacement_uses_owner_only_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    node_dir = tmp_path / "node"
    first = generate_identity(node_dir)
    identity_path = node_dir / "identity" / "pcm_identity.json"
    os.chmod(identity_path, 0o666)

    source_modes: list[int] = []
    real_replace = os.replace

    def checked_replace(source: os.PathLike, target: os.PathLike) -> None:
        source_modes.append(_mode(Path(source)))
        assert Path(source) != identity_path
        assert Path(target) == identity_path
        real_replace(source, target)

    monkeypatch.setattr(identity_module.os, "replace", checked_replace)
    old_umask = os.umask(0)
    try:
        second = generate_identity(node_dir, force=True)
    finally:
        os.umask(old_umask)

    assert second["did"] != first["did"]
    assert source_modes == [0o600]
    assert _mode(identity_path) == 0o600
    assert not list(identity_path.parent.glob(".pcm_identity.json.*.tmp"))


@POSIX_ONLY
def test_load_identity_warns_or_fails_for_broad_permissions(
    tmp_path: Path,
) -> None:
    node_dir = tmp_path / "node"
    expected = generate_identity(node_dir)
    identity_path = node_dir / "identity" / "pcm_identity.json"
    os.chmod(identity_path, 0o644)

    with pytest.warns(RuntimeWarning, match="expected 0600"):
        assert load_identity(node_dir) == expected

    with pytest.raises(PermissionError, match="expected 0600"):
        load_identity(node_dir, strict_permissions=True)
