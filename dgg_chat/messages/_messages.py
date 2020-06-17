from json import loads, dumps

from .._event_types import EventTypes


class ChatUser:
    def __init__(self, nick, features):
        self.nick = nick
        self.features = features

    @classmethod
    def from_ws_messsage(cls, msg):
        return cls(nick=msg.get('nick'), features=msg.get('features'))

    def __repr__(self):
        return f"ChatUser(nick='{self.nick}')"


class Message:
    def __init__(self, msg):
        split = msg.split()
        self.event = split[0]
        payload = ' '.join(split[1:])
        try:
            self.payload = loads(payload)
        except:
            self.payload = payload

    def __repr__(self):
        obj = self.__dict__.copy()
        if type(self).__name__ != Message.__name__:
            del obj['payload']
        return dumps(obj, default=lambda o: o.__dict__, ensure_ascii=False)

    @classmethod
    def parse(cls, msg):
        event = msg.split()[0]
        if event == EventTypes.SERVED_CONNECTIONS:
            return ServedConnections(msg)
        if event == EventTypes.USER_JOINED:
            return UserJoined(msg)
        if event == EventTypes.USER_QUIT:
            return UserQuit(msg)
        if event == EventTypes.BROADCAST:
            return Broadcast(msg)
        if event == EventTypes.CHAT_MESSAGE:
            return ChatMessage(msg)
        if event == EventTypes.WHISPER:
            return Whisper(msg)
        if EventTypes.is_moderation_event(event):
            return ModerationMessage(msg)
        return cls(msg)

    @property
    def json(self):
        obj = self.__dict__.copy()
        if type(self).__name__ != Message.__name__:
            del obj['payload']
        return dumps(obj, default=lambda o: o.__dict__, indent=4, ensure_ascii=False)


class ServedConnections(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.count = self.payload.get('connectioncount')
        self.users = [
            ChatUser.from_ws_messsage(u) for u in self.payload.get('users')
        ]


class UserJoined(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.user = ChatUser.from_ws_messsage(self.payload)
        self.timestamp = self.payload.get('timestamp')/1000.


class UserQuit(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.user = ChatUser.from_ws_messsage(self.payload)
        self.timestamp = self.payload.get('timestamp')/1000.


class Broadcast(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.timestamp = self.payload.get('timestamp')/1000.
        self.content = self.payload.get('data')


class ChatMessage(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.user = ChatUser.from_ws_messsage(self.payload)
        self.timestamp = self.payload.get('timestamp')/1000.
        self.content = self.payload.get('data')


class Whisper(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.user = ChatUser.from_ws_messsage(self.payload)
        self.message_id = self.payload.get('messageid')
        self.timestamp = self.payload.get('timestamp')/1000.
        self.content = self.payload.get('data')


class ModerationMessage(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.moderator = ChatUser.from_ws_messsage(self.payload)
        self.timestamp = self.payload.get('timestamp')/1000.
        user, *sentence = self.payload.get('data').split()
        self.affected_user = user
        self.sentence = ' '.join(sentence)


class SubOnly(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.moderator = ChatUser.from_ws_messsage(self.payload)
        self.timestamp = self.payload.get('timestamp')/1000.
        # on or off
        self.mode = self.payload.get('data')
