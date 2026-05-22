import functools
import inspect
from types import FunctionType
from typing import Any, Callable

from .config import CURRENT_CONFIG, ConfigSlot
from .cursor import CONFIG_CURSOR, ConfigCursor, ConfigCursorSlot, _search_config


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


class ConfigurableContextManager:
    def __init__(
        self,
        key: str | None = None,
        handlers: dict[str, Callable[[Any], Any]] = {},
        cursor: ConfigCursorSlot = CONFIG_CURSOR,
        current_config: ConfigSlot = CURRENT_CONFIG,
    ):
        self.key = key
        self.handlers = handlers
        self.cursor = cursor
        self.current_config = current_config
        self.history: list[ConfigCursor] = []
        self.is_decorator = False

    def __enter__(self):
        """@public"""
        assert self.key is not None, 'key required'

        self.cursor.check(self.current_config)
        next_cursor = self.cursor.slot.descend(self.key)

        self.history.append(self.cursor.slot)
        self.cursor.slot = next_cursor

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """@public"""
        self.cursor.slot = self.history.pop()

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
            self.is_decorator = True

            with self:
                config_kwargs = {}
                for param in sig.parameters.values():
                    if param.kind is not inspect.Parameter.KEYWORD_ONLY:
                        continue
                    if param.name in kwargs:
                        continue

                    value = _search_config(param.name)
                    if value is None:
                        continue
                    data = value.data

                    if param.name in self.handlers:
                        data = self.handlers[param.name](data)
                    config_kwargs[param.name] = data

                new_kwargs = config_kwargs | kwargs
                out = fn(*args, **new_kwargs)

            self.is_decorator = False
            return out

        return wrapper


def _generate_key(
    fn: FunctionType,
) -> str:
    # If it's an __init__ of a class, use the class name instead
    if fn.__name__ == '__init__':
        return fn.__qualname__.split('.')[-2]
    return fn.__name__
