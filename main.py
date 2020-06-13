from os import getenv
from time import sleep
from dgg_chat import DGGChat
from dotenv import load_dotenv


load_dotenv(verbose=True)
dgg_auth_token = getenv('DGG_AUTH_TOKEN')

chat = DGGChat(auth_token=dgg_auth_token, print_messages=True)
chat.run_forever()
