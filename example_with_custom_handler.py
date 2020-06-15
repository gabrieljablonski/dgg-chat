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
from dgg_chat.logger import setup_logger, WARNING, DEBUG


class CustomHandler(DGGChatHandler):
    def on_chat_message(self, chat: DGGChat, message: ChatMessage):
        print(f"{message.user.nick} just said: {message.content}")

    def on_whisper(self, chat: DGGChat, message: Whisper):
        print(f"Just received a message from {message.user.nick}: {message.content}")
        chat.send_whisper(message.user.nick, 'Hello!')

    def on_whisper_sent(self, chat: DGGChat):
        print('whisper ok')


class CustomHandlerWithCustomNames(DGGChatHandler):
    @property
    def mapping(self):
        return {
            MessageTypes.SERVED_CONNECTIONS: 'on_served_connections',
            MessageTypes.CHAT_MESSAGE: 'on_chat',
            MessageTypes.WHISPER: 'on_private',
            MessageTypes.WHISPER_SENT: 'on_private_sent',
        }

    def on_served_connections(self, chat: DGGChat, message: ServedConnections):
        print(f"There are {message.count} connections and {len(message.users)} users online.")

    def on_chat(self, chat: DGGChat, message: ChatMessage):
        print(f"{message.user.nick} just said: {message.content}")

    def on_private(self, chat: DGGChat, message: Whisper):
        print(f"Just received a message from {message.user.nick}: {message.content}")
        chat.send_whisper(message.user.nick, 'Hello!')

    def on_private_sent(self, chat: DGGChat):
        print('whisper ok')


setup_logger(WARNING)

load_dotenv(verbose=True)
dgg_auth_token = getenv('DGG_AUTH_TOKEN')

handler = CustomHandler()
# handler = CustomHandlerWithCustomNames()
chat = DGGChat(
    auth_token=dgg_auth_token,
    handler=handler
)

while chat.run_forever(): 
    pass
