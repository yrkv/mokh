import argparse
import json
import re
import warnings
from pathlib import Path
from typing import Any

import yaml

from .common import is_dict_str_Any
from .config import ConfigureContextManager, build_config
from .trie import TrieNode


def configure(
    source: dict[str, Any] = {},
    /,
    **kwargs: Any,
) -> ConfigureContextManager:
    """Apply configuration values within some context.

    This interprets the args as a config source and updates
    `mokh.config.CURRENT_CONFIG` with it.

    Basic usage is to set config value(s) within a context. Then, those values
    are accessible to `mokh.get` and applied to `@mokh.configurable` functions
    called from that context.
    ```python
    @mokh.configurable()
    def some_func(*, a):
        print(f'a={a}')

    with mokh.configure(a=10, b=20):
        some_func() # prints "a=10"
        print(f'b={mokh.get("b")}') # prints "b=20"
    ```

    More advanced usage would utilize nested dicts and/or dot-separated paths
    to control which `mokh.configurable()` context to apply within.
    ```python
    @mokh.configurable()
    def fn_a(*, x): print(f'fn_a: x={x}')
    @mokh.configurable()
    def fn_b(*, x):
        fn_a()
        print(f'fn_b: x={x}')

    with mokh.configure({
        'x': 1, # default value is x=1
        'fn_a.x': 2, # but within fn_a, x=2
        'fn_b.fn_a.x': 3, # except when fn_a is called from fn_b, then x=3
    }):
        fn_a()
        # fn_a: x=2
        fn_b()
        # fn_a: x=3
        # fn_b: x=1
    ```
    """

    if len(source) > 0 and len(kwargs) > 0:
        raise ValueError(
            'Provide either a single positional arg or keyword arguments, not both'
        )

    if source == {}:
        source = kwargs

    config = build_config(source)
    return ConfigureContextManager(lambda c: c.merge(config))


def _config_from_file(
    p: Path,
) -> TrieNode:
    if not p.exists():
        raise ErrMissing(f"No such file: '{p}'")
    if not p.is_file():
        raise ErrNotFile(f"Not a regular file: '{p}'")

    match p.suffix:
        case '.json':
            with open(p, 'rt') as f:
                source = json.load(f)
        case '.toml':
            try:
                import tomllib  # type: ignore[import-not-found]
            except ModuleNotFoundError as e:
                raise ErrUnsupported(
                    'mokh: TOML support requires Python 3.11+'
                ) from e

            with open(p, 'rb') as f:
                source = tomllib.load(f)
        case '.yaml':
            with open(p, 'rt') as f:
                source = yaml.safe_load(f)
        case _:
            raise ErrUnsupported(f"Unsupported config filetype: '{p.suffix}'")

    if not is_dict_str_Any(source):
        raise ErrInvalidData(
            f"Invalid data of type '{type(source)}' in config file '{p}'"
        )

    return build_config(source)


def configure_file(
    path: Path | str,
    /,
    *,
    on_missing: str = 'warn',
    on_not_file: str = 'error',
    on_unsupported: str = 'error',
    on_invalid_data: str = 'error',
    on_any_error: str | None = None,
) -> ConfigureContextManager:
    """Variant of `configure` which reads a file for the config.

    `configure_file` allows defining handling of each possible error:
    - `on_*` define behavior for each possible error:
        - `"error"` -- raise the error.
        - `"warn"` -- log a warning to stderr.
        - `"ignore"` -- do nothing.
    - `on_any_error` overrides all others, if set.
    - Note default values for each option in function signature.
    """

    path = Path(path)
    try:
        config = _config_from_file(path)
    except ConfigError as e:
        handlers = {
            ErrMissing: on_missing,
            ErrNotFile: on_not_file,
            ErrUnsupported: on_unsupported,
            ErrInvalidData: on_invalid_data,
        }
        mode = on_any_error or handlers[type(e)]
        match mode:
            case 'error':
                raise
            case 'warn':
                warnings.warn(str(e), stacklevel=2)
            case 'ignore':
                pass
            case _:
                raise ValueError(
                    f"Invalid mode '{mode}'. Expected one of 'error', 'warn', 'ignore'"
                )

        return ConfigureContextManager(lambda c: c)

    return ConfigureContextManager(lambda c: c.merge(config))


def configure_cli(
    short: str | None = '-c',
    long: str | None = '--config',
) -> ConfigureContextManager:
    """Variant of `configure` which gathers config values using arguments.

    Using `argparse`, it registers `-c` and `--config` to set configuration
    values. If provided with `<key>=<value>`, it attempts to interpret the value
    as json and set that key to that value. If provided with a file path, it
    checks for that file and tries to load it as configuration values. Each such
    arg is applied in order from left to right, with later configuration parts
    overwriting earlier parts.

    For example, let's say the original cmdline is `python train.py -c
    base_config.json -c overflow=1`, and `configure_from_args()` is called from
    somewhere within `train.py`. The file `base_config.json` is found and read
    for configuration values. Then, the configuration key "overflow" is set to
    value 1. This is applied as a context manager, just as if those same values
    had been set with a `configure()` call.
    """

    parser = argparse.ArgumentParser()

    assert short is not None or long is not None
    arg_short = [] if short is None else [short]
    arg_long = [] if long is None else [long]
    parser.add_argument(*arg_short, *arg_long, type=str, action='append')

    # TODO:
    # parser.add_argument(
    #    '--mokh.query_functions', type=bool, action='store_true'
    # )
    # parser.add_argument(
    #    '--mokh.query_params', type=bool, action='store_true'
    # )
    # parser.add_argument(
    #    '--mokh.generate_config', type=bool, action='store_true',
    #    help="""
    #    Instead of continuing with the program, print to standard output a
    #    json config containing the minimal configuration such that (A) all
    #    current values are preserved and (B) all functions are callable. Any
    #    unknown values are set to null, which maps to None in python.
    #    """.strip()
    # )

    args, _ = parser.parse_known_args()

    if args.config is None:
        return ConfigureContextManager(lambda c: c)

    configs = []
    for c in args.config:
        # first case is a JSON object string
        match_json = re.match(r'\{.*\}', c.strip(), re.DOTALL)
        if match_json is not None:
            j = json.loads(c)
            assert is_dict_str_Any(j)
            configs.append(build_config(j))
            continue

        # second case is {key}={value}
        match_key_eq_value = re.match('([^=]+)=([^=]+)', c.strip())
        if match_key_eq_value is not None:
            key, value = match_key_eq_value.groups()
            value = json.loads(value)
            configs.append(build_config({key: value}))
            continue

        # third case is to read it as a file
        p = Path(c)
        configs.append(_config_from_file(p))

    merged_config = TrieNode()
    for config in configs:
        merged_config = merged_config.merge(config)

    return ConfigureContextManager(lambda c: c.merge(merged_config))


class ConfigError(Exception):
    """Base class for errors related to `mokh` processing of config files."""


class ErrMissing(ConfigError, FileNotFoundError):
    """File does not exist."""


class ErrNotFile(ConfigError, ValueError):
    """File is not a regular file (e.g. directory)"""


class ErrUnsupported(ConfigError, ValueError):
    """Unsupported file extension provide."""


class ErrInvalidData(ConfigError, ValueError):
    """Invalid configuration data (e.g. not a mapping at top-level)."""
