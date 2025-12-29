# How to setup>>>
#
# 1. Rename environ.env to .env and update the values API_ID, API_HASH, and OWNER_ID.
#
#
import logging
import asyncio
import sys
import time
from datetime import datetime
from typing import Dict, List

from pyrogram.errors import FloodWait
from pyrogram import Client, filters
from pyrogram.types import Message
from rich.console import Console

from bot.configs import Config
from bot.database import Database
from bot.media_collector import MediaGroupCollector
from bot.helper import HelperClass
from bot.settings_manager import SettingsManager
from bot.utils import ForwardStats, MessageQueue, RetryHandler, setup_logging

# Configure logging
setup_logging()


## --------------------
api_id = Config.API_ID
api_hash = Config.API_HASH

# Configuration constants
DELAY_FOR_SINGLE_MESSAGE = Config.DELAY_FOR_SINGLE_MESSAGE
DELAY_FOR_MEDIA_GROUPS = Config.DELAY_FOR_MEDIA_GROUPS
BATCH_SIZE = 200  # Messages fetched per API call when streaming history
MEDIA_GROUP_FLUSH_SECONDS = getattr(Config, "MEDIA_GROUP_FLUSH_SECONDS", 3)
DRY_RUN_DEFAULT = "--dry-run" in sys.argv or "-n" in sys.argv

# Initialize components
console = Console()
db = Database("user_data")  # Initialize with user_data directory
active_forwards: Dict[int, MessageQueue] = {}  # Track active forward operations by user
forward_stats: Dict[int, ForwardStats] = {}  # Track statistics by user
retry_handler = RetryHandler(max_retries=5, base_delay=1.0)
reset_confirmations = {}  # Track reset confirmations

# Initialize client with optimized settings
app = Client(
    "my_account",
    api_id=api_id,
    api_hash=api_hash,
    app_version="Forwarder v1.0",
    device_model="Server",
    system_version="1.0",
)

# Initialize handlers
conversation_handler = HelperClass(app, db)
settings_manager = SettingsManager(app, db)

# ------------- Command Handlers ------------- #


@app.on_message(
    filters.command("start") & filters.user(Config.OWNER_ID) & filters.private
)
async def start_command(client: Client, message: Message):
    """Handle start command"""
    start_text = """
Hi, welcome to the Best Forwarder Bot! 🤖\n
Send `/help` to see available commands.\n"""
    await message.reply(start_text, disable_web_page_preview=True)


@app.on_message(
    filters.command("help") & filters.user(Config.OWNER_ID) & filters.private
)
async def help_command(client: Client, message: Message):
    """Handle help command"""
    help_text = """
Hello! 👋\n
I am your personal forwarder bot.\nI can help you forward files from one chat to another with ease.\n\n
Here are the available commands:\n
**/start:** Start the bot\n
**/set_ids (or /set):** source_chat_id target_chat_id - Set the source and target chat IDs for forwarding.\n
**/forward (or /f):** Start forwarding files from the source chat to the target chat.\n
    **/forward --dry-run:** Simulate the forward without sending any messages.\n
**/stop:** Stop an ongoing forward operation\n
**/count (or /cnt):** Show chat history statistics with ETA for forwarding (chat IDs must be set first)\n
**/settings (or /st):** View your current settings\n
**/stats:** View detailed statistics of the current/last forward operation\n
**/rs (or /reset):** Reset your settings and start over.\n
"""
    await message.reply(help_text)


@app.on_message(
    filters.command("stop") & filters.user(Config.OWNER_ID) & filters.private
)
async def stop_command(client: Client, message: Message):
    """Stop ongoing forward operation"""
    user_id = message.from_user.id
    if user_id in active_forwards:
        queue = active_forwards[user_id]
        queue.stop()
        del active_forwards[user_id]
        stats = forward_stats.get(user_id)
        if stats:
            await message.reply(
                f"⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️\n\n"
                f"** ✋ Forward process stopped by {user_id}.**\n\n{stats.format_progress()}\n"
                f"⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️"
            )
            logging.info(f"Forward operation stopped by user {user_id}")
    else:
        await message.reply("❌ No active forward operation to stop.")


