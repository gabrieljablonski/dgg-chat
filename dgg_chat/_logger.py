import os
import logging
from logging.handlers import RotatingFileHandler


MAX_FILE_SIZE = 10*int(2**20)  # 10MiB


def setup_logger(level=logging.NOTSET):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    handler = RotatingFileHandler('logs/dgg.log', maxBytes=MAX_FILE_SIZE, backupCount=10, encoding='utf8')
    logging.basicConfig(
        handlers=[handler],
        level=level,
        format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
