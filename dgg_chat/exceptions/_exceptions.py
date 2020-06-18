import logging


class APIError(Exception):
    def __init__(self, endpoint, response):
        message = f"failed to call `{endpoint}`: {response.status_code} `{response.content.decode('utf8')}`"
        logging.warning(message)
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


class CDNError(Exception):
    def __init__(self, message='CDN error'):
        super().__init__(message)


class DumbFucksBeware(Exception):
    def __init__(self, message):
        super().__init__(
            f"{message}\n"
            "If you end up doing some dumb shit and getting banned from dgg, "
            "I take no responsibility from this point on. "
            "In any case, have a look at the source code to get what you need."
        )


class InvalidAuthTokenError(Exception):
    def __init__(self, auth_token, message=''):
        message = message or (
            f"invalid auth token `{auth_token}`. it should be a 64 character alphanumeric string. "
            'if you believe this is a mistake, set `validate_auth_token` to `False`'
        )
        super().__init__(message)


class InvalidChatLine(Exception):
    def __init__(self, line):
        super().__init__(line)


class InvalidMessageError(Exception):
    def __init__(self, message):
        message = f"message length should be between 1 and 512 characters: `{message}`"

        logging.warning(message)

        super().__init__(message)
