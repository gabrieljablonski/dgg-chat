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

    def mapping(self):
        """
        Should be overridden if your custom handler implements any method
        with a different method from the ones listed below.

        Handlers not implemented don't need to be mapped.
        """

        return {
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
            MessageTypes.Special.ON_ANY_MESSAGE: self.on_any_message,
            MessageTypes.Special.ON_MENTION: self.on_mention,
            MessageTypes.Special.ON_WS_ERROR: self.on_ws_error,
            MessageTypes.Special.ON_WS_CLOSE: self.on_ws_close,
        }

    def _try_call_handler(self, message_type, *args):
        if message_type not in self.mapping():
            msg = f"message type `{message_type}` not supported by `{type(self).__name__}`"
            logging.debug(msg)
            return
        handler = self.mapping()[message_type]
        handler(*args)

    def handle_special(self, message_type, *args):
        self._try_call_handler(message_type, *args)

    def handle_message(self, message: Message):
        self.handle_special(MessageTypes.Special.ON_ANY_MESSAGE, message)

        handled_message_types = set(self.mapping().keys())
        if self.backup_handler:
            handled_message_types.update(self.backup_handler.mapping())

        if message.type not in handled_message_types:
            msg = f"message type `{message.type}` not handled: `{message}`"
            logging.warning(msg)
            logging.debug(f"handled message types: {handled_message_types}")
            return

        try:
            self._try_call_handler(message)
        except KeyError:
            if self.backup_handler:
                self.backup_handler._try_call_handler(message)

    def on_any_message(self, message: Message):
        """Called when receiving any message. Specific handler still called as usual."""
        pass

    def on_served_connections(self, connections: ServedConnections):
        """
        Called when receiving the first message when a new connection is established,
        which lists all users connected and amount of connections currently served.
        """
        pass

    def on_user_joined(self, joined: UserJoined):
        pass

    def on_user_quit(self, quit: UserQuit):
        pass

    def on_broadcast(self, broadcast: Broadcast):
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

    def on_whisper(self, whisper: Whisper):
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
