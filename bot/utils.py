"""Utility functions and classes for the forwarder bot."""

import asyncio
import logging
from typing import Optional, Any, Dict, List
from datetime import datetime
from pyrogram.errors import FloodWait
from rich.console import Console

console = Console()


class RetryHandler:
    """Handles retrying operations with exponential backoff."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """Execute a function with exponential backoff retry."""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                return await func(*args, **kwargs)
            except FloodWait as e:
                delay = e.value * (2**retry_count)
                console.log(f"[yellow]FloodWait: Sleeping for {delay} seconds[/yellow]")
                await asyncio.sleep(delay)
                retry_count += 1
            except Exception as e:
                if retry_count == self.max_retries - 1:
                    raise
                delay = self.base_delay * (2**retry_count)
                console.log(f"[red]Error: {str(e)}. Retrying in {delay} seconds[/red]")
                await asyncio.sleep(delay)
                retry_count += 1
        raise Exception(f"Failed after {self.max_retries} retries")


class ForwardStats:
    """Tracks statistics for forward operations."""

    def __init__(self):
        self.start_time = datetime.now()
        self.processed = 0
        self.failed = 0
        self.skipped = 0
        self.media_groups = 0
        self.total = 0
        self.percentage = 0.0
        self.total_delays = 0.0  # Track total sleep time for ETA calculation    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.percentage = (self.processed / self.total * 100) if self.total > 0 else 0.0

        # Calculate ETA based on remaining messages and expected delays
        remaining = self.total - self.processed
        if self.processed > 0 and remaining > 0:
            # Calculate average time per message based on actual elapsed time
            # This includes all delays: COPY_DELAY_SECONDS (0.85s), processing delays (0.7s),
            # rate limiting (0.5s), and any retry/error handling delays
            avg_time_per_message = elapsed / self.processed
            eta_seconds = remaining * avg_time_per_message
        else:
            eta_seconds = 0

        return {
            "processed": self.processed,
            "failed": self.failed,
            "skipped": self.skipped,
            "media_groups": self.media_groups,
            "total": self.total,
            "elapsed": elapsed,
            "eta": eta_seconds,
            "percentage": self.percentage,
        }

    def format_time(self, seconds: float) -> str:
        """Format time in H:M:S format."""
        if seconds < 0:
            return "0:00:00"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        return f"{hours}:{minutes:02d}:{secs:02d}"

    def format_progress(self) -> str:
        """Format progress message."""
        stats = self.get_stats()
        elapsed_formatted = self.format_time(stats["elapsed"])
        eta_formatted = (
            self.format_time(stats["eta"]) if stats["eta"] > 0 else "Calculating..."
        )

        return (
            f"📊 **Forward Progress: {stats['percentage']:.1f}%**\n"
            f"✅ Processed: {stats['processed']:,}/{stats['total']:,}\n"
            f"🕒 ETA: {eta_formatted}\n"
            f"⌛ Elapsed: {elapsed_formatted}\n"
            f"📑 Media Groups: {stats['media_groups']}\n"
            f"⚠️ Failed: {stats['failed']}\n"
            f"⏭️ Skipped: {stats['skipped']}\n"
        )


class MessageQueue:
    """Manages queued messages for forwarding."""

    def __init__(self, max_size: int = 1000):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._active = True

    async def add(self, message: Any) -> None:
        """Add message to queue."""
        if self._active:
            await self.queue.put(message)

    async def get(self) -> Optional[Any]:
        """Get next message from queue."""
        if not self._active:
            return None
        try:
            return await self.queue.get()
        except asyncio.QueueEmpty:
            return None

    def stop(self) -> None:
        """Stop queue processing."""
        self._active = False

    @property
    def size(self) -> int:
        """Current queue size."""
        return self.queue.qsize()


def setup_logging() -> None:
    """Configure logging with rich handler."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] - %(levelname)s: %(message)s - %(filename)s - %(lineno)s - %(funcName)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("bot.log")],
        datefmt="%H:%M:%S",
    )
