import time
import logging
import queue
from os import getenv
from queue import Queue
from threading import Thread
from websocket import WebSocketApp
from websocket._exceptions import WebSocketException

from .exceptions import (
    AnonymousConnectionError,
    AnonymousSessionError,
    DumbFucksBeware,
    InvalidAuthTokenError,
    InvalidMessageError,
)
from .messages import Message, EventTypes, ChatUser
from .api import DGGAPI, User
from ._utils import format_payload
from ._handler import DGGChatEventHandler


class DGGChat:
    """
    A dgg chat API.    
    """

    DGG_WS = 'wss://destiny.gg/ws'
    RECONNECT_DELAY = 3    # in seconds
    WAIT_WS_BOOTSTRAP = 1  # in seconds
    # considering server throttle is 300ms and some network overhead
    WS_THROTTLE_DELAY = .200  # in seconds
    # after this much time after last sent message, throttle factor is reset
    WS_THROTTLE_RESET = 600  # in seconds
    # throttling should be a very exceptional case, so instead of starting at 1,
    # a bit of padding ensures it doesn't happen multiple times in a row
    BASE_WS_THROTTLE_FACTOR = 1.1

    MAX_MESSAGE_LENGTH = 512

    def __init__(
        self, auth_token=None, session_id=None,
        validate_auth_token=True,
        handle_history=False,
        handle_unread_whispers=False,
        mark_as_read=False,
        anti_throttle_bot='',
    ):
        """
        Parameters
        ----------
        `auth_token` : `str`

            an authentication token for a dgg account.
            can be created at `https://www.destiny.gg/profile/developer`.

        `session_id` : `str`

            a session id for a dgg connection. used for profile related stuff.
            currently needs to be set manually by logging in on the browser and copying the cookie.

        `validate_auth_token` : `bool`

            whether the token should be validated. `True` by default.
            (should only be needed to disable it if something's changed in how tokens are generated)

        `handle_unread_whispers` : `bool`

            whether unread whispers should be handled. requires `session_id` to work.
            handlers are called upon connecting (if `handle_history` also enabled, this happens before).
            `False` by default.

        `handle_history` : `bool`

            whether the previous 150 most recent messages from before connection should be handled.
            handlers are called upon connecting (if `handle_unread_whispers` also enabled, this happens after).
            `False` by default.

        `mark_as_read` : `bool`

            whether after handling a whisper it should be marked as read in the chat backend.
            doing so will make it so it doesn't show up when calling `get_unread_whispers()`.
            requires `session_id` to work.
            `False` by default.

        `anti_throttle_bot` : `str`

            the chat nick for an echo bot connected in chat.
            Only use it if you know what you're doing.
        """

        if auth_token and validate_auth_token and not self.auth_token_is_valid(auth_token):
            raise InvalidAuthTokenError(auth_token)

        self.mark_as_read = mark_as_read
        self.handle_history = handle_history
        self.handle_unread_whispers = handle_unread_whispers

        self._auth_token = auth_token
        self._session_id = session_id

        self._running = False
        self._users_available_to_whisper = set()

        self._last_message_time = 0
        self._next_message_time = time.time()
        self._ws_throttle_factor = self.BASE_WS_THROTTLE_FACTOR
        self._anti_throttle_bot = anti_throttle_bot

        self._queued_messages = Queue()
        self._unhandled_messages = Queue()

        self._handler = DGGChatEventHandler()
        self._api = DGGAPI(auth_token, session_id)

        self._profile = self._reload_profile() if auth_token else None

        self._setup_web_socket()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    @property
    def throttle_factor(self):
        return self._ws_throttle_factor

    @property
    def profile(self):
        return self._profile

    @property
    def api(self):
        return self._api

    @staticmethod
    def auth_token_is_valid(token):
        return len(token) == 64 and token.isalnum()

    @staticmethod
    def message_is_valid(msg):
        return 0 < len(msg) <= DGGChat.MAX_MESSAGE_LENGTH

    def _handle_errors(self):
        if self._handler.errors:
            self._handler.handle_event(EventTypes.Special.HANDLER_ERROR, self._handler.errors)
            self._handler.errors.clear()

    def _setup_web_socket(self):
        def on_message(ws, message):
            """The top-level message handling function."""

            parsed = Message.parse(message)

            logging.debug(f"received message: `{message}`")
            logging.info(f"parsed message: `{parsed}`")

            self._handler.handle_event(EventTypes.Special.BEFORE_EVERY_MESSAGE, parsed)

            if not self._unhandled_messages.empty() and parsed.event in (EventTypes.ERROR_MESSAGE, EventTypes.WHISPER_SENT):
                self._handle_message(parsed)

            if parsed.event == EventTypes.WHISPER:
                enabled = str(getenv('DGG_ENABLE_WHISPERS')).lower()
                if enabled and enabled != 'false':
                    self._users_available_to_whisper.add(parsed.user.nick)
                    logging.info(
                        f"{parsed.user.nick} added to users available to whisper"
                    )

            if self._profile and parsed.event == EventTypes.CHAT_MESSAGE and self._profile.nick in parsed.content:
                self._handler.handle_event(EventTypes.Special.MENTION, parsed)

            if parsed.event == EventTypes.WHISPER and self.mark_as_read:
                self.mark_all_as_read(parsed.user.nick)

            if parsed.event == EventTypes.WHISPER_SENT:
                # `on_whisper_sent` handler takes no arguments
                return self._handler.handle_event(parsed.event)
            self._handler.handle_event(parsed.event, parsed)
            self._handler.handle_event(EventTypes.Special.AFTER_EVERY_MESSAGE, parsed)
            self._handle_errors()

        def on_ws_error(ws, error):
            """Handler for websocket related errors."""

            self._handler.handle_event(EventTypes.Special.WS_ERROR, error)

            msg = f"websocket error: `{error}`"

            logging.error(msg)
            raise WebSocketException(msg)

        def on_close(ws):
            """Handler for when the websocket connection is closed."""

            self._handler.handle_event(EventTypes.Special.WS_CLOSE)
            self._running = False

            logging.info('connection closed')

        self._ws = WebSocketApp(
            self.DGG_WS,
            on_message=on_message,
            on_error=on_ws_error,
            on_close=on_close,
            cookie=f"authtoken={self._auth_token}" if self._auth_token else None
        )

    def _reload_profile(self):
        self._profile = self._api.user_info()
        logging.info(f"profile updated: {self._profile}")

    def _handle_history(self):
        """Handles the 150 most recent chat messages up until chat is connected."""

        logging.info('handling history')

        history = self._api.chat_history()
        for message in history:
            self._handler.handle_event(message.event, Message.parse(message))

    def _handle_unread_whispers(self):
        """Handles unread whispers. Marks them as read."""

        if not self._session_id:
            raise AnonymousConnectionError('unable to handle unread whispers')

        logging.info('handling unread whispers')

        unread = self.get_unread_whispers()
        for user, whispers in unread.items():
            for whisper in whispers:
                self._handler.handle_event(
                    whisper.event, whisper.as_websocket_message
                )

    def _handle_message(self, message):
        try:
            payload = self._unhandled_messages.get_nowait()
        except queue.Empty as e:
            logging.fatal('unhandled messages queue was empty')
            raise e

        now = time.time()
        if now >= self._last_message_time + self.WS_THROTTLE_RESET:
            logging.info('resetting throttle factor')
            self._ws_throttle_factor = self.BASE_WS_THROTTLE_FACTOR

        if message.event == EventTypes.ERROR_MESSAGE:
            # max throttle factor seems to be 16 (16*.3=5s)
            # verified empirically since this doesn't seem to match the source code (https://github.com/destinygg/chat/blob/master/connection.go#L407)
            if message.payload == 'throttled':
                logging.warning('connection throttled')
                self._ws_throttle_factor = min(16, 2*self._ws_throttle_factor)

            if message.payload == 'duplicate':
                logging.warning('duplicate message')
                self._ws_throttle_factor = min(
                    16, 1 + self._ws_throttle_factor
                )
        else:
            self._last_message_time = now

        self._next_message_time = now + self._ws_throttle_factor*self.WS_THROTTLE_DELAY

    def _start_send_loop(self):
        Thread(target=self._send_loop, daemon=True).start()

    def _send_loop(self):
        time.sleep(self.WAIT_WS_BOOTSTRAP)
        self._running = True
        while True:
            while not self._next_message_time or time.time() < self._next_message_time:
                continue

            if not self._running:
                break

            self._next_message_time = 0

            payload = self._queued_messages.get()
            logging.debug(f"sending payload: `{payload}`")

            try:
                self._ws.send(payload)
            except Exception as e:
                logging.error(f"on send loop: {e}")
                self._queued_messages.put(payload)
                continue
            
            self._unhandled_messages.put(payload)

            if self._anti_throttle_bot:
                anti_throttle_payload = format_payload(
                    EventTypes.WHISPER, nick=self._anti_throttle_bot, data='0'
                )
                logging.debug(
                    f"anti-throttle payload: `{anti_throttle_payload}`"
                )

                self._ws.send(anti_throttle_payload)
                self._unhandled_messages.put(anti_throttle_payload)

    def _queue_message(self, type, **kwargs):
        payload = format_payload(type, **kwargs)
        logging.debug(f"enqueueing payload: `{payload}`")
        self._queued_messages.put(payload)

    def update_profile(self):
        """
        Updates `self.profile` with info from the auth token's account.
        Useful on flair or subscriber status changes.
        """

        if not self._auth_token and not self._session_id:
            raise AnonymousConnectionError('unable to update profile')

        self._reload_profile()

    def mark_all_as_read(self, from_user=None):
        # TODO: implement more efficiently (use `/messages/inbox|read` endpoints)
        self.get_unread_whispers(from_user=from_user)

    def get_unread_whispers(self, from_user=None, received_only=True):
        """
        Retrieves all unread whispers. Includes the messages sent to the user.
        When `received_only` is `True`, messages sent are filtered out,
        returning only those received. All messages are marked as read.
        """

        if not self._session_id:
            raise AnonymousSessionError('unable to get unread messages')

        unread = self._api.messages_unread()
        messages = {}

        if from_user:
            if from_user in unread:
                messages[from_user] = self._api.messages_inbox(
                    from_user, unread[from_user]
                )
            else:
                messages[from_user] = []
            return messages

        for user, count in unread.items():
            messages[user] = self._api.messages_inbox(user, count)

        return messages

    def connect(self):
        """Connect to chat and run in a new thread (non-blocking)."""

        if self._running:
            raise ConnectionError('chat is already connected')

        logging.info('setting up connection')
        t = Thread(target=self.run_forever, daemon=True)
        t.start()

        time.sleep(self.WAIT_WS_BOOTSTRAP)
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
        """Connect to chat and block the thread."""

        if self._running:
            raise ConnectionError(
                'chat already connected, call `disconnect()` first'
            )
        
        if self.handle_unread_whispers:
            self._handle_unread_whispers()

        if self.handle_history:
            self._handle_history()

        self._handle_errors()

        logging.info('running websocket on loop')
        self._start_send_loop()

        while self._ws.run_forever():
            logging.warning(
                f"connection dropped. trying to reconnect in {self.RECONNECT_DELAY} seconds..."
            )
            time.sleep(self.RECONNECT_DELAY)

    def send_whisper(self, user, message):
        if not self.message_is_valid(message):
            raise InvalidMessageError(message)

        if not self._auth_token and not self._session_id:
            raise AnonymousConnectionError('unable to send whispers')

        if self._profile and self._profile.nick == user:
            raise ValueError("you can't whisper yourself, you silly goose")

        enabled = str(getenv('DGG_ENABLE_WHISPERS')).lower()
        if not enabled or enabled in ('none', 'false') or user not in self._users_available_to_whisper:
            raise DumbFucksBeware('cannot send whispers')

        logging.info(f"queue send whisper to {user}: `{message}`")
        self._queue_message(EventTypes.WHISPER, nick=user, data=message)

    def _on(self, event, f):
        return self._handler.on(event, f)

    def on_served_connections(self, f):
        """
        Called when receiving the first message when a new connection is established,
        which lists all users connected and amount of connections currently served.
        """

        return self._on(EventTypes.SERVED_CONNECTIONS, f)

    def on_user_joined(self, f):
        return self._on(EventTypes.USER_JOINED, f)

    def on_user_quit(self, f):
        return self._on(EventTypes.USER_QUIT, f)

    def on_broadcast(self, f):
        """
        Called when receiving broadcasts (the yellow messages),
        such as when a user subscribes.
        """

        return self._on(EventTypes.BROADCAST, f)

    def on_chat_message(self, f):
        return self._on(EventTypes.CHAT_MESSAGE, f)

    def on_mention(self, f):
        """
        Called when a chat message contains the current user's name.
        It's not called by the handler, but by the `DGGChat` instance,
        so it doesn't need to be mapped. `on_chat_message()` is still called.
        """

        return self._on(EventTypes.Special.MENTION, f)

    def on_whisper(self, f):
        return self._on(EventTypes.WHISPER, f)

    def on_whisper_sent(self, f):
        """Called on confirmation messages that a whisper was successfully sent."""

        return self._on(EventTypes.WHISPER_SENT, f)

    def on_mute(self, f):
        return self._on(EventTypes.MUTE, f)

    def on_unmute(self, f):
        return self._on(EventTypes.UNMUTE, f)

    def on_ban(self, f):
        return self._on(EventTypes.BAN, f)

    def on_unban(self, f):
        return self._on(EventTypes.UNBAN, f)

    def on_sub_only(self, f):
        return self._on(EventTypes.SUB_ONLY, f)

    def on_error_message(self, f):
        """
        Called on an error message when something goes wrong, 
        such as when sending a whisper to a user that doesn't exist.
        """

        return self._on(EventTypes.ERROR_MESSAGE, f)

    def on_ws_error(self, f):
        """
        Called when something goes wrong with the websocket connection.
        It's not called by the handler, but by the `DGGChat` instance,
        so it doesn't need to be mapped.
        """

        return self._on(EventTypes.Special.WS_ERROR, f)

    def on_ws_close(self, f):
        """
        Called when the websocket connection is closed.
        It's not called by the handler, but by the `DGGChat` instance,
        so it doesn't need to be mapped.
        """

        return self._on(EventTypes.Special.WS_CLOSE, f)

    def on_handler_error(self, f):
        """
        Called when something goes wrong in any of the handlers called.
        """

        return self._on(EventTypes.Special.HANDLER_ERROR, f)

    def before_every_message(self, f):
        return self._on(EventTypes.Special.BEFORE_EVERY_MESSAGE, f)

    def after_every_message(self, f):
        return self._on(EventTypes.Special.AFTER_EVERY_MESSAGE, f)
