from collections.abc import Iterable
from typing import Generic, TypeVar

K = TypeVar('K')
V = TypeVar('V')


class TrieNode(Generic[K, V]):
    def __init__(
        self,
        value: V | None = None,
        *,
        children: dict[K, 'TrieNode[K, V]'] | None = None,
    ):
        self.value = value
        if children is None:
            children = {}
        self.children = children

    def get(self, keys: Iterable[K], /) -> 'TrieNode[K, V] | None':
        current = self
        for key in keys:
            if key not in current.children:
                return None
            current = current.children[key]
        return current

    def __getitem__(self, keys: Iterable[K], /) -> V | None:
        out_node = self.get(keys)
        if out_node is None:
            return None
        return out_node.value

    def __setitem__(self, keys: Iterable[K], value: V, /):
        current = self
        for key in keys:
            if key not in current.children:
                current.children[key] = TrieNode()
            current = current.children[key]
        current.value = value

    def __str__(self) -> str:
        return self._str_helper().strip()

    def _str_helper(self, indent='', indent_last='  ', indent_more='| ') -> str:
        out = ''

        count = len(self.children)
        for i, (key, val) in enumerate(self.children.items()):
            indent_str = indent_more if i < count - 1 else indent_last
            out_value = '' if val.value is None else f' value={val.value}'
            out += f'{indent}{repr(key)}{out_value}\n'

            out += val._str_helper(
                indent=f'{indent}{indent_str}',
                indent_last=indent_last,
                indent_more=indent_more,
            )
        return out

    def __repr__(self) -> str:
        return f'TrieNode(value={self.value}, children={self.children})'
