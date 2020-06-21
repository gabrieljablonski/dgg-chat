# DGG Chat

A package that lets you do stuff in [dgg](https://destiny.gg) chat, like parsing messages in chat,
replying to whispers, accessing the dgg API, and retrieving user logs and CDN assets.

If you're interested in making a chat bot, check the [`dgg-chat-bot`](https://github.com/gabrieljablonski/dgg-chat-bot) package.

## Installing

This package is available via pip (requires python 3.8).

```sh
pip install dgg-chat
```

A (very) minimal working example (more details below):

```python
from dgg_chat import DGGChat

chat = DGGChat()

@chat.on_chat_message
def on_chat_message(message):
    print(message)

chat.run_forever()
```

## How It Works

The package makes use of messages sent via the dgg websocket interface.
It's based around the `DGGChat` class, which runs the main event loop, 
invoking the handlers implemented, as well as allowing you to reply to whispers.

When a message is received from the websocket, it is redirected to its respective handler 
(and any other relevant [special handler](#special-events)).

## How To Use

A handler is a method that receives one argument (with three exceptions), which will 
be of type `dgg_chat.messages.Message` or one of its subclasses. 

The three exceptions are: the handlers for the `WHISPER_SENT` and the `WS_CLOSE` events, which have no arguments;
and the `HANDLER_ERROR` event, which receive the exceptions raised on trying to handle the message.

Each handler receives a specific type of message, defined in the [`messages`](./dgg_chat/messages/_messages.py) module.
To register an event handler, you must use one of the decorators listed in the 
[Event Types and Their Respective Handlers](#event-types-and-their-respective-handlers) section.

All handlers are also synchronous, that is, a handler will only be called after the previous one
finished its work. Asynchronous support might be implemented in the future.

A simple example can be found under the [`DGGChat`](#dggchat) section. More details can be found in the [`example.py`](./example.py) file.

### Event Types and Their Respective Handlers

| Decorator                 | Event Description                                                                                                             |
|:-------------------------:|:-----------------------------------------------------------------------------------------------------------------------------:|
| `on_served_connections`   | The chat connection was established. Lists all connected users and the count of served connections.                           |
| `on_user_joined`          | A user has joined the chat.                                                                                                   |
| `on_user_quit`            | A user has left the chat.                                                                                                     |
| `on_broadcast`            | A broadcast message (yellow message) was received, such as when a user subscribes.                                            |
| `on_chat_message`         | A chat message was received.                                                                                                  |
| `on_whisper`              | A whisper was received.                                                                                                       |
| `on_whisper_sent`         | The whisper was successfully sent.                                                                                            |
| `on_mute`                 | A user was muted.                                                                                                             |
| `on_unmute`               | A user was unmuted.                                                                                                           |
| `on_ban`                  | A user was banned.                                                                                                            |
| `on_unban`                | A user was unbanned.                                                                                                          |
| `on_sub_only`             | Submode was toggled in chat.                                                                                                  |
| `on_error_message`        | A chat related error occurred (see [common errors](#common-error_message-causes)).                                            |

#### Special Events

Besides the already listed events, some others are triggered on special situations.
Those are as follow:

| Decorator              | Associated Event                                                                                                                                                        |
|:----------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| `before_every_message` | Before every event listed in the previous table. The specific handlers for that event type will still be called.                                                        |
| `after_every_message`  | After every event listed in the previous table. The specific handlers for that event type will still be called.                                                         |
| `on_mention`           | Received a `ChatMessage` that contains the username for the authenticated user. Requires either `auth_token` or `session_id`. `CHAT_MESSAGE` handler is still called.   |
| `on_ws_error`          | Something wrong happened with the websocket connection.                                                                                                                 |
| `on_ws_close`          | Websocket connection got closed, usually by calling `DGGChat().disconnect()`.                                                                                           |
| `on_handler_error`     | An exception was raised inside at least one of the handlers called.                                                                                                     |

### Common `ERROR_MESSAGE` Causes

| Error Message | Explanation                                                                                                                                                            |
|:-------------:|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| `"throttled"` | Messages got sent too fast with `DGGChat().send_whisper()`.                                                                                                            |
| `"needlogin"` | Invalid `auth_token` or `session_login` provided. See [authentication](#authentication).                                                                               |
| `"notfound"`  | Usually when target user for `DGGChat().send_whisper()` was not found.                                                                                                 |

## `DGGChat`

This is the class that runs the show. It takes the handlers you've implemented and calls them when appropriate.
The features listed below are also available (though some are not usable right away):

- Sending whispers with `DGGChat().send_whisper()`.
- View info for current user with `DGGChat().profile` property.
- Get unread whispers with `DGGChat().get_unread_whispers()`.

All of these features require the connection to be [authenticated](#authentication).

By default, you won't be able to send whispers. This was done intentionally and a quick look at 
the source code should lead you to how to enable sending whispers to people who whispered you first. 
Hopefully this discourages some ill-intentioned folks from using this to do dumb shit in the chat.

Here's a quick example on how to setup and run the chat instance.
More details can be found in the [`example.py`](./example.py) file.

```python
from dgg_chat import DGGChat

dgg_auth_token = "<your dgg auth token>"

chat = DGGChat(auth_token=dgg_auth_token)

@chat.on_user_joined
def on_user_joined(joined):
    print(f"{joined.user} just joined!")

@chat.on_chat_message
def on_chat_message(message):
    print(f"{message.user} just said something: {message.content}")

@chat.on_whisper
def on_whisper(whisper):
    print(f"{whisper.user} just sent you a whisper: {whisper.content}")
    chat.send_whisper(whisper.user, "Hello!")

...

# blocking call
chat.run_forever()
```

## Authentication

Although you can run the chat anonymously and still be able to view all messages in chat,
replying to whispers requires your connection to be authenticated.

### Auth Token

The easiest way to do that is to create an `auth_token` associated with your account. 
It will allow you to get your profile info, send chat messages, and whisper other users.
This can be done by going to the dgg [developer dashboard](https://www.destiny.gg/profile/developer),
clicking on `Connections`, and `Add login key`. The generated key should be a 64 character alphanumeric string.

**CAUTION**: this key acts as your password, so be careful not to share it with anyone 
(also don't put in any of your unignored repo files!). With it, someone else can use it to send 
messages as you and read your whispers. If you believe you've leaked your key somewhere, go back to the
dashboard, remove it, and generate another.

Auth tokens [usually do not expire](https://github.com/destinygg/website/blob/master/lib/Destiny/Controllers/ProfileController.php#L345).

### Session ID

If you care about getting unread whispers received when you were offline, or any whisper you've
ever received (and that wasn't deleted), you'll need a `session_id`.

This one is a bit trickier to get, and it will expire, unlike `auth_token`. First open your browser, 
navigate to [https://www.destiny.gg/bigscreen](), and login (if you're already logged in it works too).

Bring up the dev tools (usually F12), go to the `Network` tab, and refresh the page.
Find any request made on the destiny.gg domain (`bigscreen` will probably be one of the first ones).
Scroll down to the `Cookies` header. The key after `sid=` is your session id.

![session id](https://i.imgur.com/v42efey.png)

With the session key setup, you should be able to retrieve messages directly from your inbox.
Be mindful the session id expires after [5 hours without use (?)](https://github.com/destinygg/website/blob/master/public/index.php#L18), 
so if stuff stops working, check if this might be it.

## Extra Features

- Use `DGGChat().api` (or directly with `from dgg_chat.api import DGGAPI`) to access other functionalities of the dgg API.
- Use `DGGCDN()` (`from dgg_chat.cdn import DGGCDN`) to retrieve info about stuff like flairs and emotes from the CDN.
- Use `DGGLogs` (`from dgg_chat.overrustle_logs import DGGLogs`) to retrieve chat logs.
