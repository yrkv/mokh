import mokh


def test_configurable_basic():
    @mokh.configurable()
    def add(*, x: int, y: int):
        return x + y

    assert add(x=3, y=4) == 7

    with mokh.configure(x=6, y=7):
        assert add() == 13
    with mokh.configure(x=6, y=7):
        assert add(y=14) == 20
