"""Backward-compatible entry point for bot handlers."""

from handlers import create_dispatcher, setup_router

__all__ = ["create_dispatcher", "setup_router"]
