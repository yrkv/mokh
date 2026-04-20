from mokh.configuration import (
    Value,
    ValueConflict,
    ValueMissing,
    build_configuration,
)


def test_empty():
    assert build_configuration({}) == {}


def test_simple():
    # testing with no conflicts
    c = build_configuration(
        {
            'a': 10,
            'foo.a': 20,
            'foo.bar': {'x': 30, 'y': 40},
        }
    )

    assert c['']['a'] == Value(10)
    assert c['foo']['a'] == Value(20)
    assert c['foo']['bar'] == Value({'x': 30, 'y': 40})
    assert c['foo.bar']['x'] == Value(30)
    assert c['foo.bar']['y'] == Value(40)


def test_merge_small():
    c = build_configuration(
        {
            'train': {
                'lr': 0.01,
                'batch_size': 32,
            },
            'train.nonlinearity': 'ReLU',
        }
    )

    assert c['train']['lr'] == Value(0.01)
    assert c['train']['batch_size'] == Value(32)
    assert c['train']['nonlinearity'] == Value('ReLU')


def test_conflicts():
    source = {
        'ch_h': 32,
        'train.ch_h': 64,
        'train': {'lr': 0.01, 'nonlinearity': 'LeakyReLU'},
        'train.nonlinearity': 'ReLU',
    }
    c = build_configuration(source)

    assert c['']['ch_h'] == Value(32)
    assert c['']['train'] == Value(source['train'])
    assert c['train']['ch_h'] == Value(64)
    assert c['train']['lr'] == Value(0.01)
    assert isinstance(c['train']['nonlinearity'], ValueConflict)


def test_other_0():
    source = {
        'lr': 0.03,
        'train': {
            'foo.bar': 3,
            'params': {'foo.bar': 'baz'},
            'optim': {
                'SGD': {
                    'lr': 0.1,
                    'momentum': 0.9,
                    'nesterov': True,
                }
            },
        },
        'train.alpha': {'a': 10},
        'train.device': 'cuda',
    }
    c = build_configuration(source)

    assert c['']['lr'] == Value(source['lr'])
    assert c['']['train'] == Value(source['train'])

    assert c['train']['params'] == Value(source['train']['params'])
    assert c['train']['optim'] == Value(source['train']['optim'])
    assert c['train']['alpha'] == Value(source['train.alpha'])
    assert c['train']['device'] == Value(source['train.device'])
    assert isinstance(c['train']['foo'], ValueMissing)

    assert c['train.foo']['bar'] == Value(source['train']['foo.bar'])

    assert isinstance(c['train.params']['foo'], ValueMissing)

    assert c['train.params.foo']['bar'] == Value(
        source['train']['params']['foo.bar']
    )

    assert c['train.optim']['SGD'] == Value(source['train']['optim']['SGD'])
    assert c['train.optim.SGD']['lr'] == Value(source['train']['optim']['SGD']['lr'])
    assert c['train.optim.SGD']['momentum'] == Value(
        source['train']['optim']['SGD']['momentum']
    )
    assert c['train.optim.SGD']['nesterov'] == Value(
        source['train']['optim']['SGD']['nesterov']
    )

    assert c['train.alpha']['a'] == Value(source['train.alpha']['a'])
