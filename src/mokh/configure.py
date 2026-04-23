import argparse
import json
import re
import tomllib
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

import yaml

from .common import is_dict_str_Any
from .configuration import (
    ConfigContextManager,
    ConfigSource,
    Configuration,
    ConfigurationDict,
    merge_configurations,
)


def _configuration_from_file(
    p: Path | str,
    on_missing: str = 'error',  # one of "error","warn","ignore"
) -> Configuration:
    p = Path(p)
    if not p.exists():
        match on_missing:
            case 'error':
                raise FileNotFoundError(f"No such file: '{p}'")
            case 'warn':
                ...  # TODO: warning
                return Configuration({})
            case 'ignore':
                return Configuration({})

    assert p.is_file()
    match p.suffix:
        case '.json':
            with open(p, 'rt') as f:
                source = json.load(f)
        case '.toml':
            with open(p, 'rb') as f:
                source = tomllib.load(f)
        case '.yaml':
            with open(p, 'rt') as f:
                source = yaml.safe_load(f)
        case _:
            # Make a pull request to add it! :)
            raise ValueError(f'unsupported config filetype: "{p.suffix}"')
    assert is_dict_str_Any(source)
    return Configuration(source)


def configure(
    source: dict[str, ConfigSource] = {},
    **kwargs: ConfigSource,
) -> AbstractContextManager:
    if len(source) >= 1 and len(kwargs) >= 1:
        raise ValueError("Provide either 'source' or keyword arguments, not both")

    if source == {}:
        source = kwargs

    config = Configuration(source)
    return ConfigContextManager(config._map)


def configure_file(
    p: Path | str,
    on_missing: str = 'error',
) -> AbstractContextManager:

    config = _configuration_from_file(p, on_missing=on_missing)
    return ConfigContextManager(config._map)


def configure_cli() -> AbstractContextManager:
    """Gather configuration values from program arguments.

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
    parser.add_argument('-c', '--config', type=str, action='append')

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
        return nullcontext()

    configs = []
    for c in args.config:
        # first case is a JSON object string
        match_json = re.match(r'\{.*\}', c.strip(), re.DOTALL)
        if match_json is not None:
            j = json.loads(c)
            assert is_dict_str_Any(j)
            configs.append(Configuration(j))
            continue

        # second case is {key}={value}
        match_key_eq_value = re.match('([^=]+)=([^=]+)', c.strip())
        if match_key_eq_value is not None:
            key, value = match_key_eq_value.groups()
            value = json.loads(value)
            configs.append(Configuration({key: value}))
            continue

        # third case is to read it as a file
        p = Path(c)
        configs.append(_configuration_from_file(p))

    cdict: ConfigurationDict = {}
    for config in configs:
        cdict = merge_configurations(cdict, config._map)

    return ConfigContextManager(config_dict=cdict)
