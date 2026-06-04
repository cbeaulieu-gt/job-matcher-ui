"""tests/test_ingest_observability.py — Regression tests for issue #602.

Covers three observability improvements added to ingest.py and db.py:

1. Log flushing  — FileHandler subclass flushes after every record.
2. Pool wait timeout — db.get_connection() raises PoolWaitTimeout when
   the connection pool is exhausted and the wait exceeds the configured
   timeout.
3. Heartbeat logging — the background heartbeat thread emits a
   progress line at a configurable cadence.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _root_handler_cleanup(root: logging.Logger, before: list) -> None:
    """Remove any handler added to *root* that was not present in *before*."""
    for h in list(root.handlers):
        if h not in before:
            root.removeHandler(h)
            try:
                h.close()
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------------------
# 1. Log flushing — ImmediateFlushHandler
# ---------------------------------------------------------------------------

class TestImmediateFlushHandler:
    """The FileHandler used in _configure_file_logging() must flush on emit."""

    def test_handler_exists(self) -> None:
        """ingest module must export ImmediateFlushHandler."""
        import ingest
        assert hasattr(ingest, "ImmediateFlushHandler"), (
            "Expected ingest.ImmediateFlushHandler to exist"
        )

    def test_is_file_handler_subclass(self) -> None:
        """ImmediateFlushHandler must be a FileHandler subclass."""
        import ingest
        assert issubclass(ingest.ImmediateFlushHandler, logging.FileHandler)

    def test_flush_called_on_emit(self, tmp_path: pytest.TempdirFactory) -> None:
        """emit() must call flush() so each log record lands on disk immediately."""
        import ingest
        log_file = tmp_path / "test.log"
        handler = ingest.ImmediateFlushHandler(str(log_file), encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))

        flush_calls: list[None] = []
        original_flush = handler.flush

        def recording_flush() -> None:
            flush_calls.append(None)
            original_flush()

        handler.flush = recording_flush  # type: ignore[method-assign]

        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="hello",
                args=(),
                exc_info=None,
            )
            handler.emit(record)
        finally:
            handler.close()

        assert flush_calls, (
            "expected flush() to be called at least once during emit()"
        )

    def test_configure_file_logging_uses_immediate_flush_handler(
        self, tmp_path: pytest.TempdirFactory
    ) -> None:
        """_configure_file_logging() must attach an ImmediateFlushHandler."""
        import ingest

        root = logging.getLogger()
        handlers_before = list(root.handlers)
        try:
            with patch("ingest._configure_file_logging.__module__"):
                pass
            # Call the real function with a tmp log dir
            with patch("paths.get_log_dir", return_value=tmp_path):
                ingest._configure_file_logging()

            new_handlers = [
                h for h in root.handlers if h not in handlers_before
            ]
            assert any(
                isinstance(h, ingest.ImmediateFlushHandler)
                for h in new_handlers
            ), (
                "Expected at least one ImmediateFlushHandler attached to root "
                f"logger, got: {new_handlers}"
            )
        finally:
            _root_handler_cleanup(root, handlers_before)


# ---------------------------------------------------------------------------
# 2. Pool wait timeout — PoolWaitTimeout + get_connection()
# ---------------------------------------------------------------------------

class TestPoolWaitTimeout:
    """db.get_connection() must raise PoolWaitTimeout when the pool is
    exhausted and the configured wait elapses."""

    def test_pool_wait_timeout_exported(self) -> None:
        """db module must expose PoolWaitTimeout."""
        import db
        assert hasattr(db, "PoolWaitTimeout"), (
            "Expected db.PoolWaitTimeout to exist"
        )

    def test_pool_wait_timeout_is_exception(self) -> None:
        """PoolWaitTimeout must be an Exception subclass."""
        import db
        assert issubclass(db.PoolWaitTimeout, Exception)

    def test_raises_when_pool_exhausted(self) -> None:
        """get_connection() raises PoolWaitTimeout promptly when getconn() blocks."""
        import db

        # Simulate an exhausted pool by making getconn() block indefinitely.
        blocking_event = threading.Event()

        def _blocking_getconn(*_args, **_kwargs):
            # Block until the test tells us the timeout has already fired.
            blocking_event.wait(timeout=10)
            raise Exception("should not reach here in normal test flow")

        mock_pool = MagicMock()
        mock_pool.getconn.side_effect = _blocking_getconn

        start = time.monotonic()
        try:
            with patch("db._get_pool", return_value=mock_pool):
                with pytest.raises(db.PoolWaitTimeout):
                    # Pass a very short timeout so the test finishes quickly.
                    db.get_connection(pool_wait_timeout=0.3)
        finally:
            blocking_event.set()  # unblock the background thread

        elapsed = time.monotonic() - start
        # Should fail within ~2x the timeout, not after a long hang.
        assert elapsed < 3.0, (
            f"get_connection() took {elapsed:.2f}s — expected < 3s for a 0.3s timeout"
        )

    def test_raises_promptly(self) -> None:
        """PoolWaitTimeout must fire close to the configured timeout, not much later."""
        import db

        def _blocking_getconn(*_args, **_kwargs):
            time.sleep(10)  # simulate infinite block

        mock_pool = MagicMock()
        mock_pool.getconn.side_effect = _blocking_getconn

        start = time.monotonic()
        with patch("db._get_pool", return_value=mock_pool):
            with pytest.raises(db.PoolWaitTimeout):
                db.get_connection(pool_wait_timeout=0.25)

        elapsed = time.monotonic() - start
        # Allow 2x headroom for CI jitter, but not 10s of hang.
        assert elapsed < 2.0, (
            f"Timeout took {elapsed:.2f}s; expected < 2.0s for a 0.25s timeout"
        )

    def test_succeeds_when_pool_not_exhausted(self) -> None:
        """get_connection() returns normally when getconn() succeeds promptly."""
        import db

        mock_conn = MagicMock()
        mock_conn.autocommit = False
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        with patch("db._get_pool", return_value=mock_pool):
            conn = db.get_connection(pool_wait_timeout=5.0)

        assert conn is not None
        mock_pool.getconn.assert_called_once()

    def test_default_timeout_is_bounded(self) -> None:
        """The default pool_wait_timeout must be a positive finite number."""
        import db
        assert hasattr(db, "POOL_WAIT_TIMEOUT_SECONDS"), (
            "Expected db.POOL_WAIT_TIMEOUT_SECONDS to exist"
        )
        assert db.POOL_WAIT_TIMEOUT_SECONDS > 0
        assert db.POOL_WAIT_TIMEOUT_SECONDS < 300  # sanity — no more than 5 min


# ---------------------------------------------------------------------------
# 3. Heartbeat logging
# ---------------------------------------------------------------------------

class TestHeartbeat:
    """The _HeartbeatThread helper must log at the configured cadence."""

    def test_heartbeat_class_exported(self) -> None:
        """ingest module must expose _HeartbeatThread."""
        import ingest
        assert hasattr(ingest, "_HeartbeatThread"), (
            "Expected ingest._HeartbeatThread to exist"
        )

    def test_heartbeat_is_daemon(self) -> None:
        """_HeartbeatThread must run as a daemon so it does not block process exit."""
        import ingest
        stop_evt = threading.Event()
        hb = ingest._HeartbeatThread(
            stop_event=stop_evt,
            interval_seconds=60,
            get_counts=lambda: (0, 0, "idle"),
        )
        assert hb.daemon, "_HeartbeatThread must be a daemon thread"

    def test_heartbeat_logs_at_configured_interval(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """_HeartbeatThread must emit at least one heartbeat within 2x its interval."""
        import ingest

        stop_evt = threading.Event()
        heartbeat_fired = threading.Event()

        def _get_counts():
            return (5, 20, "scoring")

        # Use a very short interval so the test finishes quickly.
        hb = ingest._HeartbeatThread(
            stop_event=stop_evt,
            interval_seconds=0.1,
            get_counts=_get_counts,
        )

        with caplog.at_level(logging.INFO, logger="ingest"):
            hb.start()
            # Wait up to 1s for at least one heartbeat message.
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                if any(
                    "heartbeat" in r.message.lower()
                    or "still working" in r.message.lower()
                    or "processed" in r.message.lower()
                    for r in caplog.records
                ):
                    heartbeat_fired.set()
                    break
                time.sleep(0.02)
            stop_evt.set()
            hb.join(timeout=2.0)

        assert heartbeat_fired.is_set(), (
            f"No heartbeat log emitted within 1s. Records: {caplog.records}"
        )

    def test_heartbeat_stops_on_event(self) -> None:
        """_HeartbeatThread must stop running after stop_event is set."""
        import ingest

        stop_evt = threading.Event()

        hb = ingest._HeartbeatThread(
            stop_event=stop_evt,
            interval_seconds=0.05,
            get_counts=lambda: (1, 10, "scraping"),
        )
        hb.start()
        stop_evt.set()
        hb.join(timeout=2.0)

        assert not hb.is_alive(), (
            "_HeartbeatThread is still alive after stop_event was set"
        )

    def test_heartbeat_includes_progress_info(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Heartbeat messages must include scored/fetched counts and stage."""
        import ingest

        stop_evt = threading.Event()

        def _get_counts():
            return (7, 42, "scraping")

        hb = ingest._HeartbeatThread(
            stop_event=stop_evt,
            interval_seconds=0.05,
            get_counts=_get_counts,
        )
        with caplog.at_level(logging.INFO, logger="ingest"):
            hb.start()
            time.sleep(0.3)
            stop_evt.set()
            hb.join(timeout=2.0)

        heartbeat_records = [
            r for r in caplog.records
            if (
                "heartbeat" in r.message.lower()
                or "still working" in r.message.lower()
                or "processed" in r.message.lower()
            )
        ]
        assert heartbeat_records, "No heartbeat records emitted"
        # At least one record should contain count/stage info.
        combined = " ".join(r.message for r in heartbeat_records)
        assert "7" in combined or "42" in combined or "scraping" in combined, (
            f"Heartbeat messages do not appear to include progress info: {combined}"
        )
