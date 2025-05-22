# How to setup>>>
#
# 1. Rename environ.env to .env and update the values API_ID, API_HASH, and OWNER_ID.
#
#
import logging
import asyncio
from pyrogram.errors import FloodWait
from pyrogram import Client, filters
from pyrogram.types import Message
from rich.console import Console
from bot.configs import Config
from bot.database import Database
from bot.conversation import ConversationHandler
from bot.settings_manager import SettingsManager


# Configure logging
logging.basicConfig(
    # filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)

## --------------------
api_id = Config.API_ID
api_hash = Config.API_HASH


# Initialize components
console = Console()
db = Database("user_data")  # Initialize with user_data directory
active_forwards = set()  # Track active forward operations
reset_confirmations = {}  # Track reset confirmations

# Initialize client with optimized settings
app = Client("my_account", api_id=api_id, api_hash=api_hash)

# Initialize handlers
conversation_handler = ConversationHandler(app, db)
settings_manager = SettingsManager(app, db)


# ------------- Start Bot ------------- #
@app.on_message(
    filters.command("start") 
    & filters.user(Config.OWNER_ID) 
    & filters.private
)
async def start_command(client: Client, message: Message):
    """Handle start command"""

    start_text = """
Hi, welcome to the Best Forwarder Bot! 🤖\n
I can forward all your chat history from one chat to another including files, videos, text and more!\n
I can also forward media groups as they are without splitting them into individual messages.\n
Use /help to see available commands."""
    await message.reply(start_text, disable_web_page_preview=True)


#
@app.on_message(
    filters.command("help") 
    & filters.user(Config.OWNER_ID) 
    & filters.private
)
async def help_command(client: Client, message: Message):
    """Handle help command"""
    help_text = """
Here are the available commands:\n
/start - Start the bot\n
/set_ids (or /set) source_chat_id target_chat_id - Set the source and target chat IDs for forwarding.\n
/forward (or /f) - Start forwarding files from the source chat to the target chat.\n
/settings - View your current settings\n
/rs (or /reset) - Reset your settings and start over.\n
"""


# ------------- Set IDs Command ------------- #
@app.on_message(
    filters.command(["set_ids", "set"])
    & filters.user(Config.OWNER_ID)
    & filters.private
)
async def set_ids_command(client: Client, message: Message):
    """Start the chat ID setup process"""

    user_id = message.from_user.id
    ids = message.text.strip().split(" ")

    if message.from_user.id != Config.OWNER_ID:
        await message.reply("❌ You are not authorized to use this command.")
        return

    await db.init(user_id)  # Initialize database for the user

    if not len(ids) == 3:
        await message.reply(
            "❌ Invalid command format.\nUse `/set_ids source_id target_id`\n"
            "**SOURCE_CHAT:** The chat ID or username of the source chat (where to copy from).\n"
            "**TARGET_CHAT:** The chat ID or username of the destination chat (where to send all the copied items to).\n",
        )
        return
    source_chat_id = ids[1].strip()
    target_chat_id = ids[2].strip()
    if await db.get_user_settings(user_id):
        await message.reply(
            "⚠️ You already have a configuration.\nUse /settings to view or /reset to change it."
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

    except Exception as e:
        logging.error(f"Error in set_ids command: {e}")
        await message.reply(
            "❌ An error occurred while validating chat IDs. Please try again later."
        )

    # Save settings
    await db.set_user_chats(user_id, source_chat_id, target_chat_id)
    await message.reply(
        f"✅ Source and target chats set successfully:\n"
        f"Source: `{source_chat_id}`\n"
        f"Target: `{target_chat_id}`\n\n"
        f"Use /forward to start forwarding files."
    )


# ------------- Settings Command ------------- #
@app.on_message(
    filters.command(["settings", "st"])
    & filters.user(Config.OWNER_ID)
    & filters.private
)
async def settings_command(client: Client, message: Message):
    """Show settings menu"""
    await settings_manager.show_settings(message)


# --------- Exit if User ID is not set in .env --------- #
async def check_owner_id(app: Client, message: Message):
    """Check if Owner ID is set in the environment variables"""
    if not Config.OWNER_ID or len(str(Config.OWNER_ID)) == 0 or Config.OWNER_ID == 0:
        return False
    return True


# --------- Forward Command --------- #
@app.on_message(
    filters.command(["f", "forward", "fwd"])
    & filters.user(Config.OWNER_ID)
    & filters.private
)
async def forward_command(client: Client, message: Message):
    """Handle forward command"""
    user_id = message.from_user.id

    # exit the bot if owner id is not set in the environment variable
    if not await check_owner_id(client, message):
        await message.reply(
            "❌ Owner ID is not set in the environment variable (.env). Please set it and restart the bot."
        )
        raise ValueError(
            "Owner ID is not set in the environment variable (.env). Please set it and restart the bot."
        )

    if user_id in active_forwards:
        await message.reply(
            "⚠️ You already have an active forward operation. Use /stop first."
        )
        return

    # Get user settings
    settings = await db.get_user_settings(user_id)
    if not settings:
        await message.reply(
            "❌ No settings found. Use /set_ids to configure your forward settings first."
        )
        return

    source_chat = settings["source_chat"]
    target_chat = settings["target_chat"]

    try:
        active_forwards.add(user_id)
        # await message.delete()
        progress_msg = await message.reply("🔄 Starting forward operation...")

        console.log("Starting filtering process...")

        msg_count = 0
        batch = []
        index = 0
        failed_skipped = 0

        # Process messages
        async for message in app.get_chat_history(chat_id=source_chat):
            # with open("ids.txt", "a") as f:
            #     f.write(f"{message.id}\n")
            if user_id not in active_forwards:
                await client.send_message(
                    user_id, "⚠️ Forward operation stopped by user."
                )
                break
            if (message.service
                or message.has_protected_content
                or message.command
                or message.empty
                ):
                failed_skipped += 1
                console.log(
                    f"[red]Skipped {1 + failed_skipped} message(s): {message.id} - {message.text}[/red]"
                )
                continue
            elif message.forward_from_chat:
                try:
                    if message.forward_from_chat.is_restricted:
                        failed_skipped += 1
                        console.log(
                            f"[red]Skipped {1 + failed_skipped} message(s): {message.id} - {message.text}[/red]"
                        )
                        continue
                except Exception as e:
                    console.log(
                        f"[red]Error checking forward_from_chat: {e}[/red]"
                    )
                    failed_skipped += 1
                    continue

            batch.append(message)
            msg_count += 1

        while index < len(batch):
            if len(batch) == 0:
                await progress_msg.edit("No messages to forward.")
                console.log(
                    "[red]No messages to forward. Please check your source chat.[/red]"
                )
                active_forwards.discard(user_id)
                break
            if len(batch) < 100:
                messages_to_send = batch[::-1][index:]

            messages_to_send = batch[::-1][index : index + 100]
            # progress.update(task, description="Forwarding batch of files...")
            console.log(
                f"[green]Forwarding batch of {len(messages_to_send)} files...[/green]"
            )
            await forward_files(
                client,
                messages_to_send,
                source_chat,
                target_chat,
                message,
                total_msgs=msg_count,
                failed_skipped=failed_skipped,
            )
            await progress_msg.edit(f"Forwarding {index} of {msg_count} files...")
            await asyncio.sleep(2)
            index += 100
            percentage = round((index + 100) / len(batch) * 100, 2)
            await progress_msg.edit(
                f"Forwarding {len(batch)} of {msg_count} files... {percentage}%"
            )

        # Finalize progress
        console.log(
            f"[green]Forwarding complete. {msg_count:,} messages forwarded![/green]"
        )
        await progress_msg.delete()
        await app.send_message(
            target_chat,
            f"**✅ Forwarding complete:**\n\n"
            f"**Messages forwarded: {msg_count - failed_skipped:,}**\n"
            f"**Failed/Skipped messages: {failed_skipped:,}**\n\n",
        )
        console.log(
            f"[green]Forwarding complete. {msg_count:,} messages forwarded![/green]"
        )

    except Exception as e:
        active_forwards.discard(user_id)
        await progress_msg.delete()
        console.log(f"[red]Error occurred: {e}[/red]")
        logging.error(f"Error filtering messages: {e}")
        await app.send_message(
            user_id, f"An error occurred. Please try again later.\n{e}"
        )
    finally:
        active_forwards.discard(user_id)


async def forward_files(
    client: Client,
    messages_to_send: list[Message],
    source_chat,
    target_chat,
    message: Message,
    total_msgs=0,
):
    """Forward a batch of files"""
    copy_count = 0
    sent_ids = set()
    for msg in messages_to_send:

        if msg.id in sent_ids:
            continue
        try:
            if msg.media_group_id:
                media_group: list[Message] = await app.get_media_group(
                    source_chat, msg.id
                )
                await app.copy_media_group(
                    chat_id=target_chat, from_chat_id=source_chat, message_id=msg.id
                )
                copy_count += len(media_group)
                bundle_ids = [i.id for i in media_group]
                for i in bundle_ids:
                    sent_ids.add(i)
                console.log(
                    f"[green]Copied: {copy_count} of {total_msgs:,} file(s) [/green]"
                )
                await asyncio.sleep(0.5)
                # progress.update("Progress", advance=copy_count)
            else:
                await app.copy_message(
                    chat_id=target_chat,
                    from_chat_id=source_chat,
                    message_id=msg.id,
                    disable_notification=True,
                )
                copy_count += 1
                sent_ids.add(msg.id)
                console.log(
                    f"[green]Copied: {copy_count} of {len(messages_to_send)} file(s) [/green]"
                )
                await asyncio.sleep(0.5)
                # progress.update("Progress", advance=copy_count)
        except Exception as e:
            console.log(f"[red]Error forwarding file {copy_count}: {e}[/red]")
        except FloodWait as e:
            console.log(f"[red]Flood wait error: sleeping for {e.value} seconds[/red]")
            await asyncio.sleep(e.value + 0.3)


# --------- Reset Settings Command --------- #


@app.on_message(filters.command(["rs", "reset"]) & filters.user(Config.OWNER_ID) & filters.private)
async def reset_settings_command(client: Client, message: Message):
    """Handle reset settings command"""
    user_id = str(message.from_user.id)
    await db.init(user_id)  # Initialize database for the user
    try:
        if message.from_user.id == Config.OWNER_ID:
            # Check if user is the owner
            await message.reply("All your settings will be reset in 5 seconds.")
            await asyncio.sleep(5)
        await db.reset_user_settings(user_id)

    except Exception as e:
        logging.error(f"Error in reset command: {e}")
        await message.reply("❌ An error occurred. Please try again later.")


if __name__ == "__main__":
    print("Starting bot...")
    app.run()
