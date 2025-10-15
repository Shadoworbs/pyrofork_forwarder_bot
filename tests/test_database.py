import asyncio
import json
from pathlib import Path

from bot.database import Database


def test_database_init_and_settings(tmp_path):
    asyncio.run(_exercise_database(tmp_path))


async def _exercise_database(tmp_path):
    data_dir = tmp_path / "data"
    db = Database(str(data_dir))
    user_id = 12345

    await db.init(user_id)
    settings = await db.get_user_settings(user_id)

    assert settings is not None
    assert settings.get("settings", {}).get("user_id") == str(user_id)

    await db.set_user_chats(user_id, "source_chat", "target_chat")
    updated = await db.get_user_settings(user_id)

    assert updated["source_chat"] == "source_chat"
    assert updated["target_chat"] == "target_chat"

    changed = await db.update_user_settings(user_id, {"last_msg_id": 99})
    assert changed is True
    refreshed = await db.get_user_settings(user_id)
    assert refreshed["settings"]["last_msg_id"] == 99

    backup_path = await db.backup_database()
    assert backup_path is not None
    backup_dir = Path(backup_path)
    assert backup_dir.exists()
    manifest = json.loads((backup_dir / "manifest.json").read_text())
    assert manifest["total_users"] == 1

    deleted = await db.delete_user_settings(user_id)
    assert deleted is True
    assert await db.get_user_settings(user_id) == {}

    assert not (data_dir / f"{user_id}.json").exists()
