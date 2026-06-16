"""Each config is a mapping from string paths to values. Each path can be
thought of as a sequence of dot-delimited string keys.

We use a [trie](https://en.wikipedia.org/wiki/Trie) to represent the config so
we can retrieve subsets based on a prefix.
"""

import functools
from collections.abc import Generator
from contextvars import ContextVar
from typing import Any, Callable

from .common import is_dict_str_Any
from .trie import _NO_VALUE, TrieNode


def flatten_config_source(
    source: dict[str, Any],
) -> Generator[tuple[list[str], Any]]:
    for key, val in source.items():
        # it's not clear how to handle keys with dots at start/end
        assert not key.startswith('.') and not key.endswith('.')
        keys = key.split('.')

        yield (keys, val)

        if is_dict_str_Any(val):
            for sub_keys, sub_val in flatten_config_source(val):
                yield (keys + sub_keys, sub_val)


def build_config(
    source: dict[str, Any],
) -> TrieNode:
    """Create a config trie from a (potentially nested) dict source.

    This does NOT deep copy values from the source dict, so the source should
    be considered "used up" afterwards.
    """
    return TrieNode.from_pairs(flatten_config_source(source))


CURRENT_CONFIG: ContextVar[TrieNode] = ContextVar('mokh_config', default=TrieNode())
"""
Global variable used (by default) as the location where the current config
lives.

All functions which use it should have it as a default value for a parameter,
in order to support multiple simultaneous configs.
"""


class _RAISE_ERROR:
    """Sentinel to raise an error instead of a default value."""


def get(
    *keys: str,
    default: Any = _RAISE_ERROR,
    current_config: ContextVar[TrieNode] = CURRENT_CONFIG,
) -> Any:
    """
    Retrieve the corresponding value for the key if found in the current
    config. This is essentially just a convenient wrapper around the internal
    trie.

    Default behavior is to raise error if not found. Set `default` to any value
    to make it the default.
    """
    out = current_config.get()[keys]
    if out is not _NO_VALUE:
        return out
    if default is _RAISE_ERROR:
        raise ValueError(f'{repr(keys)} not found in current config search index')
    return default


class ConfigureContextManager:
    """Context manager which applies changes to the current config, as well as
    reverting said changes upon end.

    Since config tries are immutable after creation, this modifies
    `CURRENT_CONFIG` (by default), not the actual trie objects.

    Accepts a single function which will be provided the current config trie
    and expected to produce the next config trie to replace the current one.

    It can also be used as a decorator, which is equivalent to applying as a
    context manager at the start every time the function is called.
    """

    def __init__(
        self,
        f: Callable[[TrieNode], TrieNode],
        *,
        current_config: ContextVar[TrieNode] = CURRENT_CONFIG,
    ):
        self.f = f
        self.current_config = current_config
        self.history: list = []

    def __enter__(self):
        c = self.current_config.get()
        token = self.current_config.set(self.f(c))
        self.history.append(token)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.current_config.reset(self.history.pop())

    def __call__(self, fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with self:
                return fn(*args, **kwargs)

        return wrapper
