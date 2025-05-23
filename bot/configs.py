import os
from dotenv import load_dotenv

load_dotenv(".env")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", default="@shadoworbs")


class Config(object):
    API_ID = API_ID
    API_HASH = API_HASH
    OWNER_USERNAME = OWNER_USERNAME
    OWNER_ID = int(os.getenv("OWNER_ID", default=0))
