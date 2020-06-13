import time
import logging
import queue
from queue import Queue
from sched import scheduler
from threading import Thread
from websocket import WebSocketApp
from websocket._exceptions import WebSocketException

from .messages import Message, MessageTypes
from ._utils import format_payload, bind_method
from ._handler import DGGChatHandler


class AnonymousConnectionError(Exception):
    pass


class DGGChat:
    DGG_WS = 'wss://destiny.gg/ws'
    WAIT_BOOTSTRAP = 1  # in seconds
    PRINT_MAX_LENGTH = 300
    # considering server throttle is 300ms and some network overhead
    THROTTLE_DELAY = .200  # in seconds
    # after this much time after last sent message, throttle factor is reset
    THROTTLE_RESET = 600  # in seconds
    # throttling should be a very exceptional case, so instead of starting at 1,
    # adding a bit of padding to make sure it doesn't happen multiple times in a row
    BASE_THROTTLE_FACTOR = 1.1

    def __init__(
        self, auth_token=None, print_messages=False, 
        try_resend_on_throttle=True, on_close=None,
        on_any_message=None, on_served_connections=None, 
        on_user_joined=None, on_user_quit=None,
        on_broadcast=None, on_chat_message=None, 
        on_whisper=None, on_whisper_sent=None,
        on_mute=None, on_unmute=None, 
        on_ban=None, on_unban=None,
        on_sub_only=None, on_error_message=None,
    ):
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

        self.print_messages = print_messages
        self.try_resend_on_throttle = try_resend_on_throttle
        
        self._running = False
        self._auth_token = auth_token

        self._last_message_time = 0
        self._next_message_time = time.time()
        self._throttle_factor = self.BASE_THROTTLE_FACTOR

        self._queued_messages = Queue()
        self._unhandled_messages = Queue(maxsize=1)
        Thread(target=self._send_loop, daemon=True).start()

        def _on_message(ws, message):
            parsed = Message.parse(message)
            logging.debug(f"received message: `{message}`")
            logging.debug(f"parsed message: `{parsed}`")
            if self.print_messages:
                _msg = parsed.json
                print('-'*30)
                print('Received message:')
                print(_msg[:self.PRINT_MAX_LENGTH])
                print('...' if len(str(_msg)) > self.PRINT_MAX_LENGTH else '')
                print('-'*30)
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

            self._handler.on_any_message(self, parsed)

        # websocket related errors (`on_error_message` is business related, i.e. `ERR` messages)
        def _on_error(ws, error):
            msg = f"websocket error: `{error}`"
            logging.error(msg)
            raise WebSocketException(msg)

        def _on_close(ws):
            logging.info('closing connection')
            print('### connection closed ###')

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

    def _enqueue_message(self, type, **kwargs):
        payload = format_payload(type, **kwargs)
        logging.debug(f"enqueueing payload: `{payload}`")
        self._queued_messages.put(payload)

    def send_chat_message(self, message):
        if not self._auth_token:
            logging.fatal("can't send chat message: anonymous connection")
            raise AnonymousConnectionError('`auth_token` must be informed to send chat messages')
        logging.info('sending chat message')
        self._enqueue_message(MessageTypes.CHAT_MESSAGE, data=message)

    def send_whisper(self, user, message):
        if not self._auth_token:
            logging.fatal("can't send whisper: anonymous connection")
            raise AnonymousConnectionError('`auth_token` must be informed to send whispers')
        logging.info('sending whisper')
        self._enqueue_message(MessageTypes.WHISPER, nick=user, data=message)
