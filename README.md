# Mokh

Simple configuration library that tries to stay out of your way.

What Mokh defines as "configuration" is a collection of adjustable settings.
The primary goals are to be convenient and make it so you don't have to think
about configuration when implementing other code.


### Quickstart

Applying the `@mokh.configurable()` decorator to any function causes it to
search the current configuration to pull in values for any **keyword-only**
parameters.
```python
import mokh

@mokh.configurable()
def setup_model(
    # `*` marks the beginning of (configurable) keyword-only params
    *, ch_in, ch_h, ch_out
):
    ... # imagine there's a machine learning model being initialized here
    return model

@mokh.configurable()
def train(model,
    # default values make it optional in the configuration
    *, lr=0.01, batch_size=64
):
    ... # imagine there's some fancy machine learning code here
```

The current configuration can be modified via a context manager
`mokh.configure()`.
```python
with mokh.configure(ch_in=16, ch_h=64, ch_out=16, lr=0.02):
    # notice we don't need to pass configured args
    model = setup_model()
    # but we still can, in order to override them
    train(model, batch_size=8)
```

For convenience, `mokh.configure_from_args()` provides a simple CLI wrapper
that makes it easy to use files as configuration sources or set values directly
from the command line.

`main.py`:
```python
with mokh.configure_cli():
    model = setup_model()
    train(model)
```

`config.yaml`:
```yaml
ch_in: 16
ch_h: 64
# By default, functions search their name as a prefix. More detailed control
# can be achieved via args passed to `@mokh.configurable()`.
setup_model.ch_out: 16
train: 
    lr: 0.02
```

Then, we can (for example) run the following to load that configuration while
also overriding `ch_h` to be 128 in `setup_model`:
```sh
python main.py -c config.yaml -c setup_model.ch_h=128
```








