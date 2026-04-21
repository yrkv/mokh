from collections.abc import Hashable
from types import MappingProxyType
from typing import Any, NamedTuple

from .common import ConfigSource, is_dict_str_Any


class ConfigData:
    __slots__ = ('_data',)
    _data: tuple['ConfigData', ...] | MappingProxyType[str, 'ConfigData'] | Hashable

    def __init__(self, data: 'ConfigSource | ConfigData'):
        if isinstance(data, ConfigData):
            self._data = data._data
        elif isinstance(data, list):
            self._data = tuple(ConfigData(x) for x in data)
        elif is_dict_str_Any(data):
            self._data = MappingProxyType(
                {k: ConfigData(v) for k, v in data.items()}
            )
        elif isinstance(data, Hashable):
            self._data = data
        else:
            raise ValueError('')

    def __getattr__(self, name: str) -> Any:
        return getattr(self._data, name)

    def __eq__(self, other):
        if self._data == other:
            return True
        if hasattr(other, '_data'):
            return self._data == other._data
        return False

    def __hash__(self):
        # force hashing to work :)
        if isinstance(self._data, MappingProxyType):
            return hash(tuple(sorted(self._data.items())))
        return hash(self._data)


type ConfigurationDict = dict[str, dict[str, ConfigValue]]
"""
`prefix` => `param name` => `value`

- `prefix`
    - Path-like string delimited by '.'
    - Corresponds to `configurable`'s `*prefixes`
- `param name`
    - String, cannot contain '.'
    - Corresponds to keyword-only parameters in configurable functions
- `value`
    - See each variant's docstring for meanings.
    - `ConfigValue` = `Value` | `ValueConflict` | `ValueMissing`

Expected to NOT be modified after creation. Should be considered immutable.
"""

type ConfigurationMappingProxy = MappingProxyType[
    str, MappingProxyType[str, ConfigValue]
]
"""
Immutable view into a `ConfigurationDict`, making it hashable.
"""


def _configuration_mapping_proxy(d: ConfigurationDict):
    """
    Convert a `ConfigurationDict` into a `ConfigurationMappingProxy`
    """
    return MappingProxyType(
        {prefix: MappingProxyType(params) for prefix, params in d.items()}
    )


type ConfigValue = Value | ValueConflict | ValueMissing


class Configuration:
    # _source: ConfigData
    _map: ConfigurationMappingProxy

    def __init__(self, source: dict[str, ConfigSource] | ConfigData):
        if source == {}:
            self._map = _configuration_mapping_proxy({})
            return

        # _source = ConfigData(source)
        self._map = _build_configuration_map(source)


GLOBAL_CONFIG: Configuration = Configuration({})
"""Singleton used by default as the main location to keep currently loaded
configuration.

`GLOBAL_CONFIG` should NOT be altered directly. Instead, use the `configure`
context manager or variants like `configure_from_args`.

See `Configuration` for more details.
"""


class Value(NamedTuple):
    """
    Contains anything, expected/assumed to contain a `ConfigData`. Deep
    copied into corresponding arguments when invoking configurable functions.
    """

    inner: Any


class ValueConflict(NamedTuple):
    """
    This prefix+name pair was reached multiple ways with different values,
    disabling its use until resolved.
    """

    ...  # TODO: record where/how


class ValueMissing(NamedTuple):
    """
    This prefix+name pair does not have a value. For example,
    `source={'a.b.c': 10}` means that `a.b` has no value.
    """

    ...  # TODO: record where/how


def _build_configuration_map(
    source: dict[str, ConfigSource] | ConfigData,
    out: None | ConfigurationDict = None,
    prefix: str = '',
) -> ConfigurationMappingProxy:
    r"""Create a `Configuration` from a mapping, which is expected/intended to
    just be the content of a single config file.

    Note that this does NOT deep copy from the source dict. The source should
    be considered "used up" after building a configuration from it.
    """
    if out is None:
        out = {}

    # source = ConfigData(source)
    # if isinstance(source, ConfigData):
    # source = source._data

    # if not
    # if not isinstance(source, (MappingProxyType, dict)):
    # return {}
    # raise ValueError('_build_configuration_map expects a mapping')

    for key, val in source.items():
        # it's not really clear how we might handle keys with dots at start/end...
        assert not key.startswith('.') and not key.endswith('.')

        *the_rest, last = key.split('.')

        partial_prefix = prefix
        for sub_key in the_rest:
            if partial_prefix not in out:
                out[partial_prefix] = {}

            if sub_key not in out[partial_prefix]:
                out[partial_prefix][sub_key] = ValueMissing()
            else:
                ...  # TODO: warn
            partial_prefix = f'{partial_prefix}.{sub_key}'.strip('.')

        current_prefix = f'{prefix}.{".".join(the_rest)}'.strip('.')
        if current_prefix not in out:
            out[current_prefix] = {}

        if last in out[current_prefix]:
            match out[current_prefix][last]:
                case Value(inner):
                    if inner == val:
                        ...  # TODO: warn -- identical value set in multiple places
                    else:
                        out[current_prefix][last] = ValueConflict()
                case ValueMissing():
                    ...  # TODO: warn
                    out[current_prefix][last] = Value(val)
                case ValueConflict():
                    ...  # TODO: add entry to conflict locations

        else:
            out[current_prefix][last] = Value(val)

        if isinstance(val, dict) or (
            isinstance(val, ConfigData) and isinstance(val._data, MappingProxyType)
        ):
            next_prefix = f'{current_prefix}.{last}'.strip('.')
            _build_configuration_map(val, out, prefix=next_prefix)

    return _configuration_mapping_proxy(out)


def merge_configurations(
    a: ConfigurationMappingProxy,
    b: ConfigurationMappingProxy,
) -> ConfigurationMappingProxy:
    r"""Create a new `Configuration` which is equivalent to `a` with `b`
    overlaid on top, combining prefixes/parameter names and overriding values.
    - Contains all the prefixes and parameter names of both `a` and `b`.
    - Values in `b` override values in `a`.
    - This does not modify `a` or `b`, but it *does* minimize copying. This
      means many of the objects in the output are shared with `a` or `b`.
    """

    out: ConfigurationDict = {}

    all_prefixes = {*a.keys(), *b.keys()}
    for prefix in all_prefixes:
        out[prefix] = {}
        if prefix in a:
            out[prefix].update(a[prefix])
        if prefix in b:
            out[prefix].update(b[prefix])

    return _configuration_mapping_proxy(out)


def configure(
    source: dict[str, ConfigSource] = {},
    **kwargs: ConfigSource,
):
    if len(source) >= 1 and len(kwargs) >= 1:
        raise ValueError("Provide either 'source' or keyword arguments, not both")

    if source == {}:
        source = kwargs

    config = Configuration(source)
    return ConfigContextManager(config)


class ConfigContextManager:
    """Context manager which applies changes to the current configuration, as
    well as reverting said changes upon end.

    Since `Configuration`s are immutable, this changes the `GLOBAL_CONFIG`
    variable, not the actual objects.
    """

    def __init__(self, config: Configuration, target: Configuration = GLOBAL_CONFIG):
        self.config = config
        self.target = target

    def __enter__(self):
        self.prev = self.target._map
        self.target._map = merge_configurations(self.target._map, self.config._map)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.target._map = self.prev
