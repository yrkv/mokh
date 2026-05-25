import functools
from typing import Any, Callable, NamedTuple, TypeAlias

from .common import is_dict_str_Any
from .trie import TrieNode

# This way we can contain `None` without error...
Value = NamedTuple('Value', [('data', Any)])
"""
Store a `Value` wrapper type in the `Config` values in order to distinguish
between "there is no value" vs "the value is `None`".
"""

Config: TypeAlias = TrieNode[str, Value]
"""Each `Config` is a mapping from string paths to `Value`s. Each path can be
thought of as a sequence of dot-delimited string keys.

We use a [trie](https://en.wikipedia.org/wiki/Trie) to represent the config so
we can retrieve subsets based on a prefix.
"""


def build_config(
    source: dict[str, Any],
    keys: tuple[str, ...] = (),
    root: Config | None = None,
) -> Config:
    """Create a `Config` trie from a (potentially nested) dict source.

    This does NOT deep copy from the source dict, so the source should be
    considered "used up" afterwards.
    """
    if root is None:
        root = TrieNode()

    for key, val in source.items():
        # it's not really clear how we might handle keys with dots at start/end...
        assert not key.startswith('.') and not key.endswith('.')

        current_keys = (*keys, *key.split('.'))

        old_node = root.get(current_keys)
        if old_node is not None and old_node.value is not None:
            assert False, 'invalid overlap'

        root[current_keys] = Value(val)

        if is_dict_str_Any(val):
            build_config(val, current_keys, root)

    return root


def _merge_two(
    a: Config,
    b: Config,
) -> Config:
    out: Config = TrieNode()
    out.value = b.value if b.value is not None else a.value

    child_keys = {*a.children.keys(), *b.children.keys()}
    for key in child_keys:
        if key in a.children and key in b.children:
            out.children[key] = merge_configs(a.children[key], b.children[key])
        elif key in a.children:
            out.children[key] = a.children[key]
        elif key in b.children:
            out.children[key] = b.children[key]

    return out


def merge_configs(
    *configs: Config,
) -> Config:
    """Create a new `Config` by combining all the input configs, with later
    values overriding earlier ones."""
    assert len(configs) > 0

    out = configs[0]
    for config in configs[1:]:
        out = _merge_two(out, config)

    return out


class ConfigSlot:
    def __init__(self, config: Config):
        self.slot = config


CURRENT_CONFIG: ConfigSlot = ConfigSlot(TrieNode())


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
