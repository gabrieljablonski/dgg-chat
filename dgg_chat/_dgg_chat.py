import time
import logging
import queue
from os import getenv
from queue import Queue
from sched import scheduler
from threading import Thread
from websocket import WebSocketApp
from websocket._exceptions import WebSocketException

from .messages import Message, MessageTypes
from ._utils import format_payload, bind_method
from ._handler import DGGChatHandler


class InvalidAuthTokenError(Exception):
    def __init__(self, auth_token, message=''):
        message = message or (
            f"invalid auth token `{auth_token}`. it should be a 64 character alphanumeric string. "
            'if you believe this is a mistake, set `validate_auth_token` to `False`'
        )
        super().__init__(message)


class AnonymousConnectionError(Exception):
    pass


class InvalidMessageError(Exception):
    def __init__(self, message=''):
        message = message or 'message length should be in inclusive range [1, 512]'
        super().__init__(message)


class DumbFucksBeware(Exception):
    def __init__(self, message):
        super().__init__(
            f"{message}\n"
            "If you end up doing some dumb shit and getting banned from dgg, "
            "I take no responsibility from this point on. "
            "In any case, have a look at the source code."
        )

# TODO: retrieve unread messages
class DGGChat:
    DGG_WS = 'wss://destiny.gg/ws'
    WAIT_BOOTSTRAP = 1  # in seconds
    # considering server throttle is 300ms and some network overhead
    THROTTLE_DELAY = .200  # in seconds
    # after this much time after last sent message, throttle factor is reset
    THROTTLE_RESET = 600  # in seconds
    # throttling should be a very exceptional case, so instead of starting at 1,
    # a bit of padding ensures it doesn't happen multiple times in a row
    BASE_THROTTLE_FACTOR = 1.1

    def __init__(
        self, auth_token=None, validate_auth_token=True,
        try_resend_on_throttle=True, on_close=None,
        on_any_message=None, on_served_connections=None, 
        on_user_joined=None, on_user_quit=None,
        on_broadcast=None, on_chat_message=None,
        on_whisper=None, on_whisper_sent=None,
        on_mute=None, on_unmute=None, 
        on_ban=None, on_unban=None,
        on_sub_only=None, on_error_message=None,
    ):
        if validate_auth_token and not self.auth_token_is_valid(auth_token):
            raise InvalidAuthTokenError(auth_token)

        any_specific_handler_was_set = any([
            on_served_connections, on_user_joined, on_user_quit,
            on_broadcast, on_chat_message, on_whisper, on_whisper_sent, 
            on_mute, on_unmute, on_ban, on_unban, 
            on_sub_only, on_error_message
        ])
        if on_any_message != None and any_specific_handler_was_set:
            raise ValueError(
                'if `on_any_message` is provided, no other `on_` event '
                'can be set (aside from `on_close`)'
            )

        self.try_resend_on_throttle = try_resend_on_throttle
        
        self._running = False
        self._auth_token = auth_token

        self._last_message_time = 0
        self._next_message_time = time.time()
        self._throttle_factor = self.BASE_THROTTLE_FACTOR

        self._queued_messages = Queue()
        self._unhandled_messages = Queue(maxsize=1)
        Thread(target=self._send_loop, daemon=True).start()

        self._available_users_to_whisper = set()

        def _on_message(ws, message):
            """The top level message handling function."""
            parsed = Message.parse(message)
            logging.debug(f"received message: `{message}`")
            logging.debug(f"parsed message: `{parsed}`")
            if not self._unhandled_messages.empty() and parsed.type in (MessageTypes.ERROR, MessageTypes.WHISPER_SENT):
                try:
                    payload = self._unhandled_messages.get_nowait()
                except queue.Empty as e:
                    logging.fatal('unhandled messages queue was empty')
                    raise e
                now = time.time()
                if now >= self._last_message_time + self.THROTTLE_RESET:
                    logging.info('resetting throttle factor')
                    self._throttle_factor = self.BASE_THROTTLE_FACTOR
                if parsed.type == MessageTypes.ERROR:
                    # max throttle factor seems to be 16 (16*.3=5s)
                    # verified empirically since this doesn't match the source code (https://github.com/destinygg/chat/blob/master/connection.go#L407)
                    if parsed.payload == 'throttled':
                        logging.warning('connection throttled')
                        self._throttle_factor = min(16, 2*self._throttle_factor)
                        if self.try_resend_on_throttle:
                            # default behaviour when throttled is to try and resend
                            self._queued_messages.put(payload)
                    if parsed.payload == 'duplicate':
                        logging.warning('duplicate message')
                        self._throttle_factor = min(16, 1+self._throttle_factor)
                else:
                    self._last_message_time = now
                self._next_message_time = now + self._throttle_factor*self.THROTTLE_DELAY
            if parsed.type == MessageTypes.WHISPER:
                self._available_users_to_whisper.add(parsed.user.nick)
            self._handler.on_any_message(self, parsed)

        #  (`on_error_message` is business related, i.e. `ERR` messages)
        def _on_error(ws, error):
            """Handler for websocket related errors."""
            msg = f"websocket error: `{error}`"
            logging.error(msg)
            raise WebSocketException(msg)

        def _on_close(ws):
            self._running = False
            logging.info('connection closed')

        on_close = on_close or _on_close
        
        self._handler = DGGChatHandler(
            on_any_message, on_served_connections, 
            on_user_joined, on_user_quit,
            on_broadcast, on_chat_message, 
            on_whisper, on_whisper_sent,
            on_mute, on_unban, on_ban, on_unban,
            on_sub_only, on_error_message
        )

        self._ws = WebSocketApp(
            self.DGG_WS,
            on_message=_on_message,
            on_error=_on_error,
            on_close=on_close,
            cookie=f"authtoken={self._auth_token}" if self._auth_token else None
        )

    @property
    def throttle_factor(self):
        return self._throttle_factor

    @staticmethod
    def auth_token_is_valid(token):
        return len(token) == 64 and token.isalnum()

    @staticmethod
    def message_is_valid(msg):
        return 0 < len(msg) <= 512
        
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()
        
    def connect(self, *args, **kwargs):
        if self._running:
            raise ConnectionError('chat is already connected')
        logging.info('setting up connection')
        t = Thread(target=self._ws.run_forever, daemon=True, args=args, kwargs=kwargs)
        t.start()
        time.sleep(self.WAIT_BOOTSTRAP)
        logging.info('connected')
        self._running = True
        return t

    def disconnect(self):
        if not self._running:
            raise ConnectionError('chat is not connected')
        logging.info('disconnecting')
        self._ws.close()
        logging.info('disconnected')
        self._running = False

    def run_forever(self, *args, **kwargs):
        if self._running:
            logging.fatal('chat already connected')
            raise ConnectionError('chat already connected, call `disconnect()` first')
        logging.info('running websocket on loop')
        self._ws.run_forever(*args, **kwargs)

    def _send_loop(self):
        while True:
            while not self._unhandled_messages.empty():
                continue
            while not self._next_message_time or time.time() < self._next_message_time:
                continue
            self._next_message_time = 0
            payload = self._queued_messages.get()
            logging.debug(f"sending payload: `{payload}`")
            self._ws.send(payload)
            self._unhandled_messages.put(payload)

    def _queue_message(self, type, **kwargs):
        payload = format_payload(type, **kwargs)
        logging.debug(f"enqueueing payload: `{payload}`")
        self._queued_messages.put(payload)

    def send_chat_message(self, message):
        if not self.message_is_valid(message):
            raise InvalidMessageError

        if not self._auth_token:
            logging.fatal("can't send chat message: anonymous connection")
            raise AnonymousConnectionError('`auth_token` must be informed to send chat messages')
        enabled = str(getenv('DGG_ENABLE_CHAT_MESSAGES')).lower()
        if not enabled or enabled in ('none', 'false'):
            raise DumbFucksBeware("sending chat messages is currently disabled")
        logging.info('sending chat message')
        self._queue_message(MessageTypes.CHAT_MESSAGE, data=message)

    def send_whisper(self, user, message):
        if not self.message_is_valid(message):
            raise InvalidMessageError
        
        if not self._auth_token:
            logging.fatal("can't send whisper: anonymous connection")
            raise AnonymousConnectionError('`auth_token` must be informed to send whispers')
        logging.info('sending whisper')
        enabled = str(getenv('DGG_ENABLE_WHISPER_FIRST')).lower()
        if (not enabled or enabled in ('none', 'false')) and user not in self._available_users_to_whisper:
            raise DumbFucksBeware("whispers can only be sent to users who whispered you first this session")
        self._queue_message(MessageTypes.WHISPER, nick=user, data=message)
