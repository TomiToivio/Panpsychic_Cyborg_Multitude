# -*- coding: utf-8 -*-
"""Security regression tests for PCM node identity storage."""
from __future__ import annotations

import os
import stat
import sys
import tempfile
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from multitude.pcm.identity import generate_identity, load_identity


pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="POSIX mode-bit semantics are required for these tests",
)


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_generated_identity_uses_owner_only_permissions() -> None:
    root = Path(tempfile.mkdtemp(prefix="pcm-identity-mode-"))
    generate_identity(root)

    identity_dir = root / "identity"
    identity_file = identity_dir / "pcm_identity.json"

    assert _mode(identity_dir) == 0o700
    assert _mode(identity_file) == 0o600


def test_force_rotation_preserves_owner_only_permissions() -> None:
    root = Path(tempfile.mkdtemp(prefix="pcm-identity-force-"))
    first = generate_identity(root)
    identity_file = root / "identity" / "pcm_identity.json"

    # Simulate a hostile or overly permissive pre-existing mode. The forced
    # replacement must still land as a fresh owner-only file.
    identity_file.chmod(0o666)
    second = generate_identity(root, force=True)

    assert second["did"] != first["did"]
    assert _mode(identity_file) == 0o600


def test_load_warns_about_broad_existing_permissions() -> None:
    root = Path(tempfile.mkdtemp(prefix="pcm-identity-warning-"))
    generate_identity(root)
    identity_file = root / "identity" / "pcm_identity.json"
    identity_file.chmod(0o644)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        loaded = load_identity(root)

    assert loaded["did"].startswith("did:key:z")
    assert any(
        issubclass(item.category, RuntimeWarning)
        and "broad permissions" in str(item.message)
        and "0600" in str(item.message)
        for item in caught
    )
