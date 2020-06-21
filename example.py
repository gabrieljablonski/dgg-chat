from os import getenv
from dotenv import load_dotenv

from dgg_chat import DGGChat
from dgg_chat.messages import (
    EventTypes,
    Message,
    ServedConnections,
)
from dgg_chat.logging import setup_logger, WARNING, INFO, DEBUG


# uses the `logging` module
# alternatively it can be setup manually
setup_logger(INFO)

# python-dotenv is recommended for storing the auth token, although not required
load_dotenv(verbose=True)
dgg_auth_token = getenv('DGG_AUTH_TOKEN')

chat = DGGChat(auth_token=dgg_auth_token)


@chat.before_every_message
def before_every_message(message: Message):
    print(f"from `before_every_message()`: {message}")


# multiple handlers can be used for the same event
@chat.before_every_message
def alt_before_every_message(message: Message):
    ...


@chat.on_served_connections
def on_served_connections(connections: ServedConnections):
    print(
        f"There are {connections.count} connections and {len(connections.users)} users online."
    )


# the same handler can be used for multiple events
@chat.on_whisper
@chat.on_chat_message
def on_chat_or_whisper(message: Message):
    if message.event == EventTypes.CHAT_MESSAGE:
        print(f"{message.user.nick} just said: {message.content}")
    if message.event == EventTypes.WHISPER:
        print(
            f"Just received a message from {message.user.nick}: {message.content}"
        )
        chat.send_whisper(message.user.nick, 'Hello!')


@chat.on_whisper_sent
def on_whisper_sent():
    print('whisper ok')


@chat.on_ws_error
@chat.on_error_message
def on_ws_error(error):
    print(f"something went wrong: `{error}`")


@chat.on_ws_close
def on_ws_close():
    print('connection closed')


@chat.on_handler_error
def on_handler_error(exceptions):
    for e in exceptions:
        print(e)


# default way of running (blocking)
chat.run_forever()

# can also be run in parallel (non-blocking)
# chat.connect()
# do_stuff()
# ...
# chat.disconnect()
