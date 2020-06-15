from re import compile
from types import MethodType
from json import dumps


_CAMEL_SNAKE_PATTERN = compile(r'(?<!^)(?=[A-Z])')


def format_payload(type, **kwargs):
    """Formats a message to the DGG websocket format."""
    return f"{type} {dumps(kwargs)}"


def dict_swap_keys(d, key_map):
    swapped = d.copy()
    for key in d:
        if key in key_map:
            new_key = key_map[key]
            swapped[new_key] = swapped.pop(key)
    return swapped


def camel_to_snake_case(s):
    return _CAMEL_SNAKE_PATTERN.sub('_', s).lower()


def dict_keys_camel_to_snake_case(d):
    snaked = d.copy()
    for key in d:
        new_key = camel_to_snake_case(key)
        snaked[new_key] = snaked.pop(key)
    return snaked
