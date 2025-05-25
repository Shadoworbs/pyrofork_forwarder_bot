import json
import shutil
import asyncio
from asyncio.log import logger
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from rich.console import Console

# Configure logging
from bot.utils import setup_logging
setup_logging()


class Database:
    """Database class to handle user settings and data storage.

    Implements a simple JSON-based database with file persistence and backup features.

    Attributes:
        data_dir (Path): Directory to store user data files
        backup_dir (Path): Directory to store database backups
        _data (dict): Dictionary to store user settings in memory
        _lock (asyncio.Lock): Lock for thread-safe operations
    """

    def __init__(self, data_dir: str = None):
        """Initialize database with a data directory.

        Args:
            data_dir (str, optional): Directory to store user data files. Defaults to "user_data".
        """
        self.data_dir = Path(data_dir) if data_dir else Path("user_data")
        self.backup_dir = self.data_dir.parent / f"{self.data_dir.name}_backup"
        self._data: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

        try:
            # Create data and backup directories if they don't exist
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating directories: {e}")
            raise

    async def _acquire_lock(self):
        """Acquire the thread lock."""
        if not self._lock.locked():
            await self._lock.acquire()

    async def _release_lock(self):
        """Release the thread lock."""
        if self._lock.locked():
            self._lock.release()

    def _get_user_file_path(self, user_id: int) -> Path:
        """Get the path to a user's data file"""
        try:
            file_path = self.data_dir / f"{user_id}.json"
            return file_path
        except Exception as e:
            logger.error(f"Error creating file path for user {user_id}: {e}")
            raise

    async def _load_data(self, user_id: int) -> Dict:
        """Load data from user's JSON file with error handling and validation."""
        file_path = self._get_user_file_path(user_id)
        try:
            if file_path.exists():
                # async with self._lock:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        raise ValueError("Invalid data format")
                    self._data[str(user_id)] = data
            else:
                self._data[str(user_id)] = {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for user {user_id}: {e}")
            await self._backup_corrupted_file(file_path)
            self._data[str(user_id)] = {}
        except Exception as e:
            logger.error(f"Error loading data for user {user_id}: {e}")
            self._data[str(user_id)] = {}

        return self._data[str(user_id)]

    async def _save_data(self, user_id: int) -> bool:
        """Save data to user's JSON file with backup."""
        file_path = self._get_user_file_path(user_id)
        temp_file = file_path.with_suffix(".tmp")
        success = False

        try:
            # async with self._lock:
            # Write to temporary file first
            user_data = self._data.get(str(user_id), {})
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)

            # Create backup of existing file if it exists
            if file_path.exists():
                backup_file = (
                    self.backup_dir
                    / f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                shutil.copy2(file_path, backup_file)

            # Replace old file with new one
            temp_file.replace(file_path)
            success = True

        except Exception as e:
            logger.error(f"Error saving data for user {user_id}: {e}")
            if temp_file.exists():
                temp_file.unlink()

        return success

    async def _backup_corrupted_file(self, file_path: Path) -> None:
        """Backup a corrupted file for later investigation."""
        try:
            if file_path.exists():
                corrupt_dir = self.backup_dir / "corrupted"
                corrupt_dir.mkdir(exist_ok=True)
                backup_path = (
                    corrupt_dir
                    / f"{file_path.stem}_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                shutil.copy2(file_path, backup_path)
                logger.warning(f"Backed up corrupted file to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup corrupted file: {e}")

    async def init(self, user_id: int):
        """Initialize database for a user - create if not exists."""
        try:
            user_id_str = str(user_id)
            # async with self._lock:
            if user_id_str not in self._data:
                await self._load_data(user_id)
                if user_id_str not in self._data:
                    self._data[user_id_str] = {
                        "settings": {"user_id": user_id_str},
                        "created_at": str(datetime.now()),
                        "updated_at": str(datetime.now()),
                    }
                    await self._save_data(user_id)
        except Exception as e:
            logger.error(f"Error initializing database for user {user_id}: {e}")
            raise

    async def get_user_settings(self, user_id: int) -> Optional[Dict]:
        """Get user settings with validation and error handling."""
        if self._lock.locked():
            await self._release_lock()
            logger.warning("The database is locked. Unlock it first.")
        try:
            user_id_str = str(user_id)
            # async with self._lock:
            if user_id_str not in self._data:
                await self._load_data(user_id)
            return self._data.get(user_id_str, {})
        except Exception as e:
            logger.error(f"Error getting settings for user {user_id}: {e}")
            return None

    async def set_user_chats(self, user_id: int, source_chat: str, target_chat: str):
        """Set user's source and target chats with validation."""
        user_id_str = str(user_id)
        try:
            # async with self._lock:
            self._data[user_id_str] = {
                "source_chat": source_chat,
                "target_chat": target_chat,
                "settings": {
                    "user_id": user_id_str,
                    "last_msg_id": 0,
                },
                "created_at": str(datetime.now()),
                "updated_at": str(datetime.now()),
            }
            await self._save_data(user_id)
            return True
        except Exception as e:
            logger.error(f"Error setting chats for user {user_id}: {e}")
            return False

    async def update_user_settings(self, user_id: int, settings: Dict[str, Any]):
        """Update user settings with validation."""
        user_id_str = str(user_id)
        try:
            # async with self._lock:
            if user_id_str not in self._data:
                await self._load_data(user_id)
            if user_id_str in self._data:
                self._data[user_id_str]["settings"].update(settings)
                self._data[user_id_str]["updated_at"] = str(datetime.now())
                await self._save_data(user_id)
                return True
            return False
        
        except Exception as e:
            logger.error(f"Error updating settings for user {user_id}: {e}")
            return False

    async def delete_user_settings(self, user_id: int):
        """Delete user settings with backup."""
        try:
            # async with self._lock:
            file_path = self._get_user_file_path(user_id)
            if file_path.exists():
                # Backup before deletion
                backup_file = (
                    self.backup_dir
                    / f"{user_id}_deleted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                shutil.copy2(file_path, backup_file)
                file_path.unlink()
                logger.info(f"Deleted settings for user {user_id} and backed up to {backup_file}")
                
            if str(user_id) in self._data:
                del self._data[str(user_id)]
            return True
        except Exception as e:
            logger.error(f"Error deleting settings for user {user_id}: {e}")
            return False

    async def backup_database(self):
        """Create a timestamped backup of the entire database."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"full_backup_{timestamp}"
            backup_path.mkdir(exist_ok=True)

            # async with self._lock:
                # Save any pending changes
            for user_id in self._data:
                await self._save_data(int(user_id))

            # Copy all files to backup directory
            for file in self.data_dir.glob("*.json"):
                shutil.copy2(file, backup_path / file.name)

            # Create manifest file
            manifest = {
                "backup_time": timestamp,
                "files": [f.name for f in self.data_dir.glob("*.json")],
                "total_users": len(self._data),
            }

            with open(backup_path / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=4)
            logger.info(f"Backup created at {backup_path}")
            return str(backup_path)
        
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
