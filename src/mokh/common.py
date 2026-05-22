"""
Types, functions, and structures used throughout `mokh` without sufficient
complexity or specificity to warrant their own file and without strong enough
association with a specific submodule.
"""

from pathlib import Path
from typing import Any, TypeGuard

import __main__


def is_dict_str_Any(x: Any) -> TypeGuard[dict[str, Any]]:
    """
    return `True` for input strictly of type `dict[str, Any]`.
    return `False` for anything else.
    """
    return isinstance(x, dict) and all(isinstance(k, str) for k in x)


def entry_point_name() -> str | None:
    """
    Returns the name of the running entry point, or `None` if unavailable.

    Examples:
    - `python scripts/train.py` -> `"train"`
    - `./generate.py` -> `"generate"`
    - `readelf.py` (if in PATH) -> `"readelf"`
    - Python Interpreter -> `None`
    """
    filepath = getattr(__main__, '__file__', None)
    if filepath is None:
        return None
    return Path(filepath).stem
