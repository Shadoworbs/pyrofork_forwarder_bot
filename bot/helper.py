import logging
import asyncio
from typing import Tuple, List, Dict, Optional
import pyrogram
from pyrogram import Client, types
from pyrogram.errors import BadRequest, FloodWait, RPCError
from rich.console import Console
from .database import Database

from bot.utils import setup_logging
setup_logging()


class HelperClass:
    """Helper class for chat operations and validation.

    Provides utility methods for chat validation, information retrieval,
    and other common operations.
    """

    def __init__(self, client: Client, db: Database):
        """Initialize the helper class.

        Args:
            client (Client): Pyrogram client instance
            db (Database): Database instance
        """
        self.client = client
        self.db = db

    async def _ensure_db_ready(self, user_id: int) -> bool:
        """Ensure database is initialized and ready for the user.

        Args:
            user_id (int): The user ID to initialize database for.

        Returns:
            bool: True if database is ready, False otherwise.
        """
        try:
            await self.db.init(user_id)
            return True
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            return False

    async def _normalize_chat_id(self, chat_id: str) -> str:
        """Normalize a chat ID by handling different formats.

        Args:
            chat_id (str): The chat ID to normalize

        Returns:
            str: Normalized chat ID
        """
        chat_id = str(chat_id).strip()

        # Handle usernames
        if chat_id.startswith("@"):
            return chat_id

        # Handle channel/group IDs
        if chat_id.startswith("-100"):
            return chat_id

        # Convert numerical IDs
        try:
            if chat_id.isdigit():
                return str(int(chat_id))
        except ValueError:
            pass

        return chat_id

    async def is_valid_chat(self, chat_ids: tuple) -> Tuple[bool, List[str]]:
        """Validates if given chat IDs are accessible to the client.

        Args:
            chat_ids (tuple): A tuple containing chat IDs to validate. Chat IDs can be:
                - Integer IDs (e.g. -1001234567890)
                - String usernames (e.g. "@username")
                - Special strings ("me" or "self")

        Returns:
            Tuple[bool, List[str]]: A tuple containing:
                - bool: True if all chat IDs are valid and accessible
                - List[str]: List of invalid chat IDs
        """
        validity = True
        faulty_ids = []

        for chat_id in chat_ids:
            try:
                # Normalize chat ID
                chat_id = await self._normalize_chat_id(chat_id)

                # Try to get chat info
                chat = await self.client.get_chat(chat_id)

                # Verify that we got a valid chat object
                if not isinstance(chat, pyrogram.types.Chat):
                    validity = False
                    faulty_ids.append(str(chat_id))
                    logging.warning(f"Invalid chat type for ID {chat_id}")

            except BadRequest as e:
                validity = False
                faulty_ids.append(str(chat_id))
                logging.error(f"Bad request for chat ID {chat_id}: {e}")

            except FloodWait as e:
                await asyncio.sleep(e.value)
                # Retry after flood wait
                try:
                    chat = await self.client.get_chat(chat_id)
                except Exception as retry_e:
                    validity = False
                    faulty_ids.append(str(chat_id))
                    logging.error(f"Retry failed for chat ID {chat_id}: {retry_e}")

            except Exception as e:
                validity = False
                faulty_ids.append(str(chat_id))
                logging.error(f"Error validating chat ID {chat_id}: {e}")

        return validity, faulty_ids

    async def get_chat_info(self, chat_ids: tuple) -> List[Dict[str, str]]:
        """Get chat information for a list of chat IDs.

        Args:
            chat_ids (tuple): A tuple containing chat IDs to get information for.
                            Chat IDs can be numeric IDs, usernames, or special identifiers.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing chat information
        """
        chat_info = []

        for chat_id in chat_ids:
            info = {
                "title": "Unknown",
                "type": "Unknown",
                "members": "N/A",
                "id": str(chat_id),
                "username": None,
                "description": None,
            }

            try:
                # Normalize chat ID
                chat_id = await self._normalize_chat_id(chat_id)

                # Get chat info
                chat = await self.client.get_chat(chat_id)

                # Extract common information
                info["id"] = str(chat.id)
                info["type"] = str(chat.type) if hasattr(chat, "type") else "Unknown"
                info["username"] = getattr(chat, "username", None)

                # Handle different chat types
                # print(f"Chat Type: {chat.type}")
                if hasattr(chat, "type") and str(chat.type).split(".")[-1].lower() in [
                    "group",
                    "supergroup",
                    "channel",
                ]:
                    info["title"] = getattr(chat, "title", "Unknown")
                    info["description"] = getattr(chat, "description", None)
                    try:
                        count = await self.client.get_chat_members_count(chat.id)
                        info["members"] = str(count)
                    except Exception as e:
                        logging.warning(
                            f"Could not get member count for {chat_id}: {e}"
                        )
                    # print(f"Chat Type: {chat.type}")
                elif hasattr(chat, "type") and str(chat.type).split(".")[-1].lower() == "private":
                    info["title"] = (
                        f"{getattr(chat, 'first_name', '')} {getattr(chat, 'last_name', '')}".strip()
                    )
                    info["members"] = "2"  # Private chats always have 2 members

            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue

            except Exception as e:
                logging.error(f"Error getting chat info for {chat_id}: {e}")

            chat_info.append(info)

        return chat_info

    async def validate_permissions(
        self, chat_id: str, required_permissions: List[str]
    ) -> bool:
        """Validate that the bot has required permissions in a chat.

        Args:
            chat_id (str): The chat ID to check permissions for
            required_permissions (List[str]): List of required permission strings

        Returns:
            bool: True if all required permissions are available
        """
        try:
            # Get bot's member info in the chat
            bot_member = await self.client.get_chat_member(chat_id, "me")

            # Check each required permission
            for permission in required_permissions:
                if not getattr(bot_member.privileges, permission, False):
                    return False

            return True

        except Exception as e:
            logging.error(f"Error checking permissions in {chat_id}: {e}")
            return False
