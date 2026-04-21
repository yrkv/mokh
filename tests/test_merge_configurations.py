from mokh.configuration import (
    # build_configuration,
    Configuration,
    Value,
    merge_configurations,
)


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

    c1 = Configuration(source1)
    c2 = Configuration(source2)
    c = merge_configurations(c1._map, c2._map)

    assert c['']['alpha'] == Value(1)
    assert c['']['beta'] == Value(2)
    assert c['']['foo'] == Value(20)
    assert c['']['bar'] == Value(source2['bar'])
    assert c['bar']['a'] == Value(20)
    assert c['bar']['b'] == Value(40)
    assert c['bar']['c'] == Value(50)
