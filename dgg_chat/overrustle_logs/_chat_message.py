from re import findall
from datetime import datetime

from ..exceptions import InvalidChatLine
from .._utils import format_datetime


class ChatMessage:
    CHAT_LINE_PATTERN = r'^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) UTC\] (\w+): (.+)$'

    def __init__(self, user, date_time: datetime, content):
        self.user = user
        self.date_time = date_time
        self.content = content

    def __repr__(self):
        return f"ChatMessage(user='{self.user}', date_time='{format_datetime(self.date_time)}', content='{self.content}')"

    @property
    def original(self):
        return f"[{format_datetime(self.date_time)}] {self.user}: {self.content}"

    @classmethod
    def from_chat_line(cls, line):
        match = findall(cls.CHAT_LINE_PATTERN, line.strip())
        if not match:
            raise InvalidChatLine(line)

        date_time, user, content = match[0]
        return cls(
            user,
            datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S'),
            content,
        )

    @property
    def is_from_anonymous_user(self):
        return self.user == '_anon$'
