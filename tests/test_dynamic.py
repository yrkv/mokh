import pytest

import mokh
from mokh.dynamic import _find_rec, _inner_lookup, dispatch, for_each, lookup

context = {
    'foo': {
        'alpha': 10,
        'beta': 20,
        'gamma': 30,
        'delta': 40,
        'epsilon': 50,
    },
    'bar': lambda name: f'hello {name}',
}


def test_find():
    assert _find_rec('foo', context) == context['foo']
    for case in context['foo'].keys():
        assert _find_rec(f'foo.{case}', context) == context['foo'][case]

    assert _find_rec('bar', context) == context['bar']


def test_inner_lookup():
    assert _inner_lookup('foo', context) == context['foo']
    for case in context['foo'].keys():
        assert _inner_lookup(f'foo.{case}', context) == context['foo'][case]
    assert _inner_lookup('bar', context) == context['bar']


def test_inner_lookup_partial():
    assert _inner_lookup({'bar': ['world']}, context)() == 'hello world'
    assert _inner_lookup({'bar': {'name': 'there'}}, context)() == 'hello there'

    with pytest.raises(Exception):
        _inner_lookup({}, context)
    with pytest.raises(Exception):
        _inner_lookup({'bar': ['world'], 'other': 'invalid'}, context)


def test_configurable_lookup():
    @mokh.configurable(handlers={'foo': lookup(context['foo'])})
    def f(*, foo: int):
        return foo

    with mokh.configure(foo='beta'):
        assert f() == 20

    for code in context['foo']:
        with mokh.configure(foo=code):
            assert f() == context['foo'][code]


def test_configurable_for_each_lookup():
    @mokh.configurable(handlers={'foo': for_each(lookup(context['foo']))})
    def f(*, foo: list[int]):
        return foo

    with mokh.configure(foo=['epsilon', 'gamma', 'alpha']):
        assert f() == [50, 30, 10]

    for code in context['foo']:
        with mokh.configure(foo=[code]):
            assert f() == [context['foo'][code]]


def test_configurable_dispatch():
    @mokh.configurable(handlers={'foo': dispatch(context)})
    def f(*, foo: str):
        return foo

    with mokh.configure(foo={'bar': ['a']}):
        assert f() == 'hello a'
    with mokh.configure(foo={'bar': {'name': 'b'}}):
        assert f() == 'hello b'
    with mokh.configure(foo={'bar': {'*args': ['c']}}):
        assert f() == 'hello c'


def test_configurable_for_each_dispatch():
    def fn1():
        return 'fn1'

    def fn2():
        return 'fn2'

    def fn3():
        return 'fn3'

    @mokh.configurable(
        handlers={
            'foo': for_each(dispatch(locals())),
        }
    )
    def f(*, foo: list[str]):
        return ' '.join(foo)

    with mokh.configure(
        foo=[
            'fn1',
            {'fn2': []},
            {'fn3': {'*args': []}},
        ]
    ):
        assert f() == 'fn1 fn2 fn3'
