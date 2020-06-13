import time
from os import getenv
from dotenv import load_dotenv
from random import choice
from traceback import format_exc

from dgg_chat import DGGChat
from dgg_chat.messages import (
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
from dgg_chat.logger import setup_logger, DEBUG


def on_any_message(c: DGGChat, msg: Message):
    # overriding the internal handler will make it so
    # each message type has to be handled manually
    if msg.type == MessageTypes.BROADCAST:
        print(f"received a broadcast: `{msg.content}`")
    if msg.type == MessageTypes.ERROR:
        print(f"received an error: `{msg.payload}`")
    if msg.type == MessageTypes.WHISPER:
        print(f"received whisper: `{msg}`")
    ...

def on_served_connections(c: DGGChat, msg: ServedConnections):
    print(f"There are {msg.count} connections and {len(msg.users)} users online.")

def on_user_joined(c: DGGChat, msg: UserJoined):
    print(f"User {msg.user.nick} just joined!")

def on_user_quit(c: DGGChat, msg: UserQuit):
    print(f"User {msg.user.nick} just left!")

def on_broadcast(c: DGGChat, msg):
    print(f"Something interesting just happened: {msg.content}")

def on_chat_message(c: DGGChat, msg):
    print(f"{msg.user.nick} just said: {msg.content}")

def on_whisper(c: DGGChat, msg):
    print(f"Just received a message from {msg.user.nick}: {msg.content}")
    c.send_whisper(msg.user.nick, 'Hello!')

def on_whisper_sent(c: DGGChat):
    print(f"Last whisper got sent successfully!")

def on_mute(c: DGGChat, msg: ModerationMessage):
    sentence = msg.sentence or '10m'  # default mute is 10m
    print(f"{msg.affected_user} just got muted by {msg.moderator.nick} for {sentence}.")

def on_unmute(c: DGGChat, msg: ModerationMessage):
    print(f"{msg.affected_user} just got unmuted by {msg.moderator.nick}!")

def on_ban(c: DGGChat, msg: ModerationMessage):
    if msg.sentence:
        print(f"{msg.affected_user} just got banned permanently by {msg.moderator.nick}!")
        c.send_chat_message('{msg.affected_user} DuckerZ')
    else:
        print(f"{msg.affected_user} just got banned by {msg.moderator.nick} for {msg.sentence}!")

def on_unban(c: DGGChat, msg: ModerationMessage):
    print(f"{msg.affected_user} just got unbanned by {msg.moderator.nick}!")
    c.send_chat_message('{msg.affected_user} AngelThump')

def on_sub_only(c: DGGChat, msg: SubOnly):
    print(f"Sub only mode just toggled {msg.mode}")
    if msg.mode == 'on':
        c.send_chat_message('white names DuckerZ')
    if msg.mode == 'off':
        c.send_chat_message('AngelThump')

def on_error_message(c: DGGChat, msg: Message):
    print(f"something went trying to reach the chat: `{msg.payload}`")


setup_logger(DEBUG)

load_dotenv(verbose=True)
dgg_auth_token = getenv('DGG_AUTH_TOKEN')

chat = DGGChat(
    auth_token=dgg_auth_token,
    # on_any_message=on_any_message,
    on_served_connections=on_served_connections,
    on_user_joined=on_user_joined,
    on_user_quit=on_user_quit,
    on_broadcast=on_broadcast,
    on_chat_message=on_chat_message,
    on_whisper=on_whisper,
    on_whisper_sent=on_whisper_sent,
    on_mute=on_mute,
    on_unmute=on_unmute,
    on_ban=on_ban,
    on_unban=on_unban,
    on_sub_only=on_sub_only,
    on_error_message=on_error_message,
)
try:
    chat.run_forever()
except Exception as e:
    format_exc()
    raise e
    

## in case you need to do other stuff, 
## the chat handler can be run in the background like this:

# chat = DGGChat(auth_token=dgg_auth_token, ...)
# chat.connect()
# ... do stuff
# chat.disconnect()

## or this:

# with DGGChat(auth_token=dgg_auth_token, ...) as chat:
#     ... do stuff
