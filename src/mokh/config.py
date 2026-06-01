import functools
from collections.abc import Generator
from typing import Any, Callable, TypeAlias

from .common import is_dict_str_Any
from .trie import _NO_VALUE, TrieNode

# Config: TypeAlias = TrieNode[str, Value]
Config: TypeAlias = TrieNode
"""Each `Config` is a mapping from string paths to values. Each path can be
thought of as a sequence of dot-delimited string keys.

We use a [trie](https://en.wikipedia.org/wiki/Trie) to represent the config so
we can retrieve subsets based on a prefix.
"""


def flatten_config_source(
    source: dict[str, Any],
) -> Generator[tuple[list[str], Any]]:
    for key, val in source.items():
        # it's not really clear how we might handle keys with dots at start/end
        assert not key.startswith('.') and not key.endswith('.')
        keys = key.split('.')

        yield (keys, val)

        if is_dict_str_Any(val):
            for sub_keys, sub_val in flatten_config_source(val):
                yield (keys + sub_keys, sub_val)


def build_config(
    source: dict[str, Any],
) -> Config:
    """Create a `Config` trie from a (potentially nested) dict source.

    This does NOT deep copy values from the source dict, so the source should
    be considered "used up" afterwards.
    """
    return TrieNode.from_pairs(flatten_config_source(source))


class ConfigSlot:
    def __init__(self, config: Config):
        self.slot = config


CURRENT_CONFIG: ConfigSlot = ConfigSlot(TrieNode())


class _RAISE_ERROR:
    """Sentinel to raise an error instead of a default value."""


def get(
    *keys: str,
    default: Any = _RAISE_ERROR,
    current_config: ConfigSlot = CURRENT_CONFIG,
) -> Any:
    """
    Retrieve the corresponding value for the key if found in
    `mokh.config.CURRENT_CONFIG` via `CONFIG_CURSOR`.

    Default behavior is to raise error if not found. Set `default` to any value
    to make it the default.
    """
    out = current_config.slot[keys]
    if out is not _NO_VALUE:
        return out
    if default is _RAISE_ERROR:
        raise ValueError(f'{repr(keys)} not found in current config search index')
    return default


class ConfigureContextManager:
    """Context manager which applies changes to the current config, as well as
    reverting said changes upon end.

    Since `Config` is immutable after creation from our perspective, this
    changes the `CURRENT_CONFIG` variable, not the actual `Config` objects.

    TODO explain args
    """

    def __init__(
        self,
        f: Callable[[Config], Config],
        *,
        current_config: ConfigSlot = CURRENT_CONFIG,
    ):
        self.f = f
        self.current_config = current_config
        self.history: list[Config] = []

    def __enter__(self):
        self.history.append(self.current_config.slot)
        self.current_config.slot = self.f(self.current_config.slot)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.current_config.slot = self.history.pop()

    def __call__(self, fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with self:
                return fn(*args, **kwargs)

        return wrapper