@app.on_message(
    filters.command("stats") & filters.user(Config.OWNER_ID) & filters.private
)
async def stats_command(client: Client, message: Message):
    """Show forward operation statistics"""
    user_id = message.from_user.id
    stats = forward_stats.get(user_id)
    if stats:
        await message.reply(stats.format_progress())
    else:
        await message.reply(
            "❌ No statistics available. Start a forward operation first."
        )


@app.on_message(
    filters.command(["count", "cnt"]) & filters.user(Config.OWNER_ID) & filters.private
)
async def count_command(client: Client, message: Message):
    """Show chat history count with ETA calculation"""
    user_id = message.from_user.id

    # Admin check (already handled by filter, but keeping for clarity)
    if message.from_user.id != Config.OWNER_ID:
        await message.reply("❌ You are not authorized to use this command.")
        return

    # Check if there's an active forward operation
    if user_id in active_forwards:
        await message.reply(
            "⚠️ You have an active forward operation running. "
            "Use /stop to stop it first, then check chat count."
        )
        return

    try:
        # Initialize database for user if needed
        await db.init(user_id)

        # Get user settings from database
        settings = await db.get_user_settings(user_id)

        if (
            not settings
            or not settings.get("source_chat")
            or not settings.get("target_chat")
        ):
            await message.reply(
                "❌ **No settings found**\n\n"
                "You haven't configured your forwarder yet.\n"
                "Use `/set_ids source_chat target_chat` to get started.\n\n"
                "**Example:**\n"
                "`/set_ids @sourcechannel @targetchannel`\n"
                "`/set_ids -1001234567890 -1009876543210`"
            )
            return

        source_chat = settings.get("source_chat")
        target_chat = settings.get("target_chat")

        # Validate chat access
        try:
            chat_valid, faulty_ids = await conversation_handler.is_valid_chat(
                (source_chat,)
            )
            if not chat_valid:
                await message.reply(
                    f"❌ **Cannot access source chat**\n\n"
                    f"The source chat `{source_chat}` is not accessible.\n"
                    f"Please check:\n"
                    f"• Chat ID is correct\n"
                    f"• Bot has access to the chat\n"
                    f"• Chat still exists\n\n"
                    f"Use `/set_ids` to reconfigure your settings."
                )
                return
        except Exception as chat_error:
            logging.error(f"Error validating chat {source_chat}: {chat_error}")
            await message.reply(
                f"❌ **Error accessing chat**\n\n"
                f"Could not validate access to source chat `{source_chat}`.\n"
                f"Error: {str(chat_error)}\n\n"
                f"Please try again later or use `/set_ids` to reconfigure."
            )
            return

        # Send initial progress message
        progress_msg = await message.reply(
            "🔍 **Counting messages...**\n\nPlease wait while I analyze the chat history..."
        )

        # Initialize counters
        total_messages = 0
        media_groups_set = set()  # Track unique media group IDs
        valid_messages = 0
        skipped_messages = 0

        try:
            # Count messages in chat history
            async for msg in app.get_chat_history(source_chat):
                total_messages += 1

                # Skip invalid message types (same logic as forward command)
                if any(
                    [msg.service, msg.empty, msg.command, msg.has_protected_content]
                ):
                    skipped_messages += 1
                    continue

                # Count valid messages
                valid_messages += 1

                # Track media groups
                if msg.media_group_id:
                    media_groups_set.add(msg.media_group_id)

                # Update progress every 1000 messages
                if total_messages % 1000 == 0:
                    await progress_msg.edit_text(
                        f"🔍 **Counting messages...**\n\n"
                        f"📊 Processed: `{total_messages:,}` messages\n"
                        f"✅ Valid: `{valid_messages:,}`\n"
                        f"⏭️ Skipped: `{skipped_messages:,}`\n"
                        f"📑 Media Groups: `{len(media_groups_set):,}`\n\n"
                        f"⏳ Please wait..."
                    )

        except Exception as count_error:
            logging.error(f"Error counting messages in {source_chat}: {count_error}")
            await progress_msg.edit_text(
                f"❌ **Error counting messages**\n\n"
                f"An error occurred while counting messages in the source chat.\n"
                f"Error: {str(count_error)}\n\n"
                f"This might be due to:\n"
                f"• Network connectivity issues\n"
                f"• Chat access restrictions\n"
                f"• Telegram API limits\n\n"
                f"Please try again later."
            )
            return

        # Calculate ETA based on message counts and delays
        total_media_groups = len(media_groups_set)
        single_messages = valid_messages - sum(
            1 for _ in media_groups_set
        )  # Approximate

        # Calculate estimated time with delays
        # Each media group: DELAY_FOR_MEDIA_GROUPS (2 seconds)
        # Each single message: DELAY_FOR_SINGLE_MESSAGE (1 second)
        # Plus processing overhead per message (~0.1 seconds average)
        estimated_time = (
            (total_media_groups * DELAY_FOR_MEDIA_GROUPS)
            + (single_messages * DELAY_FOR_SINGLE_MESSAGE)
            + (valid_messages * 0.1)  # Processing overhead
        )

        # Format time
        def format_time(seconds: float) -> str:
            """Format time in H:M:S format."""
            if seconds < 0:
                return "0:00:00"

            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)

            return f"{hours}H:{minutes:02d}M:{secs:02d}S"

        # Get chat information for display
        try:
            chat_infos = await conversation_handler.get_chat_info(
                (source_chat, target_chat)
            )
            if len(chat_infos) >= 2:
                source_info = chat_infos[0]
                target_info = chat_infos[1]
                source_title = source_info.get("title", "Unknown")
                target_title = target_info.get("title", "Unknown")
            else:
                source_title = "Unknown"
                target_title = "Unknown"
        except Exception:
            source_title = "Unknown"
            target_title = "Unknown"

        # Format final response
        count_text = (
            f"📊 **Chat History Analysis**\n\n"
            f"📥 **Source Chat:** `{source_title}`\n"
            f"📤 **Target Chat:** `{target_title}`\n\n"
            f"📈 **Message Statistics:**\n"
            f"📋 **Total Messages:** `{total_messages:,}`\n"
            f"✅ **Valid for Forward:** `{valid_messages:,}`\n"
            f"⏭️ **Skipped (Invalid):** `{skipped_messages:,}`\n"
            f"📑 **Media Groups:** `{total_media_groups:,}`\n\n"
            f"⏱️ **Estimated Forward Time:**\n"
            f"🕒 **ETA:** `{format_time(estimated_time)}`\n\n"
            f"ℹ️ **Note:** ETA includes processing delays and rate limiting to prevent FloodWait errors.\n\n"
            f"**Ready to forward?** Use `/forward` to start!"
        )

        await progress_msg.edit_text(count_text)
        logging.info(
            f"Count command completed for user {user_id}: {valid_messages:,} valid messages, {total_media_groups:,} media groups"
        )

    except Exception as e:
        logging.error(f"Error in count command: {e}")
        await message.reply(
            "❌ **Count Error**\n\n"
            f"An error occurred while analyzing the chat history.\n"
            f"Error: {str(e)}\n\n"
            "Please try again later or check your settings with `/settings`."
        )


