"""Loader for custom interaction handlers.

This module discovers and loads all interaction handlers from the
interactions directory. It automatically imports all Python modules
in the directory, which allows their @interaction decorators to
register themselves with the global registry.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
import sys
from pathlib import Path

logger: logging.Logger = logging.getLogger(__name__)


def load_interactions() -> None:
    """Discover and load all interaction handlers.

    This function scans the interactions package for all Python modules
    and imports them. When modules are imported, any functions decorated
    with @interaction() automatically register themselves in the global
    interaction registry.

    Skipped modules:
    - Packages and directories
    - __pycache__: Python's bytecode cache
    - loader: This module itself
    - register: Legacy manual registration (not needed with decorators)

    """
    # Get the directory of this module
    interactions_dir: Path = Path(__file__).parent

    # Iterate through all modules in the interactions directory
    for _importer, interaction_module_name, is_package in pkgutil.iter_modules([
        str(interactions_dir),
    ]):
        # Skip special modules
        if is_package or interaction_module_name in {
            "__pycache__",
            "loader",
            "register",
        }:
            continue

        # Import the module to trigger the decorator registration
        module_name: str = f"juicebox.interactions.{interaction_module_name}"
        try:
            if module_name not in sys.modules:
                importlib.import_module(module_name)

        except ImportError as e:
            # Log but don't fail if a module can't be imported
            logger.warning(
                "Could not load interaction module %s: %s",
                interaction_module_name,
                e,
            )


__all__: list[str] = ["load_interactions"]
