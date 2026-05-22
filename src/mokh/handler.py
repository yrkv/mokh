from collections.abc import Callable
from typing import Any

type Handler = Callable[[Any], Any]


def for_each(
    h: Handler,
) -> Handler:
    """Wrap a `Handler` to invoke it for every item in the config value."""

    def out(value: Any) -> Any:
        if isinstance(value, (list, tuple)):
            return [h(val) for val in value]
        elif isinstance(value, dict):
            return {key: h(val) for key, val in value.items()}
        else:
            raise ValueError()

    return out
