import pytest

from mokh.trie import _NO_VALUE, ImmutableError, TrieNode


def test_empty_value():
    trie = TrieNode()

    assert trie.value is _NO_VALUE
    assert trie[()] is _NO_VALUE
    assert trie[('missing',)] is _NO_VALUE


def test_empty_repr():
    assert repr(TrieNode()) == 'TrieNode()'


def test_empty_get_node():
    trie = TrieNode()

    assert trie.get_node(('a',)) is None
    # this avoids requiring that it actually returns the same empty node
    assert repr(trie.get_node(())) == 'TrieNode()'


def test_simple():
    trie = TrieNode.from_pairs([(('a', 'b', 'c'), 123)])

    assert trie[('a', 'b', 'c')] == 123

    node = trie.get_node(('a', 'b'))

    assert node is not None
    assert node.value is _NO_VALUE
    assert trie[('a', 'b')] is _NO_VALUE


def test_lookup_of_missing_path():
    trie = TrieNode.from_pairs([(('a', 'b'), 1)])

    assert trie.get_node(('a',)) is not None
    assert trie.get_node(('a', 'c')) is None
    assert trie[('a', 'c')] is _NO_VALUE


def test_multiple_independent_values():
    trie = TrieNode.from_pairs(
        [
            (('a',), 1),
            (('b',), 2),
            (('c',), 3),
        ]
    )

    assert trie[('a',)] == 1
    assert trie[('b',)] == 2
    assert trie[('c',)] == 3


def test_value_and_descendant_value_can_both_exist():
    trie = TrieNode.from_pairs(
        [
            (('a',), 1),
            (('a', 'b'), 2),
        ]
    )

    assert trie[('a',)] == 1
    assert trie[('a', 'b')] == 2


def test_duplicate_key_sequence_raises():
    with pytest.raises(ImmutableError):
        TrieNode.from_pairs(
            [
                (('a', 'b'), 1),
                (('a', 'b'), 2),
            ]
        )


def test_attributes_cannot_be_assigned():
    trie = TrieNode()

    with pytest.raises(ImmutableError):
        trie.value = 123

    with pytest.raises(ImmutableError):
        trie._children = {}


def test_merge_disjoint():
    a1 = TrieNode.from_pairs([(('a',), 1)])
    b2 = TrieNode.from_pairs([(('b',), 2)])

    a1_b2 = a1.merge(b2)

    assert a1_b2[('a',)] == 1
    assert a1_b2[('b',)] == 2


def test_merge_value():
    a1 = TrieNode.from_pairs([(('a',), 1)])
    a2 = TrieNode.from_pairs([(('a',), 2)])

    a1_a2 = a1.merge(a2)
    a2_a1 = a2.merge(a1)

    assert a1[('a',)] == 1
    assert a2[('a',)] == 2
    assert a1_a2[('a',)] == 2
    assert a2_a1[('a',)] == 1


def test_merge_recurses_into_children():
    ax1 = TrieNode.from_pairs([(('a', 'x'), 1)])
    ay2 = TrieNode.from_pairs([(('a', 'y'), 2)])

    ax1_ay2 = ax1.merge(ay2)

    assert ax1_ay2[('a', 'x')] == 1
    assert ax1_ay2[('a', 'y')] == 2


def test_root_value():
    trie = TrieNode.from_pairs([((), 'root')])

    assert trie[()] == 'root'
    # empty key sequence is equivalent to setting value
    assert trie.value == 'root'


def test_non_string_keys():
    obj = object()

    trie = TrieNode.from_pairs([((1, 2.5, obj), 'value')])

    assert trie[(1, 2.5, obj)] == 'value'


def test_iterator_keys_supported():
    trie = TrieNode.from_pairs([(iter([1, 2, 3]), 'value')])

    assert trie[(1, 2, 3)] == 'value'


def test_can_store_none():
    trie = TrieNode.from_pairs([(('a',), None)])

    assert trie[('a',)] is None


def test_can_store_no_value_sentinel():
    trie = TrieNode.from_pairs([(('a',), _NO_VALUE)])

    assert trie[('a',)] is _NO_VALUE
    # from the perspective of values, storing _NO_VALUE is the same as not
    # storing any value at all. However, it will still create sub-nodes.
    assert trie[('b',)] is _NO_VALUE


def test_simple_get_node():
    trie = TrieNode.from_pairs([(('a', 'b', 'c'), 123)])

    ab = trie.get_node(('a', 'b'))
    abc = trie.get_node(('a', 'b', 'c'))

    assert ab is not None
    assert ab.value is _NO_VALUE

    assert abc is not None
    assert abc.value == 123


def test_repr_with_value_only():
    assert repr(TrieNode(value=123)) == 'TrieNode(value=123)'


def test_str_contains_keys_and_values():
    trie = TrieNode.from_pairs(
        [
            (('a',), 1),
            (('b',), 2),
        ]
    )

    out = str(trie)

    assert "'a'" in out
    assert "'b'" in out
    assert 'value=1' in out
    assert 'value=2' in out
