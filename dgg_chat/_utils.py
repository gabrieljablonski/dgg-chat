from types import MethodType
from json import dumps


def format_payload(type, **kwargs):
    return f"{type} {dumps(kwargs)}"


def bind_method(method, obj):
    return MethodType(lambda self, *args: method(*args), obj)