@app.on_message(
    filters.command(["settings", "st"])
    & filters.user(Config.OWNER_ID)
    & filters.private
)
async def settings_command(client: Client, message: Message):
    """Display user settings in a formatted way"""
    user_id = message.from_user.id

    # Admin check (already handled by filter, but keeping for clarity)
    if message.from_user.id != Config.OWNER_ID:
        await message.reply("❌ You are not authorized to use this command.")
        return

    # Check if there's an active forward operation
    if user_id in active_forwards:
        await message.reply(
            "⚠️ You have an active forward operation running. "
            "Use /stop to stop it first, then check your settings."
        )
        return

    try:
        # Initialize database for user if needed
        await db.init(user_id)

        # Get user settings from database
        settings = await db.get_user_settings(user_id)

        if (
            not settings
            or not settings.get("source_chat")
            or not settings.get("target_chat")
        ):
            await message.reply(
                "❌ **No settings found**\n\n"
                "You haven't configured your forwarder yet.\n"
                "Use `/set_ids source_chat target_chat` to get started.\n\n"
                "**Example:**\n"
                "`/set_ids @sourcechannel @targetchannel`\n"
                "`/set_ids -1001234567890 -1009876543210`"
            )
            return

        # Extract settings
        source_chat = settings.get("source_chat")
        target_chat = settings.get("target_chat")
        updated_at = settings.get("updated_at", "Unknown")

        # Get chat information
        try:
            chat_infos = await conversation_handler.get_chat_info(
                (source_chat, target_chat)
            )

            if len(chat_infos) >= 2:
                source_info = chat_infos[0]
                target_info = chat_infos[1]

                source_title = source_info.get("title", "Unknown")
                target_title = target_info.get("title", "Unknown")

                # Format the settings message
                settings_text = (
                    "⚙️ **Your Current Settings**\n\n"
                    f"📥 **Source Chat:**\n"
                    f"`{source_chat}` - {source_title}\n\n"
                    f"📤 **Target Chat:**\n"
                    f"`{target_chat}` - {target_title}\n\n"
                    f"🕒 **Last Updated:** {updated_at}\n\n"
                    f"**Commands:**\n"
                    f"• Use `/forward` to start forwarding\n"
                    f"• Use `/reset` to change settings\n"
                    f"• Use `/stats` to view operation statistics"
                )
            else:
                # Fallback if chat info retrieval fails
                settings_text = (
                    "⚙️ **Your Current Settings**\n\n"
                    f"📥 **Source Chat:** `{source_chat}`\n"
                    f"📤 **Target Chat:** `{target_chat}`\n\n"
                    f"🕒 **Last Updated:** {updated_at}\n\n"
                    f"⚠️ *Could not retrieve chat details*\n\n"
                    f"**Commands:**\n"
                    f"• Use `/forward` to start forwarding\n"
                    f"• Use `/reset` to change settings\n"
                    f"• Use `/stats` to view operation statistics"
                )

        except Exception as chat_error:
            logging.warning(f"Could not get chat info: {chat_error}")
            # Fallback message if chat info fails
            settings_text = (
                "⚙️ **Your Current Settings**\n\n"
                f"📥 **Source Chat:** `{source_chat}`\n"
                f"📤 **Target Chat:** `{target_chat}`\n\n"
                f"🕒 **Last Updated:** {updated_at}\n\n"
                f"⚠️ *Could not retrieve chat details*\n\n"
                f"**Commands:**\n"
                f"• Use `/forward` to start forwarding\n"
                f"• Use `/reset` to change settings\n"
                f"• Use `/stats` to view operation statistics"
            )

        await message.reply(settings_text)

    except Exception as e:
        logging.error(f"Error in settings command: {e}")
        await message.reply(
            "❌ An error occurred while retrieving your settings. "
            "Please try again later or use /reset to reconfigure."
        )


