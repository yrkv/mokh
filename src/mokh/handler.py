from collections.abc import Callable
from typing import Any, TypeVar, overload

A = TypeVar('A')
B = TypeVar('B')


def optional(
    h: Callable[[A], B],
) -> Callable[[A | None], B | None]:
    """Wrap a handler to simply return `None` if the value is `None`, otherwise
    invoke it."""

    def out(value: A | None) -> B | None:
        if value is None:
            return value

        return h(value)

    return out


K = TypeVar('K')


@overload
def for_each(h: Callable[[A], B]) -> Callable[[list[A]], list[B]]: ...
@overload
def for_each(h: Callable[[A], B]) -> Callable[[tuple[A, ...]], tuple[B, ...]]: ...
@overload
def for_each(h: Callable[[A], B]) -> Callable[[dict[K, A]], dict[K, B]]: ...


def for_each(
    h: Callable[[A], B],
) -> Callable[[Any], Any]:
    """Wrap a handler to invoke it for every item in the value."""

    def out(value: Any) -> Any:
        if isinstance(value, list):
            return [h(val) for val in value]
        if isinstance(value, tuple):
            return tuple(h(val) for val in value)
        elif isinstance(value, dict):
            return {key: h(val) for key, val in value.items()}
        else:
            raise ValueError()

    return out
