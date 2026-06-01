import copy
from collections.abc import Hashable, Iterable
from typing import Any


class _NO_VALUE:
    """Sentinel for a `TrieNode` having no value set for some keys."""


class TrieNode:
    """
    Simple immutable [trie](https://en.wikipedia.org/wiki/Trie).
    """

    value: Any | _NO_VALUE
    children: dict[Hashable, 'TrieNode']

    def __init__(
        self,
        *,
        value: Any | _NO_VALUE = _NO_VALUE,
        children: dict[Hashable, 'TrieNode'] | None = None,
    ):
        if children is None:
            children = {}
        object.__setattr__(self, 'value', value)
        object.__setattr__(self, 'children', children)

    # Note: we bypass this with `object.__setattr__` during initialization
    def __setattr__(self, name: str, value: Any):
        raise ImmutableError('Attributes cannot be modified')

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[Iterable[Hashable], Any]]):
        """
        Construct a trie from an iterable to pairs containing a prefix of keys
        and the corresponding value to assign there.

        It is an error for two sequences of values to map to the same value.
        """
        root = cls()
        for keys, value in pairs:
            root._set_value(keys, value)
        return root

    def _set_value(self, keys: Iterable[Hashable], value: Any | _NO_VALUE, /):
        current = self
        for key in keys:
            if key not in current.children:
                current.children[key] = TrieNode()
            current = current.children[key]

        if current.value is not _NO_VALUE:
            raise ImmutableError(f'Value for {keys!r} is already set')
        object.__setattr__(current, 'value', value)

    def get(self, keys: Iterable[Hashable], /) -> 'TrieNode' | None:
        current = self
        for key in keys:
            if key not in current.children:
                return None
            current = current.children[key]
        return current

    def __getitem__(self, keys: Iterable[Hashable], /) -> Any | _NO_VALUE:
        out_node = self.get(keys)
        if out_node is None:
            return _NO_VALUE
        return out_node.value

    def merge(self, other: 'TrieNode') -> 'TrieNode':
        """
        Create a new trie by combining this trie with another, with values from
        the other trie taking priority over values from self.
        """
        value = self.value
        children = copy.copy(self.children)

        if other.value is not _NO_VALUE:
            value = other.value

        for key in other.children:
            if key in children:
                children[key] = children[key].merge(other.children[key])
            else:
                children[key] = other.children[key]

        return TrieNode(value=value, children=children)

    def __str__(self) -> str:
        return self._str_helper().strip()

    def _str_helper(self, indent='', indent_last='  ', indent_more='| ') -> str:
        out = ''

        count = len(self.children)
        for i, (key, val) in enumerate(self.children.items()):
            indent_str = indent_more if i < count - 1 else indent_last
            out_value = '' if val.value is _NO_VALUE else f' value={val.value}'
            out += f'{indent}{repr(key)}{out_value}\n'

            out += val._str_helper(
                indent=f'{indent}{indent_str}',
                indent_last=indent_last,
                indent_more=indent_more,
            )
        return out

    def __repr__(self) -> str:
        value_str = () if self.value is _NO_VALUE else (f'value={self.value}',)
        children_str = () if self.children == {} else (f'children={self.children}',)
        return f'TrieNode({", ".join([*value_str, *children_str])})'


class ImmutableError(Exception):
    """Attempting to modify an immutable object."""