@app.on_message(
    filters.command(["reset", "rs"]) & filters.user(Config.OWNER_ID) & filters.private
)
async def reset_command(client: Client, message: Message):
    """Reset user settings and delete their data file"""
    user_id = message.from_user.id

    # Admin check (already handled by filter, but keeping for clarity)
    if message.from_user.id != Config.OWNER_ID:
        await message.reply("❌ You are not authorized to use this command.")
        return

    # Check if there's an active forward operation
    if user_id in active_forwards:
        await message.reply(
            "⚠️ You have an active forward operation running. "
            "Use /stop to stop it first, then try resetting your settings."
        )
        return

    try:
        # Initialize database for user if needed
        await db.init(user_id)

        # Check if user has any settings to reset
        settings = await db.get_user_settings(user_id)

        if not settings or (
            not settings.get("source_chat") and not settings.get("target_chat")
        ):
            await message.reply(
                "❌ **No settings found to reset**\n\n"
                "You don't have any configured settings yet.\n"
                "Use `/set_ids source_chat target_chat` to get started."
            )
            return

        # Notify user about reset with countdown
        reset_msg = await message.reply(
            "⚠️ **Database Reset Initiated**\n\n"
            "Your settings will be permanently deleted in **5 seconds**.\n"
            "This action cannot be undone.\n\n"
            "💾 Current settings that will be lost:\n"
            f"📥 Source: `{settings.get('source_chat', 'Not set')}`\n"
            f"📤 Target: `{settings.get('target_chat', 'Not set')}`\n\n"
            "⏳ Resetting in 5 seconds..."
        )

        # Wait for 5 seconds
        await asyncio.sleep(5)

        # Delete user settings
        delete_success = await db.delete_user_settings(user_id)

        if delete_success:
            await reset_msg.edit_text(
                "✅ **Settings Reset Complete**\n\n"
                "Your database has been successfully reset.\n"
                "All settings have been permanently deleted.\n\n"
                "🚀 **Next Steps:**\n"
                "• Use `/set_ids source_chat target_chat` to configure new settings\n"
                "• Use `/help` to see all available commands\n\n"
                "📋 A backup of your old settings has been created for safety."
            )
        else:
            await reset_msg.edit_text(
                "❌ **Reset Failed**\n\n"
                "An error occurred while resetting your settings.\n"
                "Your data may still be intact.\n\n"
                "Please try again later or contact support if the issue persists."
            )

    except Exception as e:
        err = logging.error(f"Error in reset command: {e}")
        err
        await message.reply(
            "❌ **Reset Error**\n\n"
            f"An error occurred while resetting your settings: {err}\n"
            "Your settings may still be intact.\n\n"
            "Please try again later or use `/settings` to check your current configuration."
        )


