from ._messages import MessageTypes
from ._utils import bind_method


class DGGChatWSHandler:
    def __init__(
        self, on_any_message=None,
        on_served_connections=None, on_user_joined=None, on_user_quit=None,
        on_broadcast=None, on_chat_message=None, on_whisper=None, on_whisper_sent=None,
        on_mute=None, on_unmute=None, on_ban=None, on_unban=None,
        on_sub_only=None, on_error_message=None
    ):
        if on_any_message:
            self.on_any_message = bind_method(on_any_message, self)
        if on_served_connections:
            self.on_served_connections = bind_method(on_served_connections, self)
        if on_user_joined:
            self.on_user_joined = bind_method(on_user_joined, self)
        if on_user_quit:
            self.on_user_quit = bind_method(on_user_quit, self)
        if on_broadcast:
            self.on_broadcast = bind_method(on_broadcast, self)
        if on_chat_message:
            self.on_chat_message = bind_method(on_chat_message, self)
        if on_whisper:
            self.on_whisper = bind_method(on_whisper, self)
        if on_whisper_sent:
            self.on_whisper_sent = bind_method(on_whisper_sent, self)
        if on_mute:
            self.on_mute = bind_method(on_mute, self)
        if on_unmute:
            self.on_unmute = bind_method(on_unmute, self)
        if on_ban:
            self.on_ban = bind_method(on_ban, self)
        if on_unban:
            self.on_unban = bind_method(on_unban, self)
        if on_sub_only:
            self.on_sub_only = bind_method(on_sub_only, self)
        if on_error_message:
            self.on_error_message = bind_method(on_error_message, self)

    def on_any_message(self, ws, message):
        handler_mapping = {
            MessageTypes.SERVED_CONNECTIONS: self.on_served_connections,
            MessageTypes.USER_JOINED: self.on_user_joined,
            MessageTypes.USER_QUIT: self.on_user_quit,
            MessageTypes.BROADCAST: self.on_broadcast,
            MessageTypes.CHAT_MESSAGE: self.on_chat_message,
            MessageTypes.WHISPER: self.on_whisper,
            MessageTypes.WHISPER_SENT: self.on_whisper_sent,
            MessageTypes.MUTE: self.on_mute,
            MessageTypes.UNMUTE: self.on_unmute,
            MessageTypes.BAN: self.on_ban,
            MessageTypes.UNBAN: self.on_unban,
            MessageTypes.SUB_ONLY: self.on_sub_only,
            MessageTypes.ERROR: self.on_error_message,
        }
        if message.type in handler_mapping:
            return handler_mapping[message.type](ws, message)
        print(f"message type `{message.type}` not handled: {message}")

    def on_served_connections(self, ws, message):
        pass

    def on_user_joined(self, ws, message):
        pass

    def on_user_quit(self, ws, message):
        pass

    def on_broadcast(self, ws, message):
        pass

    def on_chat_message(self, ws, message):
        pass

    def on_whisper(self, ws, message):
        pass

    def on_whisper_sent(self, ws, message):
        pass

    def on_mute(self, ws, message):
        pass

    def on_unmute(self, ws, message):
        pass

    def on_ban(self, ws, message):
        pass

    def on_unban(self, ws, message):
        pass

    def on_sub_only(self, ws, message):
        pass
    
    def on_error_message(self, ws, message):
        print('*'*10)
        print(message)
        print('*'*10)
