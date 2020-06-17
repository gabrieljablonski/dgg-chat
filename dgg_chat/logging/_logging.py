import os
import logging
from logging import NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
from logging.handlers import RotatingFileHandler


MAX_FILE_SIZE = 10*int(2**20)  # 10MiB


def setup_logger(level=logging.NOTSET, file_name='dgg.log', log_to_console=True):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    handler = RotatingFileHandler(
        f"logs/{file_name}", maxBytes=MAX_FILE_SIZE,
        backupCount=10, encoding='utf8'
    )
    handlers = [handler]
    if log_to_console:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        handlers=handlers,
        level=level,
        format=u"[%(asctime)s.%(msecs)03d] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    logging._defaultFormatter = logging.Formatter(u"%(message)s")
