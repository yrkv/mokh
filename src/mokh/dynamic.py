from types import ModuleType
from typing import Any, Callable

from .common import ConfigSource

type Handler = Callable[[ConfigSource], Any]

type Context = ModuleType | dict[str, Any]


def listHandler(h: Handler) -> Handler:
    def out(config: ConfigSource) -> list[Any]:
        assert isinstance(config, list)
        return [h(val) for val in config]

    return out


def dictHandler(h: Handler) -> Handler:
    def out(config: ConfigSource) -> dict[str, Any]:
        assert isinstance(config, dict)
        return {key: h(val) for key, val in config.items()}

    return out


def lookup(context: Context) -> Handler:
    # stub; TODO: implement
    return lambda c: None


def dispatch(context: Context) -> Handler:
    # stub; TODO: implement
    return lambda c: None
