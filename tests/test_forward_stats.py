from datetime import datetime, timedelta

from bot.utils import ForwardStats


def test_forward_stats_percentage_and_eta():
    stats = ForwardStats()
    stats.start_time = datetime.now() - timedelta(seconds=40)
    stats.total = 10
    stats.processed = 4
    stats.failed = 1
    stats.skipped = 2
    stats.media_groups = 3

    report = stats.get_stats()

    assert report["processed"] == 4
    assert report["failed"] == 1
    assert report["skipped"] == 2
    assert report["media_groups"] == 3
    assert report["percentage"] == 40.0
    assert report["eta"] > 0

    progress_text = stats.format_progress()
    assert "40.0%" in progress_text
    assert "Processed" in progress_text


def test_forward_stats_format_time():
    stats = ForwardStats()
    assert stats.format_time(3661) == "1H:01M:01S"
    assert stats.format_time(0) == "0:00:00"
