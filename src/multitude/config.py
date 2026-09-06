# -*- coding: utf-8 -*-
"""Runtime configuration for the rhizome kernel.

Every default can be overridden with an environment variable, so a rhizome
can run anywhere without code changes. Nothing here is secret.
"""
import os

# --- Ollama (the voice box of technological nodes) ---
OLLAMA_HOST = os.environ.get("PCM_OLLAMA_HOST", "http://localhost:11434")

# Prefer Ollama local models by default. Small local Gemma 4 models are
# enough for most Concordia-style work; larger local models are used on
# machines with more GPU. The cloud Gemma 4 model is a fallback when a
# larger-capability model is needed but local GPU is insufficient.
DEFAULT_MODEL = os.environ.get("PCM_OLLAMA_MODEL", "gemma4:e4b")

# Long timeout: cloud-backed models served through local Ollama can be slow.
REQUEST_TIMEOUT = float(os.environ.get("PCM_OLLAMA_TIMEOUT", "180"))

# --- Storage (local-first by default; the rhizome's memory belongs to the rhizome) ---
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_ROOT = os.environ.get("PCM_DATA_DIR", os.path.join(_REPO_ROOT, "data"))


def rhizomes_root(data_root: str | None = None) -> str:
    """Directory under which rhizome directories live."""
    return os.path.join(data_root or DATA_ROOT, "tribes")


def find_rhizome_dir(explicit: str | None = None, data_root: str | None = None) -> str:
    """Resolve the rhizome directory to operate on.

    Explicit --tribe DIR wins; otherwise the most recently used rhizome
    under the data root is selected.
    """
    if explicit:
        if not os.path.isfile(os.path.join(explicit, "tribe.json")):
            raise FileNotFoundError(f"not a rhizome directory: {explicit}")
        return explicit
    root = rhizomes_root(data_root)
    if not os.path.isdir(root):
        raise FileNotFoundError(
            f"no rhizomes found under {root} - run 'multitude found' first "
            f"or pass --tribe DIR"
        )
    candidates = [
        os.path.join(root, name)
        for name in os.listdir(root)
        if os.path.isfile(os.path.join(root, name, "tribe.json"))
    ]
    if not candidates:
        raise FileNotFoundError(f"no rhizomes found under {root}")
    return max(candidates, key=os.path.getmtime)