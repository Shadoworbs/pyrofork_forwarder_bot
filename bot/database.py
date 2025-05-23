from asyncio.log import logger
import json
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path

 
class Database:
    """Database class to handle user settings and data storage.

    Attributes:
        data_dir (Path): Directory to store user data files
        _data (dict): Dictionary to store user settings
    """

    def __init__(self, data_dir: str = None):
        """Initialize database with a data directory.

        Args:
            data_dir (str, optional): Directory to store user data files. Defaults to "user_data".
        """
        self.data_dir = Path(data_dir) if data_dir else Path("user_data")
        self._data = {}

        try:
            # Create data directory if it doesn't exist
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating data directory: {e}")
            raise

    def _get_user_file_path(self, user_id: int) -> Path:
        """Get the path to a user's data file"""
        try:
            file_path = Path(self.data_dir) / f"{user_id}.json"
            return file_path
        except Exception as e:
            logger.error(f"Error creating file path for user {user_id}: {e}")
            raise

    def _ensure_user_initialized(self, user_id: int):
        """Ensure user data is loaded and initialized"""
        user_id_str = str(user_id)
        if user_id_str not in self._data:
            self._load_data(user_id)

    def _load_data(self, user_id: int):
        """Load data from user's JSON file"""
        file_path = self._get_user_file_path(user_id)
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    self._data[str(user_id)] = json.load(f)
            else:
                self._data[str(user_id)] = {}
        except Exception as e:
            logger.error(f"Error loading database for user {user_id}: {e}")
            self._data[str(user_id)] = {}
        return self._data[str(user_id)]

    def _save_data(self, user_id: int):
        """Save data to user's JSON file"""
        file_path = self._get_user_file_path(user_id)
        try:
            # Ensure data dir exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            # Save only this user's data to their file
            user_data = self._data.get(str(user_id), {})
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving database for user {user_id}: {e}")

    async def init(self, user_id: int):
        """Initialize database for a user - create if not exists.

        Args:
            user_id (int): The user ID to initialize settings for.
        """
        try:
            self._ensure_user_initialized(user_id)
            user_id_str = str(user_id)

            if user_id_str not in self._data:
                self._data[user_id_str] = {
                    "settings": {"user_id": user_id_str},
                    "created_at": str(datetime.now()),
                    "updated_at": str(datetime.now()),
                }
                self._save_data(user_id)

        except Exception as e:
            logger.error(f"Error initializing database for user {user_id}: {e}")
            raise

    async def get_user_settings(self, user_id: int) -> Optional[Dict]:
        """Get user settings from database.

        Args:
            user_id (int): The user ID to get settings for.

        Returns:
            Optional[Dict]: The user's settings or None if not found.
        """
        try:
            user_id_str = str(user_id)
            user_file = Path(self._get_user_file_path(user_id))

            # If data not in memory and file exists, load from file
            if user_id_str not in self._data and user_file.exists():
                self._load_data(user_id)

            # If data still not found, initialize empty settings
            if user_id_str not in self._data:
                await self.init(user_id)

            return self._data.get(user_id_str, {})

        except Exception as e:
            logger.error(f"Error getting settings for user {user_id}: {e}")
            return None

    async def set_user_chats(self, user_id: int, source_chat: str, target_chat: str):
        """Set user's source and target chats"""
        user_id_str = str(user_id)
        self._data[user_id_str] = {
            "source_chat": source_chat,
            "target_chat": target_chat,
            "settings": {
                "user_id": user_id_str,
            },
            "created_at": str(datetime.now()),
            "updated_at": str(datetime.now()),
        }
        self._save_data(user_id)

    async def update_user_settings(self, user_id: int, settings: Dict):
        """Update user settings"""
        user_id_str = str(user_id)
        if user_id_str not in self._data:
            self._load_data(user_id)
        if user_id_str in self._data:
            self._data[user_id_str]["settings"] = settings
            self._data[user_id_str]["updated_at"] = str(datetime.now())
            self._save_data(user_id)

    async def delete_user_settings(self, user_id: int):
        """Delete user settings"""
        file_path = self._get_user_file_path(user_id)
        if file_path.exists():
            try:
                file_path.unlink()  # Delete the user's file
            except Exception as e:
                logger.error(f"Error deleting settings for user {user_id}: {e}")
        if str(user_id) in self._data:
            del self._data[str(user_id)]

    async def reset_user_settings(self, user_id: int):
        """Reset user settings by deleting them"""
        await self.delete_user_settings(user_id)

    async def backup_database(self):
        """Create a backup of the entire data directory"""
        try:
            backup_dir = self.data_dir.with_suffix(".bak")
            if not backup_dir.exists():
                backup_dir.mkdir(parents=True)
            # Copy all user files to backup directory
            for file in self.data_dir.glob("*.json"):
                backup_file = backup_dir / file.name
                with open(file, "r", encoding="utf-8") as src, open(
                    backup_file, "w", encoding="utf-8"
                ) as dst:
                    dst.write(src.read())
            return True
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
