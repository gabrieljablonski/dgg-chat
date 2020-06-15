import logging
from json import loads
from datetime import datetime
from requests import get

from ._user import User
from ._stream_info import StreamInfo
from ._private_message import PrivateMessage
from ..exceptions import APIError, AnonymousConnectionError, AnonymousSessionError


class DGGAPI:
    DGG_API = 'https://www.destiny.gg/api'
    
    def __init__(self, auth_token=None, session_id=None):
        self._auth_token = auth_token
        self._session_id = session_id

    @property
    def auth_token(self):
        return self._auth_token

    def _get(self, endpoint, as_json=True):
        logging.info(f"calling api on `{endpoint}`")

        endpoint = f"{self.DGG_API}{endpoint}"
        cookies = dict(authtoken=self._auth_token, sid=self._session_id)

        r = get(endpoint, cookies=cookies)
        if r.status_code != 200:
            raise APIError(endpoint, r)
        
        logging.info(f"received from api: `{r.content.decode()}`")
        return loads(r.content) if as_json else r.content

    def user_info(self):
        if not self._auth_token:
            raise AnonymousConnectionError('unable to get profile')
        user = self._get(f"/userinfo?token={self._auth_token}")
        return User.from_api_response(user)

    def chat_me(self):
        if not self._auth_token:
            raise AnonymousSessionError('unable to get profile')

        user = self._get('/chat/me')
        return User.from_api_response(user)

    def chat_history(self):
        """
        Returns a list of the last 150 chat messages from right before connecting.
        The format is the same as used in the WebSocket interface.
        """

        return self._get('/chat/history')

    def messages_unread(self):
        """
        Returns a dictionary with the username and the amount of private messages
        currently unread from that user.
        """

        if not self._session_id:
            raise AnonymousSessionError('unable to get unread messages')

        unread = self._get('/messages/unread')
        return {
            m.get('username'): m.get('unread')
            for m in unread
        }

    def messages_inbox(self, user, offset=0):
        """
        Returns a list of last 25 `PrivateMessages` exchanged with `user`.
        `offset` can be user to retrieve older messages.
        This marks messages as read.
        """

        if not self._session_id:
            raise AnonymousSessionError('unable to get inbox')

        inbox = self._get(f"/messages/usr/{user}/inbox?s={offset}")
        return [
            PrivateMessage.from_api_response(m)
            for m in inbox
        ]

    def info_stream(self):
        """Returns info about current stream if live, or last stream."""

        info = self._get('/info/stream')
        return StreamInfo.from_api_response(info)
