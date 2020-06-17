from json import dumps
from datetime import datetime

from ..messages import Message
from .._utils import dict_swap_keys
from .._event_types import EventTypes


class PrivateMessage:
    def __init__(
        self, id,
        deleted_by_receiver,
        deleted_by_sender,
        from_user, target_user,
        from_user_id, target_user_id,
        date_time, is_read, content
    ):
        self.id = id
        self.deleted_by_receiver = bool(int(deleted_by_receiver))
        self.deleted_by_sender = bool(int(deleted_by_sender))
        self.from_user = from_user
        self.target_user = target_user
        self.from_user_id = from_user_id
        self.target_user_id = target_user_id
        self.date_time = datetime.strptime(date_time, '%Y-%m-%dT%H:%M:%S+0000')
        self.is_read = bool(int(is_read))
        self.content = content

    @classmethod
    def from_api_response(cls, response):
        key_map = {
            'deletedbyreceiver': 'deleted_by_receiver',
            'deletedbysender': 'deleted_by_sender',
            'from': 'from_user',
            'to': 'target_user',
            'userid': 'from_user_id',
            'targetuserid': 'target_user_id',
            'isread': 'is_read',
            'message': 'content',
            'timestamp': 'date_time',
        }
        response = dict_swap_keys(response, key_map)
        return cls(**response)

    @property
    def as_websocket_message(self):
        payload = {
            'messageid': self.id,
            'nick': self.from_user,
            'timestamp': int(1000*self.date_time.timestamp()),
            'data': self.content,
        }
        msg = f"{EventTypes.WHISPER} {dumps(payload, ensure_ascii=False)}"
        return Message.parse(msg)
