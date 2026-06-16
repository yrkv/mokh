import functools
import inspect
import warnings
from contextvars import ContextVar
from importlib.util import find_spec
from pathlib import Path
from types import FunctionType
from typing import Any, Callable

from .config import CURRENT_CONFIG, ConfigureContextManager
from .config import get as mokh_get
from .trie import _NO_VALUE, TrieNode

_HAS_BEARTYPE = find_spec('beartype') is not None


def configurable(
    key: str | None = None,
    /,
    *,
    handlers: dict[str, Callable[[Any], Any]] = {},
):
    """
    Context manager and function decorator which defines how the config is
    interpreted and used.

    As a context manager:
    - The key defines an (optional) search prefix in the current config.

    As a function decorator:
    - Applies self as a context manager before the wrapped function is called.
    - The key can be inferred from the name of the function.
        - If decorating an `__init__`, it uses the name of the class instead.
    - Applies default values to keyword-only args from the config.
        - Equivalent to `mokh.get(name, default=default)` for each unset param.
    - See `ConfigurableContextManager.__call__` for more details.
    """
    return ConfigurableContextManager(
        key=key,
        handlers=handlers,
    )


def _descend(config: TrieNode, key: str) -> TrieNode:
    sub_config = config.get_node([key])
    if sub_config is None:
        return config
    return config.merge(sub_config)


class ConfigurableContextManager:
    def __init__(
        self,
        key: str | None = None,
        handlers: dict[str, Callable[[Any], Any]] = {},
        current_config: ContextVar[TrieNode] = CURRENT_CONFIG,
    ):
        self.key = key
        self.handlers = handlers
        self.current_config = current_config

        self.filestem = None

        def configure_fn(config: TrieNode) -> TrieNode:
            if self.key is None:
                raise ValueError('key is required')

            if self.filestem is not None:
                config = _descend(config, self.filestem)
            config = _descend(config, self.key)
            return config

        self.configure_cm = ConfigureContextManager(
            configure_fn, current_config=self.current_config
        )

    def __enter__(self):
        """@public"""
        self.configure_cm.__enter__()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """@public"""
        self.configure_cm.__exit__(exc_type, exc_value, exc_traceback)

    def __call__(self, fn):
        """@public
        Use `self` as a decorator, wrapping a function with `self` as a
        context manager and applying default values to keyword-only args.

        See `configurable` for broad strokes of behavior.

        `@configurable` intentionally applies only to keyword-only parameters,
        as denoted by a `*` separator in the parameters. This both simplifies
        the implementation and requires the user to clearly indicate which
        paramters should be considered part of the configuration.

        `@configurable` amends precedence for keyword-only parameters:
        1. Directly passed in keyword arguments.
        2. (added) Configured values, with "more specific" matches taking
           precedence.
            - See examples and test cases in `tests/configurable.py`.
        3. Default values in the function definition.
        """

        if self.key is None:
            self.key = _generate_key(fn)
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):

            configurable_auto_filestem = mokh_get(
                'mokh',
                'configurable_auto_filestem',
                default=True,
                current_config=self.current_config,
            )

            if configurable_auto_filestem:
                self.filestem = Path(inspect.getfile(fn)).stem
            else:
                self.filestem = None

            with self:
                warn_configured_non_kwonly = mokh_get(
                    'mokh',
                    'warn_configured_non_kwonly',
                    default=True,
                    current_config=self.current_config,
                )
                warn_mismatched_type = mokh_get(
                    'mokh',
                    'warn_mismatched_type',
                    default=_HAS_BEARTYPE,
                    current_config=self.current_config,
                )

                config_kwargs = {}
                for param in sig.parameters.values():
                    if param.kind is not inspect.Parameter.KEYWORD_ONLY:
                        if (
                            warn_configured_non_kwonly
                            and self.current_config.get()[[param.name]]
                            is not _NO_VALUE
                        ):
                            warnings.warn(
                                f'Configured value found for non keyword-only param `{param.name}`.'
                            )
                        continue
                    if param.name in kwargs:
                        continue

                    value = self.current_config.get()[[param.name]]
                    if value is _NO_VALUE:
                        continue

                    if param.name in self.handlers:
                        value = self.handlers[param.name](value)

                    if (
                        warn_mismatched_type
                        and param.annotation is not inspect.Parameter.empty
                    ):
                        import beartype.door  # type: ignore[import-not-found]

                        if not beartype.door.is_bearable(value, param.annotation):
                            warnings.warn(
                                f'Parameter `{param}` received non-matching value of type `{type(value)}`.',
                                stacklevel=2,
                            )

                    config_kwargs[param.name] = value

                new_kwargs = config_kwargs | kwargs
                out = fn(*args, **new_kwargs)

            return out

        return wrapper


def _generate_key(
    fn: FunctionType,
) -> str:
    # If it's an __init__ of a class, use the class name instead
    if fn.__name__ == '__init__':
        return fn.__qualname__.split('.')[-2]
    return fn.__name__
