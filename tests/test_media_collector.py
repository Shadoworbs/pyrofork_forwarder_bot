from datetime import datetime, timedelta, UTC
from types import SimpleNamespace

from bot.media_collector import MediaGroupCollector


def make_message(message_id, group_id=None, *, date=None):
    return SimpleNamespace(
        id=message_id,
        media_group_id=group_id,
        date=date or datetime.now(UTC),
    )


def test_collector_returns_complete_groups():
    collector = MediaGroupCollector(flush_window=10)
    first = make_message(2, "grp")
    second = make_message(1, "grp")

    collector.add_message(first)
    assert collector.get_ready_groups() == []

    collector.add_message(second)
    ready = collector.get_ready_groups()

    assert len(ready) == 1
    assert [msg.id for msg in ready[0]] == [1, 2]


def test_collector_flushes_single_message_groups():
    collector = MediaGroupCollector(flush_window=0.5)
    old_time = datetime.now(UTC) - timedelta(seconds=1)
    lone = make_message(5, "solo", date=old_time)

    collector.add_message(lone)
    flushed = collector.get_ready_groups(datetime.now(UTC))

    assert len(flushed) == 1
    assert flushed[0][0].id == 5


def test_collector_drain_all_clears_state():
    collector = MediaGroupCollector(flush_window=5)
    collector.add_message(make_message(3, "group"))
    remaining = collector.drain_all()

    assert len(remaining) == 1
    assert collector.get_ready_groups() == []
