from os import getenv
from time import sleep
from dotenv import load_dotenv
from logging import DEBUG

from dgg_chat import DGGChat, setup_logger


load_dotenv(verbose=True)
dgg_auth_token = getenv('DGG_AUTH_TOKEN')

setup_logger(DEBUG)

chat = DGGChat(auth_token=dgg_auth_token, print_messages=True)
chat.run_forever()
