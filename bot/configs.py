import os
from re import M
from dotenv import load_dotenv

load_dotenv(".env")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", default="@shadoworbs")
MEDIA_ONLY_MODE = os.getenv("MEDIA_ONLY_MODE", default=False)


class Config(object):
    API_ID = API_ID
    API_HASH = API_HASH
    OWNER_USERNAME = OWNER_USERNAME
    OWNER_ID = int(os.getenv("OWNER_ID", default=0))
    DELAY_FOR_SINGLE_MESSAGE = int(os.getenv("DELAY_FOR_SINGLE_MESSAGE", default=1))
    DELAY_FOR_MEDIA_GROUPS = int(os.getenv("DELAY_FOR_MEDIA_GROUPS", default=2))
    MEDIA_ONLY_MODE = MEDIA_ONLY_MODE
