import logging

class InvalidAuthTokenError(Exception):
    def __init__(self, auth_token, message=''):
        message = message or (
            f"invalid auth token `{auth_token}`. it should be a 64 character alphanumeric string. "
            'if you believe this is a mistake, set `validate_auth_token` to `False`'
        )
        super().__init__(message)


class AnonymousConnectionError(Exception):
    def __init__(self, message='connection is anonymous'):
        message = f"{message}: no auth token provided"

        logging.warning(message)

        super().__init__(message)


class AnonymousSessionError(Exception):
    def __init__(self, message='session is anonymous'):
        message = f"{message}: no session id provided"

        logging.warning(message)

        super().__init__(message)


class InvalidMessageError(Exception):
    def __init__(self, message=''):
        message = message or 'message length should be in inclusive range [1, 512]'

        logging.warning(message)

        super().__init__(message)


class DumbFucksBeware(Exception):
    def __init__(self, message):
        super().__init__(
            f"{message}\n"
            "If you end up doing some dumb shit and getting banned from dgg, "
            "I take no responsibility from this point on. "
            "In any case, have a look at the source code."
        )


class APIError(Exception):
    def __init__(self, endpoint, response):
        message = f"failed to call `{endpoint}`: {response.status_code} `{response.content.decode()}`"
        logging.warning(message)
        super().__init__(message)


class CDNError(Exception):
    def __init__(self, message='CDN error'):
        super().__init__(message)
