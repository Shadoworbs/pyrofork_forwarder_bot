# Telegram Forwarder Bot

A sophisticated Telegram bot built with PyroFork that allows owners to forward messages and media between chats with advanced features, comprehensive error handling, and intelligent media group preservation.

## Qucick Links

- [Features](#-features)
- [Commands](#-commands)
- [Setup Instructions](#setup-instructions)
- [Installation](#installation)
- [Running the Bot](#running-the-bot)
- [Project Structure](#project-structure)
- [Database Management](#database-management)
- [Technical Features](#technical-features)
- [Error Handling & Reliability](#error-handling--reliability)
- [Contributing](#contributing)

## 🚀 Features

### Core Features

- **⚡ Fast & Efficient**: Built with PyroFork for optimal performance and reliability
- **💾 Persistent Storage**: Thread-safe JSON database with automatic backups and corruption recovery
- **🎯 Multiple Chat Support**: Forward between any accessible chats (groups, channels, private)
- **📊 Real-time Progress Tracking**: Live updates with detailed statistics and processing rates
- **🔒 Owner-Only Access**: Secure access control with comprehensive permission checks
- **📱 Smart Media Group Support**: Preserves albums and media groups as complete units
- **🏗️ Chronological Order**: Messages forwarded in correct chronological sequence (oldest first)

### Advanced Features

- **⚙️ Comprehensive Settings Management**: View, edit, and reset configuration with chat details
- **🔄 Intelligent Batch Processing**: Handles large message volumes efficiently with memory optimization  
- **🛡️ Robust Error Handling**: Exponential backoff, FloodWait management, and graceful recovery
- **🧹 Automatic Cleanup**: Smart cleanup of temporary data and corrupted files with backup system
- **🎛️ Intuitive Command System**: User-friendly commands with comprehensive validation
- **📈 Detailed Statistics**: Track processed, failed, skipped messages and media groups with rates
- **🔄 Queue Management**: Active operation tracking with stop/resume capabilities
- **⚠️ Rate Limiting**: Built-in delays to prevent API rate limits and account restrictions
- **🔐 Data Safety**: Automatic backups before operations with recovery mechanisms

## 📱 Commands

### Core Commands

- `/start` - Start the bot and view welcome message
- `/help` - Show available commands and detailed feature list
- `/set_ids` (or `/set`) - Set source and target chat IDs with validation
- `/forward` (or `/f`, `/fwd`) - Start forwarding with progress tracking
- `/stop` - Stop ongoing forward operation gracefully

### Management Commands

- `/settings` (or `/st`) - View current settings with chat details and timestamps
- `/stats` - View detailed statistics of current/last forward operation
- `/count` (or `/cnt`) - Show chat history statistics with ETA for forwarding
- `/reset` (or `/rs`) - Reset all settings with 5-second confirmation countdown

**Note**: All commands are owner-only and work exclusively in private chats for security.

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- Telegram API credentials (api_id and api_hash) get them from [Telegram App Configuration](https://app.telegram.org)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/Shadoworbs/pyrofork_forwarder_bot.git && cd pyrofork_forwarder_bot
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
   OWNER_ID = "your telegram ID (not username)"
   DELAY_FOR_SINGLE_MESSAGE = 1 # Delay (in seconds) after each copy operation to prevent FloodWait (increase only if you get FloodWait errors)
   DELAY_FOR_MEDIA_GROUPS = 2 # Delay (in seconds) for media groups
   ```

### Running the Bot

#### Option 1: Manual Execution

1. First, run the login process:

   ```bash
      python login.py
   ```

2. Then start the bot:

   ```bash
      python forwarder.py
   ```

#### Option 2: Automated Startup (Recommended)

1. Use the provided startup script:

   On Linux:

   ```bash
   chmod +x start.sh  # Make executable (Linux)
   ./start.sh
   ```

   On Windows:

   ```bash
      bash start.sh
   ```

#### Option 3: Docker Deployment

1. Build the Docker image:

   ```bash
   docker build -t telegram-forwarder .
   ```

2. Run the container:

   ```bash
   docker run -d --name forwarder-bot -v $(pwd)/user_data:/app/user_data telegram-forwarder
   ```

3. Set up your forward configuration:
   - Use `/set_ids source_id target_id` to configure source and target chats
   - Use `/settings` to verify your configuration
   - Use `/forward` to start forwarding

## Project Structure

   ```plaintext
   pyrofork_forwarder_bot/
   ├── bot/
   │   ├── __init__.py
   │   ├── configs.py         # Configuration management
   │   ├── database.py        # Thread-safe database operations with backups
   │   ├── helper.py          # Chat validation and utility functions
   │   ├── settings_manager.py # Settings management
   │   └── utils.py           # Utility classes (RetryHandler, ForwardStats, etc.)
   ├── user_data/             # Database storage directory (auto-created)
   ├── forwarder.py           # Main bot application
   ├── login.py               # Telegram authentication script
   ├── start.sh               # Automated startup script
   ├── Dockerfile             # Docker configuration
   ├── requirements-l.txt     # Linux dependencies
   ├── requirements-w.txt     # Windows dependencies
   ├── environ.env            # Environment template
   └── README.md              # Project documentation
   ```

## Database Management

The bot includes a sophisticated database system with:

- **Thread-safe Operations**: Async locks prevent data corruption
- **Automatic Backups**: Creates backups before major operations
- **Corruption Recovery**: Restores from backups if database corruption is detected
- **Data Persistence**: User settings are preserved across restarts
- **Safe Reset**: 5-second countdown protection for data deletion

## Technical Features

### Message Processing

- **Chronological Ordering**: Two-phase collection and reversal ensures oldest-first forwarding
- **Media Group Preservation**: Albums forwarded as complete units without splitting
- **Batch Processing**: Efficient memory usage for large message volumes
- **Progress Tracking**: Real-time statistics with processing rates and ETA

### Error Recovery

- **Retry Handler**: Exponential backoff with configurable maximum attempts
- **FloodWait Management**: Intelligent delays to respect Telegram rate limits
- **Queue Management**: Active operation tracking with graceful stop/resume
- **Connection Resilience**: Automatic reconnection on network interruptions

### Performance Optimizations

- **Memory Management**: Efficient batch processing to handle large chat histories
- **Rate Limiting**: Built-in delays prevent API restrictions
- **Async Operations**: Non-blocking database and network operations
- **Resource Cleanup**: Automatic cleanup of temporary data and handles

## Error Handling & Reliability

The bot includes comprehensive error handling with:

- **FloodWait Protection**: Exponential backoff for API rate limits
- **Invalid Chat ID Handling**: Validates and normalizes chat identifiers
- **Database Operation Recovery**: Automatic backup restoration on corruption
- **Message Processing Errors**: Graceful handling of failed message operations
- **Connection Error Recovery**: Automatic reconnection on network issues
- **Memory Management**: Efficient batch processing to prevent memory overloads

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
