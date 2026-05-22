import functools
from collections.abc import Callable, Mapping, Sequence
from types import ModuleType
from typing import Any, TypeAlias

from .common import is_dict_str_Any
from .handler import Handler

Context: TypeAlias = ModuleType | dict[str, Any]


def lookup(context: Context) -> Handler:
    r"""Create a configuration handler that dynamically finds a value within
    `context` using the corresponding configuration part to as the lookup path.

    Example:
    ```python
    from PIL import Image

    # `lookup(...)` creates a configuration handler
    @mokh.configurable(handlers={'resample':lookup(Image.Resampling)})
    def finalize_image(image, *, resample=None):
        return image.resize((256,256), resample)

    # Later, configured values are processed via the handler first
    with mokh.configure(resample='NEAREST'):
        final_image = finalize_image(image)
    ```
    """

    def handler(value: Any):
        nonlocal context
        assert isinstance(value, (str, dict))
        return _inner_lookup(value, context)

    return handler


def dispatch(context: Context) -> Handler:
    r"""Create a configuration handler to dynamically invoke a constructor (or
    more generally, any function) within `context` using the corresponding
    configuration part to as the lookup path.

    Example:
    ```python
    @mokh.configurable(handlers={'nonlinearity':dispatch(torch.nn)})
    def create_model(*, ch_in=8, ch_hid=16, ch_out=8, nonlinearity):
        return torch.nn.Sequential(
            torch.nn.Linear(ch_int, ch_hid),
            nonlinearity,
            torch.nn.Linear(ch_hid, ch_out),
        )

    # Later, configured values are processed via the handler first
    with mokh.configure(nonlinearity='ReLU'):
        create_model() # same as passing in `nonlinearity=torch.nn.ReLU()`
    with mokh.configure(nonlinearity={'LeakyReLU': [0.2]}):
        create_model() # same as passing in `nonlinearity=torch.nn.LeakyReLU(0.2)`
    with mokh.configure(nonlinearity={'CELU': {'alpha': 0.5}}):
        create_model() # same as passing in `nonlinearity=torch.nn.CELU(alpha=0.5)`
    ```
    """

    def handler(value: Any):
        nonlocal context
        assert isinstance(value, (str, dict))
        fn = _inner_lookup(value, context)
        assert callable(fn)
        # We *could* add `*args, **kwargs` into the call here, but (for now) it
        # feels like an anti-pattern. Equivalent behavior is *probably* better
        # done by using `lookup` and adding args at the deferred call.
        return fn()

    return handler


def _inner_lookup(
    value: str | dict[str, list[Any]] | dict[str, dict[str, Any]],
    context: Context,
) -> Any:
    """
    - value="a.b.c"
        -> `context.a.b.c`, `context[a][b][c]`, or any mix of those.
    - value={"foo.bar": [a, b, c]}
        -> `functools.partial(context.foo.bar, a, b, c)`
    - value={"foo.bar": {"a":10, "b":20}}
        -> `functools.partial(context.foo.bar, a=10, b=20)`
    """

    if isinstance(value, str):
        return _find_rec(value, context)

    assert isinstance(value, dict) and len(value) == 1
    path, partial_data = next(iter(value.items()))

    found = _find_rec(path, context)
    assert callable(found), 'must be callable if partial_data provided'

    assert isinstance(partial_data, (Sequence, Mapping))
    return _apply_partial(found, partial_data)


def _find_rec(
    path: str,
    context: Context,
) -> Any:
    """
    Interpret `path` as a sequence of dot-delimited keys to access attributes
    or index into `context`.
    """

    if '.' in path:
        (name, next_path) = path.split('.', 1)
    else:
        (name, next_path) = path, None

    if hasattr(context, name):
        next_context = getattr(context, name)
    elif is_dict_str_Any(context) and name in context.keys():
        next_context = context[name]
    else:
        raise LookupError(f"Unable to find '{name}'")

    if next_path is None:
        return next_context
    else:
        return _find_rec(next_path, next_context)


def _apply_partial(
    fn: Callable[..., Any],
    partial_data: Sequence[Any] | Mapping[str, Any],
):
    """Flexible version of `functools.partial` which interprets `partial_data`
    as either `*args` or `**kwargs` depending on if it's a `Sequence` or
    `Mapping`. If it's a `Mapping`, it has special handling for the key
    `"*args"`, which is applied as `*args` to the `fn`.
    """
    assert callable(fn)
    assert isinstance(partial_data, (Sequence, Mapping))

    if len(partial_data) == 0:
        return fn

    if isinstance(partial_data, Sequence):
        return functools.partial(fn, *partial_data)
    elif isinstance(partial_data, Mapping):
        if '*args' not in partial_data:
            return functools.partial(fn, **partial_data)

        keyword_args = {k: v for k, v in partial_data.items() if k != '*args'}
        star_args = partial_data['*args']
        assert isinstance(star_args, Sequence)
        return functools.partial(fn, *star_args, **keyword_args)
    else:
        raise ValueError()