@app.on_message(
    filters.command(["set_ids", "set"])
    & filters.user(Config.OWNER_ID)
    & filters.private
)
async def set_ids_command(client: Client, message: Message):
    """Start the chat ID setup process"""
    user_id = message.from_user.id
    parts = message.text.strip().split()

    if message.from_user.id != Config.OWNER_ID:
        await message.reply("❌ You are not authorized to use this command.")
        return

    await db.init(user_id)  # Initialize database for the user

    if len(parts) < 3:
        await message.reply(
            "❌ Invalid command format.\nUse `/set_ids source_id target_id`\n"
            "**SOURCE_CHAT:** The chat ID or username of the source chat.\n"
            "**TARGET_CHAT:** The chat ID or username of the destination chat.\n"
        )
        return

    source_chat_id = parts[1].strip()
    target_chat_id = parts[2].strip()
    extra_flags = {flag.lower() for flag in parts[3:]}

    existing_settings = await db.get_user_settings(user_id) or {}
    has_active_configuration = bool(
        existing_settings.get("source_chat") and existing_settings.get("target_chat")
    )
    force_overwrite = bool(
        extra_flags & {"--force", "-f", "force", "overwrite", "--overwrite"}
    )

    if has_active_configuration and not force_overwrite:
        await message.reply(
            "⚠️ A configuration already exists.\n"
            "Re-run the command with `--force` to overwrite, or use /reset first."
        )
        return

    try:
        # Validate chat IDs
        valid_check, faulty_id = await conversation_handler.is_valid_chat(
            (source_chat_id, target_chat_id)
        )
        if not valid_check:
            await message.reply(
                "❌ Invalid chat ID. Please make sure:\n"
                "1. The chat ID/username is correct\n"
                "2. You have access to the chat\n"
                f"Invalid chat IDs: {', '.join(faulty_id)}"
            )
            return
        else:
            await message.reply(
                "✅ Valid chat IDs. Proceeding to {}settings...".format(
                    "update " if has_active_configuration else "save "
                )
            )
        # Save settings
        await db.set_user_chats(user_id, source_chat_id, target_chat_id)
        source_info, target_info = await conversation_handler.get_chat_info(
            (source_chat_id, target_chat_id)
        )
        await message.reply(
            f"✅ Source and target chats set successfully:\n"
            f"Source: `{source_chat_id}` {source_info.get('title', 'Unknown')} \n"
            f"Target: `{target_chat_id}` {target_info.get('title', 'Unknown')}\n\n"
            f"Use /st (or /settings) to see your settings.\nUse /f (or /forward) to start forwarding files.\n"
            f"Use /rs (or /reset) to reset your settings.\n"
        )

    except Exception as e:
        logging.error(f"Error in set_ids command: {e}")
        await message.reply(
            "❌ An error occurred while validating chat IDs. Please try again later."
        )


