"""
Types, functions, and structures used throughout `mokh` without sufficient
complexity to warrant their own file and without strong enough association with
a specific submodule.
"""

import inspect
from types import FunctionType, MappingProxyType
from typing import Any, NamedTuple, TypeGuard


def is_dict_str_Any(x: Any) -> TypeGuard[dict[str, Any]]:
    """
    return `True` for input strictly of type `dict[str, Any]`.
    return `False` for anything else.
    """
    return isinstance(x, dict) and all(isinstance(k, str) for k in x)


class ConfigurableFunction(NamedTuple):
    prefixes: tuple[str, ...]
    kwonly_params: MappingProxyType[str, inspect.Parameter]


GLOBAL_CONFIGURABLE_FUNCTIONS: dict[FunctionType, ConfigurableFunction] = dict()
"""
Cache of all functions decorated with `@configurable(...)`.
"""
