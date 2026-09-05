#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical repository entrypoint for the tribe kernel.

All local agents should invoke the root-level kernel through this file so
they share one launcher and one import path strategy.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_src() -> None:
    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


def main(argv: list[str] | None = None) -> int:
    _bootstrap_src()
    from multitude.cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
