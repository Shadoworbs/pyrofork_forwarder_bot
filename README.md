# Telegram Forwarder Bot

A sophisticated Telegram bot built with Pyrofork that allows owners to forward media files between chats with advanced features and robust error handling.

## Features

- 🚀 **Fast & Efficient**: Built with Pyrofork for optimal performance
- 💾 **Persistent Storage**: User-specific JSON file storage
- 🎯 **Multiple Chat Support**: Forward between any accessible chats
- 📊 **Progress Tracking**: Real-time forwarding progress updates
- 🔒 **Owner-Only Access**: Secure access control
- 📱 **Media Group Support**: Preserves media groups while forwarding
- ⚙️ **User Settings Management**: Easy-to-use settings menu
- 🔄 **Batch Processing**: Handles large forwards efficiently
- 🛡️ **Error Handling**: Robust error recovery and graceful degradation
- 🧹 **Auto Cleanup**: Automatic cleanup of stale confirmations
- 🎛️ **Command System**: Intuitive command interface

## Commands

- `/start` - Start the bot and view welcome message
- `/help` - Show available commands and help
- `/set_ids` (or `/set`) - Set source and target chat IDs directly
- `/settings` (or `/st`) - View your current settings
- `/forward` (or `/f`, `/fwd`) - Start forwarding files with progress tracking
- `/rs` (or `/reset`) - Reset all your settings

Note: All commands are owner-only and work only in private chats.

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- Telegram API credentials (api_id and api_hash) get them from [Telegram App Configuration](https://app.telegram.org)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/telegram-forwarder-bot.git
   cd telegram-forwarder-bot
   ```

2. Install required packages:

   - #### For Linux

   ```bash
   pip install -r requirements-l.txt
   ```

   - #### For Windows

   ```bash
   pip install -r requirements-w.txt
   ```

3. Create and configure environment variables:
   - Rename `environ.env` to `.env`
   - Add your Telegram API credentials:

   ```env
   API_ID = "your_api_id"
   API_HASH = "your_api_hash"
   OWNER_USERNAME = "@your_telegram_username"
   ```

### Running the Bot

1. Start the bot:

   ```bash
   python forwarder.py
   ```

2. Set up your forward configuration:
   - Use `/set_ids` to configure source and target chats
   - Use `/settings` to verify your configuration
   - Use `/forward` to start forwarding

   ## Project Structure

   ``` md
   ├── bot/
   │   ├── configs.py         # Configuration management
   │   ├── conversation.py    # Conversation handler
   │   ├── database.py       # Database operations
   │   └── settings_manager.py # Settings management
   ├── forwarder.py          # Main bot file
   ├── requirements.txt      # Dependencies
   └── .env                 # Environment variables
   ```

## Error Handling

The bot includes comprehensive error handling:

- FloodWait protection
- Invalid chat ID handling
- Database operation error recovery
- Message deletion error handling
- Connection error recovery

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Pyrofork](https://github.com/Mayuri-Chan/pyrofork)
- Uses [Rich](https://github.com/Textualize/rich) for beautiful console output
- SQLite for efficient data storage

## Safety Notes

- Never share your `api_id` and `api_hash`
- Keep your `.env` file secure
- Don't commit sensitive information to git
- Use `.gitignore` to prevent accidental uploads

## Contact

For support or inquiries, contact [@shadoworbs](https://t.me/shadoworbs) on Telegram.
