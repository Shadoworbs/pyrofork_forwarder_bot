import logging
from pyrogram import Client
from pyrogram.types import Message
from bot.helper import HelperClass as conv_handler
from .database import Database
from rich.console import Console

console = Console()

class SettingsManager:
    def __init__(self, client: Client, db: Database):
        self.client = client
        self.db = db
 
    async def _ensure_db_ready(self, user_id: int, message: Message) -> bool:
        """Ensure database is ready for the user.

        Args:
            user_id (int): User ID to check database for
            message (Message): Message to reply to if error occurs

        Returns:
            bool: True if database is ready, False otherwise
        """
        try:
            if not self.db.data_dir.exists():
                self.db.data_dir.mkdir(parents=True, exist_ok=True)

            await self.db.init(user_id)
            return True

        except Exception as e:
            console.log(f"[Red] Error initializing database: {e} [/Red]")
            await message.reply("❌ Error accessing settings. Please try again later.")
            return False

    async def show_settings(self, message: Message):
        """Display user settings in a clean text format"""
        info_handler = conv_handler(self.client, self.db)
        try:
            user_id = message.from_user.id

            # Ensure database is ready
            if not await self._ensure_db_ready(user_id, message):
                return

            settings = await self.db.get_user_settings(user_id)

            if not settings:
                await message.reply(
                    "❌ No settings found. Use /set_ids to configure your forward settings."
                )
                return

            source_chat = settings.get("source_chat", "Not set")
            target_chat = settings.get("target_chat", "Not set")
            updated_at = settings.get("updated_at", "Unknown")

            chat_infos: tuple[dict] = await info_handler.get_chat_info((source_chat, target_chat))
            if chat_infos:
                source_chat_title = chat_infos[0].get("title", "Unknown")
                source_chat_id = chat_infos[0].get("id", "Unknown")
                target_chat_title = chat_infos[1].get("title", "Unknown")
                target_chat_id = chat_infos[1].get("id", "Unknown")

            text = (
                "📱 **Current Forward Settings**\n"
                f"**SOURCE CHAT:**\n"
                f"📤 **Source Chat ID:** `{source_chat_id}`\n"
                f"📥 **Source Chat Title:** `{source_chat_title}`\n"
                f"📥 **Chat Type:** `{str(chat_infos[0].get('type', 'Unknown')).split(".")[-1]}`\n\n"
                f"🎯 **TARGET CHAT:🎯**:\n"
                f"📥 **Target Chat ID:** `{target_chat_id}`\n"
                f"📥 **Target Chat Title:** `{target_chat_title}`\n"
                f"📥 **Chat Type:** `{str(chat_infos[1].get('type', "Unknown")).split(".")[-1]}`\n\n"
                f"🕒 **Last Updated:** `{updated_at}`\n"
            )

            await message.reply(text)

        except Exception as e:
            console.log(f"[Red] Error displaying settings: {e} [/Red]")
            await message.reply(
                "❌ An error occurred while fetching settings. Please try again later."
            )