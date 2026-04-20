from types import FunctionType
from typing import Any, NamedTuple

type Json = list[Json] | dict[str, Json] | str | int | float | bool | None


class ConfigurableFunction(NamedTuple):
    keys: tuple[str, ...]
    kwonly_params: dict[str, Any]


GLOBAL_CONFIGURABLE_FUNCTIONS: dict[FunctionType, ConfigurableFunction] = dict()
"""
Cache of all functions decorated with `@configurable(...)`.
"""
