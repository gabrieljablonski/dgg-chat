from os import getenv
from dotenv import load_dotenv

from dgg_chat import DGGChat
from dgg_chat.messages import (
    MessageTypes,
    Message,
    ServedConnections,
    ChatMessage,
    Whisper,
)
from dgg_chat.handler import DGGChatHandler
from dgg_chat.logging import setup_logger, WARNING, INFO, DEBUG


class CustomHandler(DGGChatHandler):
    def on_chat_message(self, message: ChatMessage):
        print(f"{message.user.nick} just said: {message.content}")

    def on_whisper(self, whisper: Whisper):
        print(
            f"Just received a message from {whisper.user.nick}: {whisper.content}"
        )
        self.chat.send_whisper(whisper.user.nick, 'Hello!')

    def on_whisper_sent(self):
        print('whisper ok')

    def on_ws_error(self, error):
        print(f"something went wrong: {error}")

    def on_ws_close(self):
        print('connection closed')


class CustomHandlerWithCustomNames(DGGChatHandler):
    def mapping(self):
        return {
            MessageTypes.SERVED_CONNECTIONS: self.on_served_connections,
            MessageTypes.CHAT_MESSAGE: self.on_chat,
            MessageTypes.WHISPER: self.on_private,
            MessageTypes.WHISPER_SENT: self.on_private_sent,
            MessageTypes.Special.ON_ANY_MESSAGE: self.on_all_messages,
        }

    def on_all_messages(self, message: Message):
        print(f"from `on_all_messages()`: {message}")

    def on_served_connections(self, connections: ServedConnections):
        print(
            f"There are {connections.count} connections and {len(connections.users)} users online."
        )

    def on_chat(self, message: ChatMessage):
        print(f"{message.user.nick} just said: {message.content}")

    def on_private(self, whisper: Whisper):
        print(
            f"Just received a message from {whisper.user.nick}: {whisper.content}"
        )
        self.chat.send_whisper(whisper.user.nick, 'Hello!')

    def on_private_sent(self):
        print('whisper ok')

    # does not need to be mapped!
    def on_ws_error(self, error):
        print(f"something went wrong: {error}")

    # does not need to be mapped!
    def on_ws_close(self):
        print('connection closed')


setup_logger(INFO)

load_dotenv(verbose=True)
dgg_auth_token = getenv('DGG_AUTH_TOKEN')

handler = CustomHandler()
# handler = CustomHandlerWithCustomNames()
chat = DGGChat(
    auth_token=dgg_auth_token,
    handler=handler,
)

# default way of running (blocking)

chat.run_forever()

# can also be run in parallel (non-blocking)

# chat.connect()
# do_stuff()
# ...
# chat.disconnect()