# ------------- Forward Implementation ------------- #

# Common video extensions to check against
VIDEO_EXTENSIONS = (
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
)


def _is_forwardable(message: Message) -> bool:
    """Return True when a message is safe to forward."""
    # Basic checks
    if any(
        [message.service, message.empty, message.command, message.has_protected_content]
    ):
        return False

    # Media only mode check
    if Config.MEDIA_ONLY_MODE:
        is_valid_video = False

        # Check video objects
        if message.video and message.video.file_name:
            if message.video.file_name.lower().endswith(VIDEO_EXTENSIONS):
                is_valid_video = True

        # Check document objects that might be videos
        elif message.document and message.document.file_name:
            if message.document.file_name.lower().endswith(VIDEO_EXTENSIONS):
                is_valid_video = True

        if not is_valid_video:
            return False

    return True


async def forward_media_group(
    client: Client,
    media_group: List[Message],
    target_chat: str,
    source_chat: str | int = None,
    dry_run: bool = False,
) -> bool:
    """Forward a media group with retry handling."""

    if dry_run:
        logging.info(
            "Dry-run: would forward media group %s with %s messages to %s",
            media_group[0].id,
            len(media_group),
            target_chat,
        )
        return True

    async def _copy_media_group() -> None:
        await client.copy_media_group(
            chat_id=target_chat,
            from_chat_id=source_chat,
            message_id=media_group[0].id,
        )

    try:
        await retry_handler.retry_with_backoff(_copy_media_group)
        return True
    except Exception as e:
        logging.error(f"Error forwarding media group {media_group[0].id}: {e}")
        return False


async def forward_message(
    client: Client, message: Message, target_chat: str, *, dry_run: bool = False
) -> bool:
    """Forward a single message with retry handling."""

    if dry_run:
        logging.info(
            "Dry-run: would forward message %s from %s to %s",
            message.id,
            message.chat.id if message.chat else "unknown",
            target_chat,
        )
        return True

    async def _copy_message() -> None:
        await client.copy_message(
            chat_id=target_chat,
            from_chat_id=message.chat.id,
            message_id=message.id,
            disable_notification=True,
        )

    try:
        await retry_handler.retry_with_backoff(_copy_message)
        return True
    except Exception as e:
        logging.error(f"Error forwarding {message.id}: {e}")
        return False


async def update_progress(
    message: Message,
    stats: ForwardStats,
    update_interval: int = 5,
    completion_event: asyncio.Event | None = None,
) -> None:
    """Update progress message periodically."""
    last_update = 0
    while True:
        if completion_event and completion_event.is_set():
            break

        current_time = time.time()
        if current_time - last_update >= update_interval:
            await message.edit_text(stats.format_progress())
            last_update = current_time
        await asyncio.sleep(1)


