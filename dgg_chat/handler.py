import logging

from .messages import (
    MessageTypes,
    Message,
    User,
    ServedConnections,
    UserJoined,
    UserQuit,
    Broadcast,
    ChatMessage,
    Whisper,
    ModerationMessage,
    SubOnly
)
from ._utils import bind_method


class DGGChatHandler:
    def __init__(
        self, 
        *,
        on_any_message=None, on_served_connections=None, 
        on_user_joined=None, on_user_quit=None,
        on_broadcast=None, on_chat_message=None, 
        on_whisper=None, on_whisper_sent=None,
        on_mute=None, on_unmute=None, 
        on_ban=None, on_unban=None,
        on_sub_only=None, on_error_message=None
    ):
        self.backup_handler = None
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

    @property
    def mapping(self):
        return {
            MessageTypes.SERVED_CONNECTIONS: 'on_served_connections',
            MessageTypes.USER_JOINED: 'on_user_joined',
            MessageTypes.USER_QUIT: 'on_user_quit',
            MessageTypes.BROADCAST: 'on_broadcast',
            MessageTypes.CHAT_MESSAGE: 'on_chat_message',
            MessageTypes.WHISPER: 'on_whisper',
            MessageTypes.WHISPER_SENT: 'on_whisper_sent',
            MessageTypes.MUTE: 'on_mute',
            MessageTypes.UNMUTE: 'on_unmute',
            MessageTypes.BAN: 'on_ban',
            MessageTypes.UNBAN: 'on_unban',
            MessageTypes.SUB_ONLY: 'on_sub_only',
            MessageTypes.ERROR: 'on_error_message',
        }

    def _try_call_handler(self, chat, message):
        handler_name = self.mapping[message.type]
        handler = getattr(self, handler_name)
        if message.type == MessageTypes.WHISPER_SENT:
            # whisper sent is the only handler that doesn't have a message (i.e. arity 1)
            return handler(chat)
        else:
            handler(chat, message)

    def handle_message(self, chat, message):
        self.on_any_message(chat, message)

        handled_message_types = set(self.mapping.keys())
        if self.backup_handler:
            handled_message_types.update(self.backup_handler.mapping)

        if message.type not in handled_message_types:
            logging.warning(f"message type `{message.type}` not handled: `{message}`")
            logging.debug(f"handled message types: {handled_message_types}")
            return

        try:
            self._try_call_handler(chat, message)
        except AttributeError:
            if self.backup_handler:
                self.backup_handler._try_call_handler(chat, message)

    def on_any_message(self, chat, message: Message):
        """Called when receiving any message. Specific handler still called as usual."""
        pass
        
    def on_served_connections(self, chat, message: ServedConnections):
        """
        Called when receiving the first message when a new connection is established,
        which lists all users connected and amount of connections currently served.
        """
        pass

    def on_user_joined(self, chat, message: UserJoined):
        pass

    def on_user_quit(self, chat, message: UserQuit):
        pass

    def on_broadcast(self, chat, message: Broadcast):
        """
        Called when receiving broadcasts (the yellow messages),
        such as when a user subscribes.
        """
        pass

    def on_chat_message(self, chat, message: ChatMessage):
        pass

    def on_whisper(self, chat, message: Whisper):
        pass

    def on_whisper_sent(self, chat):
        """Called on confirmation messages that a whisper was successfully sent."""
        pass

    def on_mute(self, chat, message: ModerationMessage):
        pass

    def on_unmute(self, chat, message: ModerationMessage):
        pass

    def on_ban(self, chat, message: ModerationMessage):
        pass

    def on_unban(self, chat, message: ModerationMessage):
        pass

    def on_sub_only(self, chat, message: SubOnly):
        pass
    
    def on_error_message(self, chat, message: Message):
        """
        Called on an error message when something goes wrong, 
        such as when sending a whisper to a user that doesn't exist.
        """
        pass
