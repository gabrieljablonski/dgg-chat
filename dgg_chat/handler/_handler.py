import logging

from ..messages import (
    MessageTypes,
    Message,
    ServedConnections,
    UserJoined,
    UserQuit,
    Broadcast,
    ChatMessage,
    Whisper,
    ModerationMessage,
    SubOnly
)


class DGGChatHandler:
    def __init__(self, chat=None):
        self.chat = chat
        self.backup_handler = None

    @property
    def mapping(self):
        """
        Should be overridden if your custom handler implements any method
        with a different method from the ones listed below.
        
        Handlers not implemented don't need to be mapped.
        """

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

    def _try_call_handler(self, message):
        if message.type not in self.mapping:
            logging.debug(f"message type `{message.type}` not supported by `{type(self).__name__}`")
            return
        handler_name = self.mapping[message.type]
        handler = getattr(self, handler_name)
        if message.type == MessageTypes.WHISPER_SENT:
            # whisper sent is the only handler that doesn't have a message (i.e. arity 1)
            return handler()
        else:
            handler(message)

    def handle_message(self, message: Message):
        self.on_any_message(message)

        handled_message_types = set(self.mapping.keys())
        if self.backup_handler:
            handled_message_types.update(self.backup_handler.mapping)

        if message.type not in handled_message_types:
            logging.warning(f"message type `{message.type}` not handled: `{message}`")
            logging.debug(f"handled message types: {handled_message_types}")
            return

        try:
            self._try_call_handler(message)
        except AttributeError:
            if self.backup_handler:
                self.backup_handler._try_call_handler(message)

    def on_any_message(self, message: Message):
        """Called when receiving any message. Specific handler still called as usual."""
        pass
        
    def on_served_connections(self, message: ServedConnections):
        """
        Called when receiving the first message when a new connection is established,
        which lists all users connected and amount of connections currently served.
        """
        pass

    def on_user_joined(self, message: UserJoined):
        pass

    def on_user_quit(self, message: UserQuit):
        pass

    def on_broadcast(self, message: Broadcast):
        """
        Called when receiving broadcasts (the yellow messages),
        such as when a user subscribes.
        """
        pass

    def on_chat_message(self, message: ChatMessage):
        pass

    def on_mention(self, message: ChatMessage):
        """
        Called when a chat message contains the current user's name.
        It's not called by the handler, but by the `DGGChat` instance,
        so it doesn't need to be mapped. `on_chat_message` is still called.
        """
        pass

    def on_whisper(self, message: Whisper):
        pass

    def on_whisper_sent(self):
        """Called on confirmation messages that a whisper was successfully sent."""
        pass

    def on_mute(self, message: ModerationMessage):
        pass

    def on_unmute(self, message: ModerationMessage):
        pass

    def on_ban(self, message: ModerationMessage):
        pass

    def on_unban(self, message: ModerationMessage):
        pass

    def on_sub_only(self, message: SubOnly):
        pass
    
    def on_error_message(self, message: Message):
        """
        Called on an error message when something goes wrong, 
        such as when sending a whisper to a user that doesn't exist.
        """
        pass

    def on_ws_error(self, error):
        """
        Called when something goes wrong with the websocket connection.
        It's not called by the handler, but by the `DGGChat` instance,
        so it doesn't need to be mapped.
        """
        pass


    def on_ws_close(self):
        """
        Called when the websocket connection is closed.
        It's not called by the handler, but by the `DGGChat` instance,
        so it doesn't need to be mapped.
        """
        pass
