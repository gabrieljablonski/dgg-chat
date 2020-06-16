# DGG Chat API

An API that lets you do stuff in [dgg](https://destiny.gg) chat, like parsing and sending messages in chat.

## How It Works

The API is based on messages emitted from dgg's websocket interface.
It consists of two main classes: 

- `DGGChatHandler`: the class used to implement the custom handlers for the different message types.
- `DGGChat`: the class that will run the main event loop, invoking the handlers in a
`DGGChatHandler` instance, as well as allowing you to send whispers and messages in chat.

When a message is received from the websocket, it is redirected to its respective handler 
(and any relevant [special handlers](#special-handlers)). The handler class has access to 
the chat class, so messages can be sent as a response to an event, for example.

## `DGGChatHandler`

To implement a custom handler, you must define a new class that inherits from `DGGChatHandler`.
Aside from [four special exceptions](#special-handlers) (and the `on_whisper_sent()`, which has no arguments), 
the custom handler will be a method with one argument (besides `self`), which is the websocket message received. 
Each handler receives a specific type of message. 

All defined message classes can be viewed in the [`messages`](./dgg_chat/messages/_messages.py) 
module. The message type each handler should expect is defined by the 
[`DGGChatHandler().mapping()`](./dgg_chat/handler/_handler.py#L30) method.

Overriding one of the predefined methods will effectively implement a custom handler. The chat 
instance can be accessed via the `self.chat` attribute. A simple custom handler example follows:

```python
    from dgg_chat.handler import DGGChatHandler

    def CustomHandler(DGGChatHandler):
        def on_user_joined(self, joined):
            print(f"{joined.user} just joined!")

        def on_chat_message(self, message):
            print(f"{message.user} just said something: {message.content}")

        def on_whisper(self, whisper):
            print(f"{whisper.user} just sent you a whisper: {whisper.content}")
            self.chat.send_whisper(whisper.user, "Hello!")

        ...
```

In case you don't use the default method names as defined in the `DGGChatHandler` base class, 
the `self.mapping()` method must be overriden. Handlers not implemented don't need to be mapped, 
**but if `self.mapping()` is overriden, you MUST reference ALL custom methods implemented.**

```python
    from dgg_chat.handler import DGGChatHandler
    from dgg_chat.messages import MessageTypes

    def CustomHandler(DGGChatHandler):
        def mapping(self):
            return {
                # both are mapped
                MessageTypes.CHAT_MESSAGE: self.someone_said_something,
                MessageTypes.WHISPER: self.on_whisper,
            }

        # method name changed
        def someone_said_something(self, message):
            print(f"{message.user} just said something: {message.content}")

        # same as default
        def on_whisper(self, whisper):
            ...

```

More details can be found in the [`example.py`](./example.py) file.

### Message Types and Their Respective Handlers

| Websocket Message Code | Default Handler Name      | Associated Event                                                                                                              |
|:----------------------:|:-------------------------:|:-----------------------------------------------------------------------------------------------------------------------------:|
| `SERVED_CONNECTIONS`   | `on_served_connections()` | Usually the first message received on a new connection. Lists all connected users and presents a count of served connections. |
| `USER_JOINED`          | `on_user_joined()`        | A user has joined the chat.                                                                                                   |
| `USER_QUIT`            | `on_user_quit()`          | A user has left the chat.                                                                                                     |
| `BROADCAST`            | `on_broadcast()`          | A broadcast message (yellow message) was received, such as when a user subscribes.                                            |
| `CHAT_MESSAGE`         | `on_chat_message()`       | A chat message was received.                                                                                                  |
| `WHISPER`              | `on_whisper()`            | A whisper was received.                                                                                                       |
| `WHISPER_SENT`         | `on_whisper_sent()`       | The whisper was successfully sent.                                                                                            |
| `MUTE`                 | `on_mute()`               | A user was muted.                                                                                                             |
| `UNMUTE`               | `on_unmute()`             | A user was unmuted.                                                                                                           |
| `BAN`                  | `on_ban()`                | A user was banned.                                                                                                            |
| `UNBAN`                | `on_unban()`              | A user was unbanned.                                                                                                          |
| `SUB_ONLY`             | `on_sub_only()`           | Submode was toggled in chat.                                                                                                  |
| `ERROR`                | `on_error_message()`      | A chat related error occurred (see [common errors](#common-error-messages)).                                                  |

### Special Handlers

Different from the already listed message types, some handlers are called on special situations.
Those are as follow:

| Default Handler Name  | Associated Event                                                                                                                                                        |
|:---------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| `on_any_message()`    | Catch all handler, a message of any type just got received. The specific handler for that message type will still be called.                                            |
| `on_mention()`        | Received a `ChatMessage` that contains the username for the authenticated user. Requires either `auth_token` or `session_id`. `on_chat_message()` will still be called. |
| `on_ws_error()`       | Something wrong happened with the websocket connection.                                                                                                                 |
| `on_ws_close()`       | Websocket connection got closed, usually by calling `DGGChat().disconnect()`.                                                                                              |

These handlers can also be implemented with different names and remapped.

### Common `ERROR` Messages

| Error Message | Explanation                                                                                                                                                            |
|:-------------:|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| `"throttled"` | Messages got sent too fast with `DGGChat().send_chat_message()` or `DGGChat().send_whisper()`. See [limitations](#limitations).                                            |
| `"duplicate"` | The message just sent was identical to the last one.                                                                                                                   |
| `"needlogin"` | Invalid `auth_token` or `session_login` provided. See [authentication](#authentication)                                                                                |
| `"notfound"`  | Usually when target user for `DGGChat().send_whisper()` was not found.                                                                                                   |

## `DGGChat`

This is the class that runs the show. It will take the handler you've implemented and call its methods whenever 
appropriate. The features listed below are available through it (though some are not usable right away):

- Sending chat messages with `DGGChat().send_chat_message()`.
- Sending whispers with `DGGChat().send_whisper()`.
- View info for current user with `DGGChat().profile` property.
- Get unread whispers with `DGGChat().get_unread_whispers()`.

All of these features require the connection to be [authenticated](#authentication).

In regards to sending messages, by default you won't be able to send chat messages at all,
and whispers can only be sent to users who already whispered you since the connection was last established.
This was done intentionally and a quick look at the source code should lead you to how to enable these
features. Hopefully this discourages some ill-intentioned folks from using this to do dumb shit in the chat.

Here's a quick example on how to setup and run the chat instance.
More details can be found in the [`example.py`](./example.py) file.

```python
    from dgg_chat import DGGChat
    from dgg_chat.handler import DGGChatHandler

    class CustomHandler(DGGChatHandler):
        ...

    dgg_auth_token = "<your dgg auth token>"

    handler = CustomHandler()
    chat = DGGChat(
        auth_token=dgg_auth_token,
        handler=handler
    )

    # blocking call
    chat.run_forever()
```

## Authentication

Although you can run the chat anonymously and still be able to view all messages in chat,
the more interesting stuff - like sending messages - requires your connection to be authenticated.

### Auth Token

The easiest way to do that is to create an `auth_token` associated with your account. 
It will allow you to get your profile info, send chat messages, and whisper other users.
This can be done by going to the dgg [developer dashboard](https://www.destiny.gg/profile/developer),
clicking on `Connections`, and `Add login key`. The generated key should be a 64 character alphanumeric string.

**CAUTION**: this key acts as your password, so be careful not to share it with anyone 
(also don't put in any of your unignored repo files!). With it, someone else can use it to send 
messages as you and read your whispers. If you believe you leaked your key somewhere, go back to the
dashboard, remove it, and generate another.

Auth tokens [usually do not expire](https://github.com/destinygg/website/blob/master/lib/Destiny/Controllers/ProfileController.php#L345).

### Session ID

If you care about getting unread whispers received when you were offline, or any whisper you've
ever received (and that wasn't deleted), you'll need a `session_id`.

This one is a bit more cumbersome to get, and it will expire much more often than the `auth_token`.
First open your browser, navigate to [https://www.destiny.gg/bigscreen](), and login (if you're already logged in it works too).
Bring up the dev tools (usually F12), go to the `Network` tab, and refresh the page.
Find any request made on the destiny.gg domain (`bigscreen` will probably be one of the first ones).
Scroll down to the `Cookies` header. The key after `sid=` is your session id.

![session id](https://i.imgur.com/v42efey.png)

With the session key setup, you should be able to retrieve messages directly from your inbox.
Be mindful the session id expires after [5 hours(?) without use](https://github.com/destinygg/website/blob/master/public/index.php#L18), 
so if stuff stops working, check if this might be it.

Hopefully soon the session id method will be unnecessary and the `auth_token` will be enough
to do everything, but the API has been giving me some trouble.

## Extra Features

- Use `DGGChat().api.info_stream()` (or `from dgg_chat.api import DGGAPI`) to retrieve information about the stream if it's currently live,
or from the last stream.
- Use `DGGCDN()` (`from dgg_chat.cdn import DGGCDN`) to retrieve info about stuff like flairs and emotes from the CDN.
- Use `DGGLogs` (`from dgg_chat.logs import DGGLogs`) to retrieve chat logs.

## Limitations

As some would expect, the chat server offers some resistence to spamming messages.
When sending messages in chat, you must know of [websocket server throttling algorithm (#1)](https://github.com/destinygg/chat/blob/master/connection.go#L400),
as well as the chat bot that takes care of spam, but unless you plan on intentionally spamming, no need to worry about it.
When sending whispers, on top of the websocket algorithm, you must be aware of the
[website backend that handles private messages (#2)](https://github.com/destinygg/website/blob/master/lib/Destiny/Messages/PrivateMessageService.php#L23) 
via the API, which is what is used by the websocket server when you whisper someone.

The throttle #1 is dealt with in the [`DGGChat()._handle_message()`](./dgg_chat/_dgg_chat.py#L241) method.
The throttle #2 can be partially exploited via [this attribution](https://github.com/destinygg/website/blob/master/lib/Destiny/Messages/PrivateMessageService.php#L64),
by running a parallel conversation with an echo bot, i.e. on every whisper, also whisper the echo bot.
