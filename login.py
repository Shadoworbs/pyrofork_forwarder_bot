import asyncio
import logging
import sys
from pyrogram import Client
from bot.configs import API_ID, API_HASH
from bot.utils import setup_logging
setup_logging()


async def main():
    """
    Login function to log in to Telegram before starting the bot to avoid the infamous login error with Docker.

    This file must be run before starting the bot.
    It will log in to the Telegram account using the provided API_ID and API_HASH.
    """
    async with Client("my_account", API_ID, API_HASH) as app:
        await app.send_message("me", "Successfully logged in!")
    asyncio.sleep(3)
    sys.exit(0)

if __name__ == "__main__":
    logging.info("Starting login process...")
    logging.info("Please ensure you have set your API_ID and API_HASH in the config file.")
    asyncio.run(main())
    logging.info("Login process completed successfully\nYou can now run the main process: python forwarder.py")
