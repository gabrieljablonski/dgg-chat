import time
import logging
import queue
from os import getenv
from queue import Queue
from threading import Thread
from websocket import WebSocketApp
from websocket._exceptions import WebSocketException

from .exceptions import (
    DumbFucksBeware,
    InvalidMessageError,
    InvalidAuthTokenError,
    AnonymousConnectionError,
    AnonymousSessionError
)
from .messages import Message, MessageTypes, ChatUser
from .handler import DGGChatHandler
from .api import DGGAPI, User
from ._utils import format_payload


class DGGChat:
    """
    A dgg chat API.    
    """

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
        self, handler: DGGChatHandler = None,
        auth_token=None, session_id=None,
        validate_auth_token=True,
        handle_history=False,
        handle_unread_whispers=False,
        mark_as_read=False,
        try_resend_on_throttle=True
    ):
        """
        Parameters
        ----------
        `handler` : `DGGHandler`

            an instance of `DGGHandler` class (or a subclass).
            defines what to do when stuff happens in chat.

        `auth_token` : `str`

            an authentication token for a dgg account.
            can be created at `https://www.destiny.gg/profile/developer`.

        `session_id` : `str`

            a session id for a dgg connection. used for profile related stuff.
            currently needs to be set manually by logging in on the browser and copying the cookie.

        `validate_auth_token` : `bool`

            whether the token should be validated. `True` by default.
            (should only be needed to disable it if something's changed in how tokens are generated)

        `handle_history` : `bool`

            whether the previous 150 most recent messages from before connection should be handled.
            `False` by default.

        `handle_unread_whispers` : `bool`

            whether unread whispers should be handled. requires `session_id` to work.
            `False` by default.

        `mark_as_read` : `bool`

            whether after handling a whisper it should be marked as read in the chat backend.
            doing so will stop it from showing up when calling `get_unread_whispers()`.
            if disabled, `get_unread_whispers()` can be called manually.
            requires `session_id` to work.
            `False` by default.

        `try_resend_on_throttle` : `bool`

            whether to try to resend a chat message or whisper when it fails because of throttling.
            if disabled, resending can be done in the `on_error_message()` handler.
            `True` by default.
        """

        if auth_token and validate_auth_token and not self.auth_token_is_valid(auth_token):
            raise InvalidAuthTokenError(auth_token)

        self._auth_token = auth_token
        self._session_id = session_id

        self.mark_as_read = mark_as_read
        self.try_resend_on_throttle = try_resend_on_throttle

        self._running = False
        self._last_message_time = 0
        self._next_message_time = time.time()
        self._throttle_factor = self.BASE_THROTTLE_FACTOR

        self._queued_messages = Queue()
        self._unhandled_messages = Queue()

        self._available_users_to_whisper = set()

        self._handler = DGGChatHandler(self)

        if handler:
            handler.chat = self
            handler.backup_handler = self._handler
            self._handler = handler

        self._api = DGGAPI(auth_token)

        self._me = self._update_profile() if auth_token else None

        if handle_unread_whispers:
            self._handle_unread_whispers()

        if handle_history:
            self._handle_history()

        def _on_message(ws, message):
            """The top level message handling function."""

            parsed = Message.parse(message)

            logging.debug(f"received message: `{message}`")
            logging.info(f"parsed message: `{parsed}`")

            if not self._unhandled_messages.empty() and parsed.type in (MessageTypes.ERROR, MessageTypes.WHISPER_SENT):
                self._handle_message(parsed)

            if parsed.type == MessageTypes.WHISPER:
                self._available_users_to_whisper.add(parsed.user.nick)
                msg = f"{parsed.user.nick} added to users available to whisper"
                logging.info(msg)

            if self._me and parsed.type == MessageTypes.CHAT_MESSAGE and self._me.nick in parsed.content:
                self._handler.handle_special(MessageTypes.Special.ON_MENTION, parsed)

            self._handler.handle_message(parsed)
            if parsed.type == MessageTypes.WHISPER and self.mark_as_read:
                self.mark_all_as_read(parsed.user)

        #  `on_error_message` is business related, i.e. `ERR` messages
        def on_error(ws, error):
            """Handler for websocket related errors."""

            self._handler.handle_special(MessageTypes.Special.ON_WS_ERROR, error)

            msg = f"websocket error: `{error}`"

            logging.error(msg)
            raise WebSocketException(msg)

        def on_close(ws):
            """Handler for when the websocket connection is closed."""

            self._handler.handle_special(MessageTypes.Special.ON_WS_CLOSE)
            self._running = False

            logging.info('connection closed')

        self._ws = WebSocketApp(
            self.DGG_WS,
            on_message=_on_message,
            on_error=on_error,
            on_close=on_close,
            cookie=f"authtoken={self._auth_token}" if self._auth_token else None
        )

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    @property
    def throttle_factor(self):
        return self._throttle_factor

    @property
    def me(self):
        return self._me

    @staticmethod
    def auth_token_is_valid(token):
        return len(token) == 64 and token.isalnum()

    @staticmethod
    def message_is_valid(msg):
        return 0 < len(msg) <= 512

    def _update_profile(self):
        self._me = self._api.user_info()
        logging.info(f"profile updated: {self._me}")

    def _handle_history(self):
        """Handles the 150 most recent chat messages up until chat is connected."""

        logging.info('handling history')

        history = self._api.chat_history()
        for message in history:
            self._handler.handle_message(Message.parse(message))

    def _handle_unread_whispers(self):
        """Handles unread whispers. Marks them as read."""

        if not self._session_id:
            raise AnonymousConnectionError('unable to handle unread whispers')

        logging.info('handling unread whispers')

        unread = self.get_unread_whispers()
        for user, whispers in unread.items():
            for whisper in whispers:
                if whisper.target_user == self._me.nick:
                    self._handler.handle_message(whisper.as_websocket_message)

    def _handle_message(self, message):
        try:
            payload = self._unhandled_messages.get_nowait()
        except queue.Empty as e:
            logging.fatal('unhandled messages queue was empty')
            raise e

        now = time.time()
        if now >= self._last_message_time + self.THROTTLE_RESET:
            logging.info('resetting throttle factor')
            self._throttle_factor = self.BASE_THROTTLE_FACTOR

        if message.type == MessageTypes.ERROR:
            # max throttle factor seems to be 16 (16*.3=5s)
            # verified empirically since this doesn't match the source code (https://github.com/destinygg/chat/blob/master/connection.go#L407)
            if message.payload == 'throttled':
                logging.warning('connection throttled')
                self._throttle_factor = min(16, 2*self._throttle_factor)
                if self.try_resend_on_throttle:
                    # default behaviour when throttled is to try and resend
                    self._queued_messages.put(payload)

            if message.payload == 'duplicate':
                logging.warning('duplicate message')
                self._throttle_factor = min(16, 1 + self._throttle_factor)
        else:
            self._last_message_time = now

        self._next_message_time = now + self._throttle_factor*self.THROTTLE_DELAY

    def _start_send_loop(self):
        Thread(target=self._send_loop, daemon=True).start()

    def _send_loop(self):
        while True:
            while not self._unhandled_messages.empty():
                continue

            while not self._next_message_time or time.time() < self._next_message_time:
                continue

            if not self._running:
                break

            self._next_message_time = 0

            payload = self._queued_messages.get()
            logging.debug(f"sending payload: `{payload}`")

            self._ws.send(payload)
            self._unhandled_messages.put(payload)

    def _queue_message(self, type, **kwargs):
        payload = format_payload(type, **kwargs)
        logging.debug(f"enqueueing payload: `{payload}`")
        self._queued_messages.put(payload)

    def update_profile(self):
        """Updates `self.me` with info from the auth token's account."""

        if not self._me:
            raise AnonymousConnectionError('unable to update profile')

        self._update_profile()

    def get_unread_whispers(self, from_user=None):
        """
        Retrieves all unread whispers. Includes the messages sent to the user.
        All of them are marked as read.
        """

        if not self._session_id:
            raise AnonymousSessionError('unable to get unread messages')

        unread = self._api.messages_unread()
        messages = {}

        if from_user:
            if from_user in unread:
                messages[from_user] = self._api.messages_inbox(from_user)
            else:
                messages[from_user] = []
            return messages

        for user, count in unread.items():
            messages[user] = self._api.messages_inbox(user)

        return messages

    def connect(self):
        """Connect to chat and run in a new thread (non-blocking)."""

        if self._running:
            raise ConnectionError('chat is already connected')

        logging.info('setting up connection')
        t = Thread(target=self.run_forever, daemon=True)
        t.start()

        time.sleep(self.WAIT_BOOTSTRAP)
        logging.info('connected')
        return t

    def disconnect(self):
        if not self._running:
            raise ConnectionError('chat is not connected')

        logging.info('disconnecting')
        self._ws.close()

        logging.info('disconnected')
        self._running = False

    def run_forever(self):
        """Connect to chat and blocks the thread."""

        if self._running:
            msg = 'chat already connected, call `disconnect()` first'
            raise ConnectionError(msg)

        logging.info('running websocket on loop')
        self._running = True
        self._start_send_loop()

        while self._ws.run_forever():
            pass

    def send_chat_message(self, message):
        if not self.message_is_valid(message):
            raise InvalidMessageError

        if not self._auth_token:
            raise AnonymousConnectionError('unable to send chat messages')

        if not self._running:
            raise ConnectionError('chat is not connected')

        enabled = str(getenv('DGG_ENABLE_CHAT_MESSAGES')).lower()
        if not enabled or enabled in ('none', 'false'):
            msg = 'sending chat messages is currently disabled'
            raise DumbFucksBeware(msg)

        logging.info('sending chat message')
        self._queue_message(MessageTypes.CHAT_MESSAGE, data=message)

    def send_whisper(self, user, message):
        if not self.message_is_valid(message):
            raise InvalidMessageError

        if not self._auth_token:
            raise AnonymousConnectionError('unable to send whispers')

        if self._me and self._me.nick == user:
            raise ValueError("you can't whisper yourself, you silly goose")

        if not self._running:
            raise ConnectionError('chat is not connected')

        enabled = str(getenv('DGG_ENABLE_WHISPER_FIRST')).lower()
        if (not enabled or enabled in ('none', 'false')) and user not in self._available_users_to_whisper:
            msg = 'whispers can only be sent to users who whispered you in this session'
            raise DumbFucksBeware(msg)

        logging.info('sending whisper')
        self._queue_message(MessageTypes.WHISPER, nick=user, data=message)
