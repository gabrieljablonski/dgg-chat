from json import loads, dumps


class MessageTypes:
    SERVED_CONNECTIONS = 'NAMES'
    USER_JOINED = 'JOIN'
    USER_QUIT = 'QUIT'
    BROADCAST = 'BROADCAST'
    CHAT_MESSAGE = 'MSG'
    WHISPER = 'PRIVMSG'
    WHISPER_SENT = 'PRIVMSGSENT'
    MUTE = 'MUTE'
    UNMUTE = 'UNMUTE'
    BAN = 'BAN'
    UNBAN = 'UNBAN'
    SUB_ONLY = 'SUBONLY'
    ERROR = 'ERR'

    @staticmethod
    def is_moderation_message(msg_type):
        return msg_type in (MessageTypes.MUTE, MessageTypes.UNMUTE, MessageTypes.BAN, MessageTypes.UNBAN)


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
        self.type = split[0]
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
        message_type = msg.split()[0]
        if message_type == MessageTypes.SERVED_CONNECTIONS:
            return ServedConnections(msg)
        if message_type == MessageTypes.USER_JOINED:
            return UserJoined(msg)
        if message_type == MessageTypes.USER_QUIT:
            return UserQuit(msg)
        if message_type == MessageTypes.BROADCAST:
            return Broadcast(msg)
        if message_type == MessageTypes.CHAT_MESSAGE:
            return ChatMessage(msg)
        if message_type == MessageTypes.WHISPER:
            return Whisper(msg)
        if MessageTypes.is_moderation_message(message_type):
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
        self.timestamp = self.payload.get('timestamp')


class UserQuit(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.user = ChatUser.from_ws_messsage(self.payload)
        self.timestamp = self.payload.get('timestamp')


class Broadcast(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.timestamp = self.payload.get('timestamp')
        self.content = self.payload.get('data')


class ChatMessage(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.user = ChatUser.from_ws_messsage(self.payload)
        self.timestamp = self.payload.get('timestamp')
        self.content = self.payload.get('data')


class Whisper(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.user = ChatUser.from_ws_messsage(self.payload)
        self.message_id = self.payload.get('messageid')
        self.timestamp = self.payload.get('timestamp')
        self.content = self.payload.get('data')


class ModerationMessage(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.moderator = ChatUser.from_ws_messsage(self.payload)
        self.timestamp = self.payload.get('timestamp')
        user, *sentence = self.payload.get('data').split()
        self.affected_user = user
        self.sentence = ' '.join(sentence)


class SubOnly(Message):
    def __init__(self, msg):
        super().__init__(msg)
        self.moderator = ChatUser.from_ws_messsage(self.payload)
        self.timestamp = self.payload.get('timestamp')
        # on or off
        self.mode = self.payload.get('data')
