import pytest

import mokh


def test_basic():
    @mokh.configurable()
    def add(*, x: int, y: int):
        return x + y

    assert add(x=3, y=4) == 7

    with mokh.configure(x=6, y=7):
        assert add() == 13
    with mokh.configure({'x': 6, 'y': 7}):
        assert add(y=14) == 20


def test_default_prefixes():
    @mokh.configurable()
    def train(*, lr: float):
        return lr

    @mokh.configurable()
    def train_other(*, lr: float):
        return lr

    @mokh.configurable()
    def train_another(*, lr: float):
        return lr

    with mokh.configure(
        {
            'lr': 0.01,
            'train_other.lr': 0.02,
            'train_another': {'lr': 0.03},
        }
    ):
        assert train() == 0.01
        assert train_other() == 0.02
        assert train_another() == 0.03


def test_overlap():
    with pytest.raises(Exception):
        mokh.configure(
            {
                'a.b': 10,
                'a': {'b': 20},
            }
        )


def test_more():
    c = mokh.configure(
        {
            'a': 10,
            'foo.a': 30,
            'bar.a': 20,
        }
    )

    foo = mokh.configurable('foo')
    bar = mokh.configurable('bar')
    asdf = mokh.configurable('asdf')

    with c:
        assert mokh.get('a') == 10
        with asdf:
            mokh.get('a') == 10

        with foo, bar:
            assert mokh.get('a') == 20
        with foo, foo, bar, bar:
            assert mokh.get('a') == 20
        with asdf, foo, bar:
            assert mokh.get('a') == 20
        with foo, asdf, bar:
            assert mokh.get('a') == 20
        with foo, bar, asdf:
            assert mokh.get('a') == 20

        with bar, foo:
            assert mokh.get('a') == 30
        with bar, bar, foo, foo:
            assert mokh.get('a') == 30
        with asdf, bar, foo:
            assert mokh.get('a') == 30
        with bar, asdf, foo:
            assert mokh.get('a') == 30
        with bar, foo, asdf:
            assert mokh.get('a') == 30

    @mokh.configurable()
    def cursed(n, *, x):
        if n > 1:
            return [x, *cursed(n - 1)]
        else:
            return [x]

        with mokh.configure(
            {
                'x': 1,
                'cursed.cursed.cursed.x': 2,
            }
        ):
            assert cursed(5) == [1, 1, 2, 2, 2]
