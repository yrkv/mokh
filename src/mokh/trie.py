import copy
from collections.abc import Hashable, Iterable
from typing import Any


class _NO_VALUE:
    """Sentinel for a `TrieNode` having no value set for some keys."""


class TrieNode:
    def __init__(
        self,
        value: Any | _NO_VALUE = _NO_VALUE,
        *,
        children: dict[Hashable, 'TrieNode'] | None = None,
    ):
        self.value = value
        if children is None:
            children = {}
        self.children = children

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

    def __setitem__(self, keys: Iterable[Hashable], value: Any | _NO_VALUE, /):
        current = self
        for key in keys:
            if key not in current.children:
                current.children[key] = TrieNode()
            current = current.children[key]
        current.value = value

    def merge(self, other: 'TrieNode') -> 'TrieNode':
        value = copy.copy(self.value)
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
