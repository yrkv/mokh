import functools
import inspect
from types import FunctionType, MappingProxyType

from .common import GLOBAL_CONFIGURABLE_FUNCTIONS, ConfigurableFunction
from .configuration import (
    GLOBAL_CONFIG,
    Configuration,
    ConfigValue,
    FrozenConfigurationDict,
    Value,
    ValueConflict,
    ValueMissing,
)
from .dynamic import Handler


def _extract_config_values(
    prefixes: tuple[str, ...],
    sig: inspect.Signature,
    configuration: Configuration,
) -> dict[str, ConfigValue]:
    config_values: dict[str, ConfigValue] = {}
    for prefix in prefixes:
        if prefix not in configuration._map:
            continue

        for name in configuration._map[prefix]:
            if name not in sig.parameters:
                continue
            param = sig.parameters[name]

            if param.kind is not inspect.Parameter.KEYWORD_ONLY:
                ...  # TODO warn_configured_non_kwonly
                continue

            val = configuration._map[prefix][name]
            match val:
                case Value():
                    config_values[name] = val
                case ValueConflict():
                    if isinstance(
                        config_values[name],
                        (ValueConflict, ValueMissing),
                    ):
                        config_values[name] = val
                case ValueMissing():
                    if isinstance(
                        config_values[name],
                        ValueMissing,
                    ):
                        config_values[name] = val
    return config_values


def configurable(
    *prefixes: str,
    handlers: dict[str, Handler] = {},
    # setattr_config_for_init: bool = False,
    # warn_mismatched_type: bool = True,
    # warn_configured_non_kwonly: bool = True,
    configuration: Configuration = GLOBAL_CONFIG,
    disable_cache: bool = False,
):

    # Cache injected kwargs per configuration. Since `Configuration._map` is
    # frozen/hashable, we can just use that as the key without issues.
    cache: dict[FrozenConfigurationDict, dict[str, ConfigValue]] = {}

    def decorator(fn):
        nonlocal prefixes
        if isinstance(fn, type):
            raise TypeError('@configurable should decorate __init__, not the class')

        if prefixes == ():
            prefixes = _generate_prefixes(fn)

        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            if len(configuration._map) == 0:
                return fn(*args, **kwargs)

            config_values = {}
            if configuration._map in cache:
                config_values = cache[configuration._map]
            else:
                config_values = _extract_config_values(prefixes, sig, configuration)

                if not disable_cache:
                    cache[configuration._map] = config_values

            config_kwargs = {}
            for name, val in config_values.items():
                if name in kwargs:
                    continue
                match val:
                    case Value(inner):
                        if name in handlers:
                            config_kwargs[name] = handlers[name](inner)
                        else:
                            config_kwargs[name] = inner
                    case ValueConflict():
                        ...  # TODO: warn_value_conflict
                    case ValueMissing():
                        ...  # TODO: warn_value_missing

            new_kwargs = config_kwargs | kwargs
            out = fn(*args, **new_kwargs)

            return out

        _cache_configurable_function(fn, prefixes)
        return decorated

    return decorator


def _generate_prefixes(
    fn: FunctionType,
) -> tuple[str, ...]:
    name = fn.__name__
    # If it's an __init__ of a class, use the class name instead
    if name == '__init__':
        name = fn.__qualname__.split('.')[-2]
    return ('', name)


def _cache_configurable_function(fn, prefixes):
    global GLOBAL_CONFIGURABLE_FUNCTIONS

    sig = inspect.signature(fn)
    kwonly_params = MappingProxyType(
        {
            param.name: param
            for param in sig.parameters.values()
            if param.kind is inspect.Parameter.KEYWORD_ONLY
        }
    )
    GLOBAL_CONFIGURABLE_FUNCTIONS[fn] = ConfigurableFunction(prefixes, kwonly_params)
