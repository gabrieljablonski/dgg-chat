from time import sleep
from threading import Thread
from websocket import WebSocketApp

from ._messages import Message, MessageTypes
from ._utils import format_payload, bind_method
from ._handler import DGGChatWSHandler


class AnonymousConnectionError(Exception):
    pass


class DGGChat:
    DGG_WS = 'wss://destiny.gg/ws'
    WAIT_BOOTSTRAP = 1  # in seconds
    PRINT_MAX_LENGTH = 200

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

        def _on_message(ws, msg):
            message = Message.parse(msg)
            if self.print_messages:
                _msg = str(msg)
                print(_msg[:self.PRINT_MAX_LENGTH], end='...\n' if len(str(_msg)) > self.PRINT_MAX_LENGTH else '\n')
            self._handler.on_any_message(ws, message)

        # websocket related errors (`on_error_message` is business related, i.e. `ERR` messages)
        def _on_error(ws, error):
            print(f"error: {error}")

        def _on_close(ws):
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
        t = Thread(target=self._ws.run_forever, args=args, kwargs=kwargs)
        t.start()
        sleep(self.WAIT_BOOTSTRAP)
        self._running = True
        return t

    def disconnect(self):
        self._ws.close()
        self._running = False

    def run_forever(self, *args, **kwargs):
        if self._running:
            raise ConnectionError('chat already connected, call `disconnect()` first')
        self._ws.run_forever(*args, **kwargs)

    def _send(self, type, **kwargs):
        payload = format_payload(type, **kwargs)
        self._ws.send(payload)

    def send_chat_message(self, message):
        if not self._auth_token:
            raise AnonymousConnectionError('`auth_token` must be informed to send chat messages')
        self._send(MessageTypes.CHAT_MESSAGE, data=message)

    def send_whisper(self, user, message):
        if not self._auth_token:
            raise AnonymousConnectionError('`auth_token` must be informed to send whispers')
        self._send(MessageTypes.WHISPER, nick=user, data=message)
