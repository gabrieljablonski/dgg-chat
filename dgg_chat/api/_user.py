from datetime import datetime

from .._utils import dict_keys_camel_to_snake_case


class User:
    def __init__(
        self, id=None, nick=None, username=None,
        status=None, auth_provider=None, country=None,
        created_date=None, features=None, roles=None,
        settings=None, subscription=None
    ):
        self.id = id
        self.nick = nick
        self.username = username
        self.status = status
        self.auth_provider = auth_provider
        self.country = country  # currently not supported
        self.created_date = datetime.strptime(
            created_date, '%Y-%m-%dT%H:%M:%S+0000'
        ) if created_date else None
        self.features = features
        self.roles = roles
        self.settings = settings
        self.subscription = subscription

    def __repr__(self):
        return f"User(id='{self.id}', nick='{self.nick}')"

    @classmethod
    def from_api_response(cls, response):
        response = dict_keys_camel_to_snake_case(response)
        if 'user_id' in response:
            response['id'] = response.pop('user_id')
        if 'user_status' in response:
            response['status'] = response.pop('user_status')
        return cls(**response)

    @property
    def is_subbed(self):
        return "subscriber" in self.features
