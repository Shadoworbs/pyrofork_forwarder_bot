from pyrogram import Client
import pyrogram

# Configure logger
from pyrogram.types import Message
from pyrogram.errors import BadRequest
from rich.console import Console
from .database import Database

console = Console()

class ConversationHandler:
    def __init__(self, client: Client, db: Database):
        self.client = client
        self.db = db
        # self.active_conversations: Dict[Any, Dict] = {}

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
            console.log(f"[Red] Error initializing database: {e} [/Red]")
            return False

    async def is_valid_chat(self, chat_ids: tuple) -> tuple[bool, list]:
        """
        Validates if given chat IDs are accessible to the client.

        Args:
            chat_ids (tuple): A tuple containing chat IDs to validate. Chat IDs can be:
                - Integer IDs (e.g. -1001234567890)
                - String usernames (e.g. "@username")
                - Special strings ("me" or "self")

        Returns:
            bool: True if all chat IDs are valid and accessible, False otherwise.
                Returns False if:
                - Any chat ID is invalid
                - Client cannot access one or more chats
                - Any other errors occur during validation

        Raises:
            No exceptions are raised, all are caught and return False
        """
        validity: bool = True
        faulty_ids: list = []
        for id in chat_ids:
            try:
                id = str(id).strip()
                if id.startswith("-100") or id.isdigit():
                    id = int(id)
                chat = await self.client.get_chat(id)
                if not isinstance(chat, pyrogram.types.Chat):
                    print(f"Invalid chat ID: {id}")
                    validity = False
                    faulty_ids.append(id)
                return validity, str(faulty_ids)
            except BadRequest:
                print("BadRequest: Invalid chat ID")
                validity = False
                pass
            except Exception:
                print(f"Exception: Unable to access chat {id}")
                validity = False
                pass
        return validity, str(faulty_ids)
    async def get_chat_info(self, chat_ids: tuple) -> list[dict]:
        """Get chat information for a list of chat IDs. @shadoworbs

        This method fetches information about Telegram chats including title, type, member count
        and chat ID for each valid chat ID provided.

        Args:
            chat_ids (tuple): A tuple containing chat IDs to get information for.
                             Chat IDs can be numeric IDs, usernames, or special identifiers.

        Returns:
            list[Dict]: A list of dictionaries containing chat information with the following keys:
                        - title (str): Chat title, first name, or chat ID if neither exists
                        - type (str): Type of chat (private, group, supergroup, etc.) or "Unknown"
                        - members (str): Number of members in the chat or "N/A"/"Unknown"
                        - id (str): The chat ID as a string

        Note:
            - Only processes chat IDs that pass the is_valid_chat check
            - Returns fallback values if chat information cannot be fetched
            - Handles exceptions gracefully by logging errors and returning placeholder data
        """
        chat_info: list[dict] = []
        for chat_id in chat_ids:
            if await self.is_valid_chat((chat_id,)):
                try:
                    chat = await self.client.get_chat(chat_id)
                    infos = {
                        "title": (
                            chat.title
                            if chat.title
                            else chat.first_name if chat.first_name else chat_id
                        ),
                        "type": chat.type if chat.type else "Unknown",
                        "members": (
                            chat.members_count if chat.members_count else "N/A"
                        ),
                        "id": str(chat.id),
                    }
                    chat_info.append(infos)
                except:
                    console.log(f"[Red] Error fetching chat info for {chat_id} [/Red]")
                    chat_info.append(
                        {
                            "title": "Unknown",
                            "type": "Unknown",
                            "members": "Unknown",
                            "id": str(chat_id),
                        }
                    )
        return chat_info
