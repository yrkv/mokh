from collections.abc import Hashable, Mapping
from typing import NamedTuple

import frozendict as cool
from frozendict import frozendict

type FrozenConfigSource = (
    tuple[FrozenConfigSource, ...] | frozendict[str, FrozenConfigSource] | Hashable
)
"""
Immutable subtype of `ConfigSource`, including all nested objects.
"""

type ConfigSource = (
    list[ConfigSource] | Mapping[str, ConfigSource] | FrozenConfigSource
)
"""
Represents the source a configuration is defined from, or any subset of it. Any
actual `Configuration` will contain (references to) subsets of the source as
its values.

Arbitrarily nestable structure intended to be a superset of `json`, `yaml`,
`toml`, or other configuration/markup formats after they're loaded into python.
"""


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

type FrozenConfigurationDict = frozendict[str, frozendict[str, ConfigValue]]
"""
Immutable `ConfigurationDict`, making it hashable.
"""

type ConfigurationMapping = Mapping[str, Mapping[str, ConfigValue]]


def _freeze_configuration_dict(d: ConfigurationMapping):
    """
    Convert any `ConfigurationMapping` into a `FrozenConfigurationDict`
    """
    return frozendict({prefix: frozendict(params) for prefix, params in d.items()})


type ConfigValue = Value | ValueConflict | ValueMissing


class Configuration:
    # TODO: descriptive information about where/how the configuration was
    # created, for later errors/tracking/help
    _map: FrozenConfigurationDict

    def __init__(self, source: dict[str, ConfigSource]):
        if source == {}:
            self._map = _freeze_configuration_dict({})
            return

        source = cool.deepfreeze(source)
        cdict = _build_configuration_map(source)
        self._map = _freeze_configuration_dict(cdict)


GLOBAL_CONFIG: Configuration = Configuration({})
"""Singleton used by default as the main location to keep currently loaded
configuration.

`GLOBAL_CONFIG` should NOT be altered directly. Instead, use the `configure`
context manager or variants like `configure_from_args`.

See `Configuration` for more details.
"""


class Value(NamedTuple):
    """
    Contains anything, expected/assumed to contain some subset of a
    configuration (`ConfigSource`). Deep copied into corresponding arguments
    when invoking configurable functions.
    """

    inner: ConfigSource


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
    source: dict[str, ConfigSource],
    out: None | ConfigurationDict = None,
    prefix: str = '',
) -> ConfigurationDict:
    r"""Create a `Configuration` from a mapping, which is expected/intended to
    just be the content of a single config file.

    Note that this does NOT deep copy from the source dict. The source should
    be considered "used up" after building a configuration from it.
    """
    if out is None:
        out = {}

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

        if isinstance(val, dict):
            next_prefix = f'{current_prefix}.{last}'.strip('.')
            _build_configuration_map(val, out, prefix=next_prefix)

    return out


def merge_configurations(
    a: ConfigurationMapping,
    b: ConfigurationMapping,
) -> ConfigurationDict:
    r"""Create a new `ConfigurationDict` which is equivalent to `a` with `b`
    overlaid on top, combining prefixes/parameter names and overriding values.
    - Contains all the prefixes and parameter names of both `a` and `b`.
    - Values in `b` override values in `a`.
    - This does not modify `a` or `b`, but it *does* avoid copying to some
      extent. This means many of the objects in the output are shared with `a`
      or `b`.
    """

    out: ConfigurationDict = {}

    all_prefixes = {*a.keys(), *b.keys()}
    for prefix in all_prefixes:
        out[prefix] = {}
        if prefix in a:
            out[prefix].update(a[prefix])
        if prefix in b:
            out[prefix].update(b[prefix])

    return out


class ConfigContextManager:
    """Context manager which applies changes to the current configuration, as
    well as reverting said changes upon end.

    Since `Configuration`s are immutable, this changes the `GLOBAL_CONFIG`
    variable, not the actual objects.
    """

    def __init__(
        self,
        config_dict: ConfigurationMapping,
        target: Configuration = GLOBAL_CONFIG,
    ):
        self.config_dict = config_dict
        self.target = target

    def __enter__(self):
        self.prev = self.target._map
        self.target._map = _freeze_configuration_dict(
            merge_configurations(self.target._map, self.config_dict)
        )

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.target._map = self.prev
