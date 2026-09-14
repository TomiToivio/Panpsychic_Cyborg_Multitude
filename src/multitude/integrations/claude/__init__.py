"""Thin Claude Code participant integration for PCM.

Claude Code is an external technological participant. It uses the same
Multitude service and permission boundary as Hermes and is never a core
runtime dependency.
"""
from .adapter import ClaudeCodeAdapter, ClaudePermissions
from .tools import ClaudeTools

__all__ = ["ClaudeCodeAdapter", "ClaudePermissions", "ClaudeTools"]
