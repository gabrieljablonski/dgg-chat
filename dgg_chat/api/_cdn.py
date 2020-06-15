import logging
from re import findall
from json import loads
from requests import get

from ..exceptions import APIError, CDNError


class DGGCDN:
    """
    An API for dgg's CDN.
    Let's you get info about emotes, flairs, and maybe other stuff.
    """

    DGG = 'https://www.destiny.gg/embed/chat'
    PATTERN = r'data-cache-key=\"(\d+\.\d+)\" data-cdn=\"(https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*))\"'

    def __init__(self):
        self.cdn = None
        self.cache_key = None

        self._setup()

    def _setup(self):
        logging.info('setting up cdn...')

        r = get(self.DGG)

        if r.status_code != 200:
            raise APIError(DGG, r)

        content = r.content.decode()
        matches = findall(self.PATTERN, content)

        if not matches:
            raise CDNError('failed to find cache key and cdn url')

        self.cache_key, self.cdn = matches[0]

        logging.info(f"setup cdn: {self.cdn} cache key: {self.cache_key}")

    def get(self, object_path, as_json=True):
        if not object_path.startswith('/'):
            object_path = f"/{object_path}"

        url = f"{self.cdn}{object_path}?_={self.cache_key}"
        logging.info(f"retrieving: {url}")
        r = get(url, allow_redirects=False)

        logging.info(f"retrieved: {r.content.decode()[:200]}")

        if r.status_code in (301, 404):
            raise FileNotFoundError(object_path)

        if r.status_code != 200:
            raise APIError(url, r)

        if as_json:
            return loads(r.content.decode())

        return r.content

    def get_flairs(self):
        return self.get('/flairs/flairs.json')

    def get_emotes(self):
        return self.get('/emotes/emotes.json')
