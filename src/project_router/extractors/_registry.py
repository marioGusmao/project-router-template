"""Extension-to-extractor mapping registry."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ._base import ExtractionResult

ExtractorFunc = Callable[[Path], ExtractionResult]

_REGISTRY: dict[str, ExtractorFunc] = {}


def register(extensions: list[str]) -> Callable[[ExtractorFunc], ExtractorFunc]:
    """Decorator to register an extractor function for a set of file extensions."""
    def decorator(func: ExtractorFunc) -> ExtractorFunc:
        for ext in extensions:
            _REGISTRY[ext.lower()] = func
        return func
    return decorator


def get_extractor(path: Path) -> ExtractorFunc | None:
    """Look up the extractor for a file path by its extension."""
    return _REGISTRY.get(path.suffix.lower())


def supported_extensions() -> frozenset[str]:
    """Return the set of all registered file extensions."""
    return frozenset(_REGISTRY)
