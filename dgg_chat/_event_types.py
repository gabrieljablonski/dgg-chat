class EventTypes:
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

    class Special:
        ANY_MESSAGE = 'ANY_MESSAGE'
        MENTION = 'MENTION'
        WS_ERROR = 'WS_ERROR'
        WS_CLOSE = 'WS_CLOSE'

    @staticmethod
    def is_moderation_event(msg_type):
        return msg_type in (EventTypes.MUTE, EventTypes.UNMUTE, EventTypes.BAN, EventTypes.UNBAN)
