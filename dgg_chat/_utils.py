from re import compile
from json import dumps
from types import MethodType
from datetime import datetime


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


def format_datetime(dt, fmt='%Y-%m-%d %H:%M:%S', with_ms=False):
    if with_ms:
        fmt = f"{fmt}.%f"
    return dt.strftime(fmt)


def validate_date_time(year=1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0):
    datetime(year, month, day, hour, minute, second, microsecond)


def isplit(source, sep=None, regex=False):
    """
    https://stackoverflow.com/a/9773142
    generator version of str.split()

    :param source:
        source string (unicode or bytes)

    :param sep:
        separator to split on.

    :param regex:
        if True, will treat sep as regular expression.

    :returns:
        generator yielding elements of string.
    """
    if sep is None:
        # mimic default python behavior
        source = source.strip()
        sep = "\\s+"
        if isinstance(source, bytes):
            sep = sep.encode("ascii")
        regex = True
    if regex:
        # version using re.finditer()
        if not hasattr(sep, "finditer"):
            sep = re.compile(sep)
        start = 0
        for m in sep.finditer(source):
            idx = m.start()
            assert idx >= start
            yield source[start:idx]
            start = m.end()
        yield source[start:]
    else:
        # version using str.find(), less overhead than re.finditer()
        sepsize = len(sep)
        start = 0
        while True:
            idx = source.find(sep, start)
            if idx == -1:
                yield source[start:]
                return
            yield source[start:idx]
            start = idx + sepsize
