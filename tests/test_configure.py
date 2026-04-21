from mokh.configuration import GLOBAL_CONFIG, Value, configure


def test_basic():
    source1 = {
        'alpha': 1,
        'foo': 10,
        'bar': {
            'a': 20,
            'b': 30,
        },
    }

    source2 = {
        'beta': 2,
        'foo': 20,
        'bar': {
            'b': 40,
            'c': 50,
        },
    }

    c1 = configure(source1)
    c2 = configure(source2)

    assert GLOBAL_CONFIG._map == {}

    with c1:
        assert GLOBAL_CONFIG._map['']['alpha'] == Value(1)
        assert GLOBAL_CONFIG._map['']['foo'] == Value(10)
        assert GLOBAL_CONFIG._map['']['bar'] == Value({'a': 20, 'b': 30})
        assert GLOBAL_CONFIG._map['bar']['a'] == Value(20)
        assert GLOBAL_CONFIG._map['bar']['b'] == Value(30)

    with c2:
        assert GLOBAL_CONFIG._map['']['beta'] == Value(2)
        assert GLOBAL_CONFIG._map['']['foo'] == Value(20)
        assert GLOBAL_CONFIG._map['']['bar'] == Value({'b': 40, 'c': 50})
        assert GLOBAL_CONFIG._map['bar']['b'] == Value(40)
        assert GLOBAL_CONFIG._map['bar']['c'] == Value(50)

    with c1:
        with c2:
            assert GLOBAL_CONFIG._map['']['alpha'] == Value(1)
            assert GLOBAL_CONFIG._map['']['beta'] == Value(2)
            assert GLOBAL_CONFIG._map['']['foo'] == Value(20)
            assert GLOBAL_CONFIG._map['']['bar'] == Value({'b': 40, 'c': 50})
            assert GLOBAL_CONFIG._map['bar']['a'] == Value(20)
            assert GLOBAL_CONFIG._map['bar']['b'] == Value(40)
            assert GLOBAL_CONFIG._map['bar']['c'] == Value(50)

    with c2, c1:
        assert GLOBAL_CONFIG._map['']['alpha'] == Value(1)
        assert GLOBAL_CONFIG._map['']['beta'] == Value(2)
        assert GLOBAL_CONFIG._map['']['foo'] == Value(10)
        assert GLOBAL_CONFIG._map['']['bar'] == Value({'a': 20, 'b': 30})
        assert GLOBAL_CONFIG._map['bar']['a'] == Value(20)
        assert GLOBAL_CONFIG._map['bar']['b'] == Value(30)
        assert GLOBAL_CONFIG._map['bar']['c'] == Value(50)

    assert GLOBAL_CONFIG._map == {}
