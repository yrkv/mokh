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
