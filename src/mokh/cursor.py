"""
Recursive traversal through and searching of `mokh.config.Config` instances.
"""

from typing import Any

from .config import CURRENT_CONFIG, Config, ConfigSlot, Value, merge_configs

# See https://peps.python.org/pep-0661/
_SENTINEL_RAISE_ERROR = object()


def get(
    key: str,
    /,
    *,
    default: Any = _SENTINEL_RAISE_ERROR,
) -> Any:
    """
    Retrieve the corresponding value for the key if found in
    `mokh.config.CURRENT_CONFIG` via `CONFIG_CURSOR`.

    Default behavior is to raise error if not found. Set `default` to any value
    to make it the default.
    """
    out = _search_config(key)
    if out is not None:
        return out.data
    if default is _SENTINEL_RAISE_ERROR:
        raise ValueError(f'{repr(key)} not found in current config search index')
    return default


class ConfigCursor:
    """Manage searching within a specific config/path pair.

    Should be considered immutable -- directly modifying anything is
    unsupported. Instead, use `descend` and `__init__` to create altered
    instances of `ConfigCursor`.
    """

    # None of these should ever be altered, only (potentially) reassigned.
    base_config: Config
    config: Config
    full_path: list[str]

    # Reset cache(s) any time the above fields are reassigned.
    _cache_descend: dict[str, 'ConfigCursor']

    def __init__(self, base_config: Config, full_path: list[str] = []):
        self.base_config = base_config
        self.config = base_config
        self.full_path = []
        self._cache_descend = {}

        for key in full_path:
            self._descend_inplace(key)

    def descend(self, key: str) -> 'ConfigCursor':
        if key in self._cache_descend:
            return self._cache_descend[key]
        out = self._copy()
        out._descend_inplace(key)
        self._cache_descend[key] = out
        return out

    def search(self, key: str) -> Value | None:
        if (
            key in self.config.children
            and self.config.children[key].value is not None
        ):
            return self.config.children[key].value

        return None

    def _descend_inplace(self, key: str):
        self.full_path = self.full_path + [key]
        self._cache_descend.clear()

        sub_config = self.config.get([key])
        if sub_config is None:
            return

        self.config = merge_configs(self.config, sub_config)

    def _copy(self) -> 'ConfigCursor':
        out = ConfigCursor.__new__(ConfigCursor)
        out.base_config = self.base_config
        out.config = self.config
        out.full_path = self.full_path
        out._cache_descend = {}
        return out


class ConfigCursorSlot:
    def __init__(self, cursor: ConfigCursor):
        self.slot = cursor

    def check(self, current_config: ConfigSlot = CURRENT_CONFIG):
        """Re-create the contained `ConfigCursor` if it no longer matches the
        current config.
        """
        if current_config.slot is not self.slot.base_config:
            self.slot = ConfigCursor(current_config.slot, self.slot.full_path)


CONFIG_CURSOR: ConfigCursorSlot = ConfigCursorSlot(ConfigCursor(CURRENT_CONFIG.slot))


def _search_config(
    key: str,
    *,
    cursor: ConfigCursorSlot = CONFIG_CURSOR,
    current_config: ConfigSlot = CURRENT_CONFIG,
) -> Value | None:
    cursor.check(current_config)
    return cursor.slot.search(key)
