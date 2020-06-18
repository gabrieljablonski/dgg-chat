import logging
from typing import Union
from requests import get
from datetime import datetime

from ._chat_message import ChatMessage

from ..exceptions import APIError
from .._utils import validate_date_time, isplit


class DGGLogs:
    """
    API for OverRustleLogs dgg logs.
    API calls return generators, thus memory efficient.
    Messages are timestamped in UTC.
    """

    DGG_LOGS = 'https://overrustlelogs.net/Destinygg%20chatlog'

    @classmethod
    def _parse_logs(cls, logs):
        for line in isplit(logs, '\n'):
            if line:
                yield ChatMessage.from_chat_line(line)

    @classmethod
    def _build_date(cls, year=0, month=None):
        if not month:
            month = datetime.utcnow().month
        if not year:
            year = datetime.utcnow().year

        if isinstance(month_full := month, int):
            month_full = datetime.strptime(str(month), '%m').strftime('%B')

        # raises `ValueError`
        validate_date_time(year=year, month=month)
        return f"{month_full} {year}"

    @classmethod
    def _get(cls, endpoint, year=0, month=None):
        date = cls._build_date(year, month)
        url = f"{cls.DGG_LOGS}/{date}/{endpoint}"

        logging.info(f"retrieving: {url}")

        r = get(url)

        logging.info(f"response: {r.status_code}")

        if r.status_code == 404:
            raise FileNotFoundError

        if r.status_code != 200:
            raise APIError(url, r)

        return cls._parse_logs(r.content.decode('utf8'))

    @classmethod
    def get_daily_logs(cls, year=0, month=0, day=0):
        """
        Retrieves chat logs for a specific day, month, and year.
        If any isn't provided, use current based on UTC time.
        """

        now = datetime.utcnow()

        year = year or now.year
        month = month or now.month
        day = day or now.day

        date = f"{year}-{month:02d}-{day:02d}"

        endpoint = f"{date}.txt"
        return cls._get(endpoint, year, month)

    @classmethod
    def get_user_logs(cls, user, year=0, month: Union[int, str] = None):
        """
        Retrieves user logs for a specific month and year.
        If either is not provided, use current based on UTC time.

        `month` : `int` or `str`

            if `str`, has to be the full month name ('January', 'February', ...).

        """

        endpoint = f"userlogs/{user}.txt"
        return cls._get(endpoint, year, month)

    @classmethod
    def get_broadcaster_logs(cls, year=0, month: Union[int, str] = None):
        """
        Retrieves broadcaster logs for a specific month and year.
        If either is not provided, use current based on UTC time.

        `month` : `int` or `str`

            if `str`, has to be the full month name ('January', 'February', ...).

        """

        endpoint = f"broadcaster.txt"
        return cls._get(endpoint, year, month)

    @classmethod
    def get_subscribers(cls, year=0, month: Union[int, str] = None):
        """
        Retrieves users who subscribed in a specific month and year.
        If either is not provided, use current based on UTC time.

        `month` : `int` or `str`

            if `str`, has to be the full month name ('January', 'February', ...).

        """

        endpoint = f"subscribers.txt"
        return cls._get(endpoint, year, month)

    @classmethod
    def get_bans(cls, year=0, month: Union[int, str] = None):
        """
        Retrieves ban messages from a specific month and year.
        If either is not provided, use current based on UTC time.

        `month` : `int` or `str`

            if `str`, has to be the full month name ('January', 'February', ...).

        """

        endpoint = f"bans.txt"
        return cls._get(endpoint, year, month)