@app.on_message(
    filters.command(["f", "forward", "fwd"])
    & filters.user(Config.OWNER_ID)
    & filters.private
)
async def forward_command(client: Client, message: Message):
    """Handle forward command with improved error handling and progress tracking."""
    user_id = message.from_user.id

    # Check if forward already in progress
    if user_id in active_forwards:
        await message.reply(
            "⚠️ You already have an active forward operation. Use /stop first."
        )
        return

    # Initialize components
    settings = await db.get_user_settings(user_id)
    if not settings:
        await message.reply(
            "❌ No settings found. Use /set_ids to configure your forward settings first."
        )
        return

    command_text = message.text or ""
    command_args = [part.lower() for part in command_text.split()[1:]]
    dry_run = DRY_RUN_DEFAULT or any(
        flag in {"--dry-run", "-n", "dry", "--dry"} for flag in command_args
    )

    source_chat = settings["source_chat"]
    target_chat = settings["target_chat"]
    start_text = "⏳ Starting forward operation..."
    if dry_run:
        start_text += "\n\n(Dry-run mode: no messages will be sent.)"
    progress_msg = await message.reply(start_text)
    logging.info(
        f"Starting forward operation from {source_chat} to {target_chat} for user {user_id}"
    )
    if dry_run:
        logging.info(
            "Forward command running in dry-run mode; no messages will be sent."
        )

    # Initialize stats and collectors
    media_collector = MediaGroupCollector(flush_window=MEDIA_GROUP_FLUSH_SECONDS)
    stats = ForwardStats()
    forward_stats[user_id] = stats

    try:
        # Initialize message queue
        queue = MessageQueue()
        active_forwards[user_id] = queue
        forward_complete = asyncio.Event()

        # Start progress updates
        task_scheduler = asyncio.create_task(
            update_progress(progress_msg, stats, completion_event=forward_complete)
        )
        counting_text = "📥 Counting messages before forwarding..."
        if dry_run:
            counting_text += "\n\n(Dry-run mode in effect.)"
        await progress_msg.edit_text(counting_text)

        async def _fetch_batch(chat_id: str, offset: int) -> List[Message]:
            history = app.get_chat_history(chat_id, offset_id=offset, limit=BATCH_SIZE)
            return [msg async for msg in history]

        async def _process_media_groups(groups: List[List[Message]]) -> None:
            for group in groups:
                if not queue._active or user_id not in active_forwards:
                    logging.info(f"Forward operation stopped by user {user_id}")
                    return

                if len(group) > 1:
                    try:
                        if await forward_media_group(
                            client, group, target_chat, source_chat, dry_run=dry_run
                        ):
                            stats.processed += len(group)
                            stats.media_groups += 1
                            logging.info(
                                f"Forwarded media group of {len(group)} messages."
                            )
                            if not dry_run:
                                await asyncio.sleep(DELAY_FOR_MEDIA_GROUPS)
                        else:
                            stats.failed += len(group)
                    except FloodWait as e:
                        logging.warning(
                            "FloodWait while processing media group %s: sleeping for %s seconds",
                            group[0].id,
                            e.value + 1,
                        )
                        await asyncio.sleep(e.value + 1)
                    except Exception as exc:
                        logging.error(f"Error processing media group: {exc}")
                        stats.failed += len(group)
                else:
                    single = group[0]
                    try:
                        if await forward_message(
                            client, single, target_chat, dry_run=dry_run
                        ):
                            stats.processed += 1
                            logging.info(
                                f"Forwarded single media group message {single.id}."
                            )
                            if not dry_run:
                                await asyncio.sleep(DELAY_FOR_SINGLE_MESSAGE)
                        else:
                            stats.failed += 1
                    except FloodWait as e:
                        logging.warning(
                            "FloodWait while processing message %s: sleeping for %s seconds",
                            single.id,
                            e.value + 1,
                        )
                        await asyncio.sleep(e.value + 1)
                    except Exception as exc:
                        logging.error(f"Error processing message {single.id}: {exc}")
                        stats.failed += 1

        total_forwardable = 0
        offset_id = 0

        # First pass: count forwardable messages without retaining them
        while True:
            if not queue._active:
                logging.info(
                    f"Forward operation stopped during counting for user {user_id}"
                )
                break

            batch = await _fetch_batch(source_chat, offset_id)
            if not batch:
                break

            offset_id = batch[-1].id
            total_forwardable += sum(1 for msg in batch if _is_forwardable(msg))

        stats.total = total_forwardable
        stats.skipped = 0

        if not queue._active:
            task_scheduler.cancel()
            queue.stop()
            del active_forwards[user_id]
            await progress_msg.edit_text(
                "⚠️ Forward operation stopped during preparation."
            )
            return

        if stats.total == 0:
            await progress_msg.edit_text(
                "❌ No valid messages found to forward.\n"
                "All messages were either service messages, empty, commands, or protected content."
            )
            task_scheduler.cancel()
            queue.stop()
            del active_forwards[user_id]
            return

        forward_text = "📤 Forwarding messages... (streaming mode)"
        if dry_run:
            forward_text += " [dry-run]"
        await progress_msg.edit_text(forward_text)

        # Reset offset for streaming pass
        offset_id = 0

        # Second pass: stream messages in chronological order using bounded batches
        while True:
            batch = await _fetch_batch(source_chat, offset_id)
            if not batch or not queue._active:
                break

            offset_id = batch[-1].id

            for msg in reversed(batch):
                if not queue._active:
                    break

                current_time = msg.date or datetime.utcnow()

                await _process_media_groups(
                    media_collector.get_ready_groups(current_time)
                )

                if not queue._active:
                    break

                if not _is_forwardable(msg):
                    stats.skipped += 1
                    continue

                if msg.media_group_id:
                    media_collector.add_message(msg)
                    await _process_media_groups(
                        media_collector.get_ready_groups(current_time)
                    )
                    if not queue._active:
                        break
                    continue

                try:
                    if await forward_message(client, msg, target_chat, dry_run=dry_run):
                        stats.processed += 1
                        logging.info(f"Forwarded message {msg.id} from {source_chat}.")
                        if not dry_run:
                            await asyncio.sleep(DELAY_FOR_SINGLE_MESSAGE)
                    else:
                        stats.failed += 1
                except FloodWait as e:
                    logging.warning(
                        f"FloodWait encountered while processing message {msg.id}: sleeping for {e.value + 1} seconds"
                    )
                    await asyncio.sleep(e.value + 1)
                except Exception as e:
                    logging.error(f"Error processing message {msg.id}: {e}")
                    stats.failed += 1

        # Flush any remaining media groups or single-message groups
        await _process_media_groups(media_collector.drain_all())

        operation_cancelled = (not queue._active) or (user_id not in active_forwards)

        if operation_cancelled:
            logging.info(f"Forward operation cancelled for user {user_id}.")
            try:
                await progress_msg.edit_text(
                    f"⚠️ Forward operation stopped.\n\n{stats.format_progress()}"
                )
            except Exception:
                pass
        else:
            completion = "**✅ Forward operation completed!**"
            if dry_run:
                completion += " (dry-run)"
            await progress_msg.edit_text(f"{completion}\n\n{stats.format_progress()}")
            logging.info(f"Forward operation completed for user {user_id}: ")
            logging.info(
                "Forward complete summary: processed=%s failed=%s skipped=%s media_groups=%s",
                stats.processed,
                stats.failed,
                stats.skipped,
                stats.media_groups,
            )
            forward_complete.set()
    except FloodWait as e:
        logging.warning(
            f"FloodWait encountered during forward operation: sleeping for {e.value + 1} seconds"
        )
        await asyncio.sleep(e.value + 1)
        await progress_msg.edit_text(
            f"⚠️ FloodWait encountered. Please wait for {e.value + 1} seconds before retrying the operation."
        )
    except Exception as e:
        logging.error(f"Error in forward operation: {e}")
        await progress_msg.edit_text(
            "❌ An error occurred during the forward operation.\n"
            "Please check the logs for details."
        )
    finally:
        forward_complete.set()
        try:
            task_scheduler.cancel()
        except Exception:
            pass

        if user_id in active_forwards:
            active_forwards[user_id].stop()
            del active_forwards[user_id]

        queue.stop()


# ------------- Utility Functions ------------- #


async def check_owner_id(app: Client, message: Message) -> bool:
    """Check if Owner ID is set in the environment variables."""
    if not Config.OWNER_ID or len(str(Config.OWNER_ID)) == 0 or Config.OWNER_ID == 0:
        await message.reply(
            "❌ Owner ID is not set in the environment variable (.env). "
            "Please set it and restart the bot."
        )
        return False
    return True


if __name__ == "__main__":
    app.run()
