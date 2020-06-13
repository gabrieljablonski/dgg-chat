import time
import logging
from queue import Queue
from sched import scheduler
from threading import Thread
from websocket import WebSocketApp

from ._messages import Message, MessageTypes
from ._utils import format_payload, bind_method
from ._handler import DGGChatWSHandler
from ._logger import setup_logger


class AnonymousConnectionError(Exception):
    pass


class DGGChat:
    DGG_WS = 'wss://destiny.gg/ws'
    WAIT_BOOTSTRAP = 1  # in seconds
    PRINT_MAX_LENGTH = 300
    THROTTLE_DELAY = 2 # in seconds

    def __init__(
        self, auth_token=None, print_messages=False, on_close=None,
        on_any_message=None, on_served_connections=None, 
        on_user_joined=None, on_user_quit=None,
        on_broadcast=None, on_chat_message=None, 
        on_whisper=None, on_whisper_sent=None,
        on_mute=None, on_unmute=None, 
        on_ban=None, on_unban=None,
        on_sub_only=None, on_error_message=None,
    ):
        self.print_messages = print_messages

        self._auth_token = auth_token
        self._running = False
        self._handler = DGGChatWSHandler(
            on_any_message, on_served_connections, 
            on_user_joined, on_user_quit,
            on_broadcast, on_chat_message, 
            on_whisper, on_whisper_sent,
            on_mute, on_unban, on_ban, on_unban,
            on_sub_only, on_error_message
        )

        self._queued_messages = Queue()
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

            self._handler.on_any_message(ws, parsed)

        # websocket related errors (`on_error_message` is business related, i.e. `ERR` messages)
        def _on_error(ws, error):
            msg = f"websocket error: `{error}`"
            logging.error(msg)
            print(msg)

        def _on_close(ws):
            logging.info('closing connection')
            print('### connection closed ###')

        on_close = on_close or _on_close

        self._ws = WebSocketApp(
            self.DGG_WS,
            on_message=_on_message,
            on_error=_on_error,
            on_close=on_close,
            cookie=f"authtoken={self._auth_token}" if self._auth_token else None
        )
        
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
        last_sent = time.time()
        while True:
            while time.time() < last_sent + self.THROTTLE_DELAY:
                continue
            last_sent = time.time()
            payload = self._queued_messages.get()
            logging.debug(f"sending payload: `{payload}`")
            self._ws.send(payload)

    def _enqueue_message(self, type, **kwargs):
        payload = format_payload(type, **kwargs)
        logging.debug(f"enqueueing payload: `{payload}`")
        self._queued_messages.put(payload)

    def send_chat_message(self, message):
        if not self._auth_token:
            logging.fatal("can't send chat message: anonymous connection")
            raise AnonymousConnectionError('`auth_token` must be informed to send chat messages')
        self._enqueue_message(MessageTypes.CHAT_MESSAGE, data=message)

    def send_whisper(self, user, message):
        if not self._auth_token:
            logging.fatal("can't send whisper: anonymous connection")
            raise AnonymousConnectionError('`auth_token` must be informed to send whispers')
        self._enqueue_message(MessageTypes.WHISPER, nick=user, data=message)
