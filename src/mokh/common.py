"""
Types, functions, and structures used throughout `mokh` without sufficient
complexity to warrant their own file and without strong enough association with
a specific submodule.
"""

import inspect
from types import FunctionType, MappingProxyType
from typing import NamedTuple

type ConfigSource = list[ConfigSource] | dict[str, ConfigSource] | object
"""
Represents the source a configuration is defined from, or any subset of it. Any
actual `Configuration` will contain (references to) subsets of the source as
its values.

Arbitrarily nestable structure intended to be a superset of `json`, `yaml`,
`toml`, or other configuration/markup formats after they're loaded into python.
"""


class ConfigurableFunction(NamedTuple):
    prefixes: tuple[str, ...]
    kwonly_params: MappingProxyType[str, inspect.Parameter]


GLOBAL_CONFIGURABLE_FUNCTIONS: dict[FunctionType, ConfigurableFunction] = dict()
"""
Cache of all functions decorated with `@configurable(...)`.
"""
