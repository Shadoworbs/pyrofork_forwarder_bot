"""Utilities for collecting media group messages before forwarding."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional


class MediaGroupCollector:
    """Collect and release media group messages with a flush window."""

    def __init__(self, flush_window: float = 3.0) -> None:
        self.flush_window = flush_window
        self.groups: Dict[str, List[Any]] = defaultdict(list)
        self.arrival_times: Dict[str, datetime] = {}

    def add_message(self, message: Any) -> bool:
        """Track a message inside its media group."""
        if not getattr(message, "media_group_id", None):
            return False

        group_id = message.media_group_id
        self.groups[group_id].append(message)
        if group_id not in self.arrival_times:
            self.arrival_times[group_id] = getattr(
                message, "date", None
            ) or datetime.now(UTC)
        return True

    def get_ready_groups(
        self, current_time: Optional[datetime] = None
    ) -> List[List[Any]]:
        """Return groups that are ready to forward."""

        if current_time is None:
            current_time = datetime.now(UTC)

        ready: List[List[Any]] = []
        for group_id in list(self.groups.keys()):
            messages = self.groups[group_id]
            if len(messages) >= 2:
                ready.append(self._pop_group(group_id))
                continue

            first_seen = self.arrival_times.get(group_id)
            if (
                first_seen
                and (current_time - first_seen).total_seconds() >= self.flush_window
            ):
                ready.append(self._pop_group(group_id))

        return ready

    def drain_all(self) -> List[List[Any]]:
        """Flush every pending group regardless of state."""
        remaining: List[List[Any]] = []
        for group_id in list(self.groups.keys()):
            remaining.append(self._pop_group(group_id))
        return remaining

    def _pop_group(self, group_id: str) -> List[Any]:
        """Remove and return a media group by its ID."""
        messages = sorted(
            self.groups[group_id], key=lambda message: getattr(message, "id", 0)
        )
        del self.groups[group_id]
        self.arrival_times.pop(group_id, None)
        return messages
