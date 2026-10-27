from __future__ import annotations

import asyncio
import selectors
import shutil
import socket
import sys
import tempfile
import time
from pathlib import Path

import pytest

if sys.platform == "win32":

    class _NoSocketSelectSelector(selectors.SelectSelector):
        def _select(  # type: ignore[no-untyped-def]
            self, readers, writers, exceptional, timeout=None
        ):
            if not readers and not writers and not exceptional:
                if timeout:
                    time.sleep(timeout)
                return [], [], []
            return super()._select(readers, writers, exceptional, timeout)

    class _NoSelfPipeSelectorEventLoop(asyncio.SelectorEventLoop):
        """Selector loop for Windows sandboxes where loopback socketpair is blocked."""

        def __init__(self) -> None:
            super().__init__(_NoSocketSelectSelector())

        def _make_self_pipe(self) -> None:
            self._ssock = None
            self._csock = None

        def _close_self_pipe(self) -> None:
            self._ssock = None
            self._csock = None

        def _write_to_self(self) -> None:
            return

    class _NoSelfPipeSelectorEventLoopPolicy(asyncio.WindowsSelectorEventLoopPolicy):
        _loop_factory = _NoSelfPipeSelectorEventLoop

    def _loopback_socketpair_available() -> bool:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.settimeout(0.1)
        client.settimeout(0.1)
        try:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            client.connect(listener.getsockname())
            server, _ = listener.accept()
            server.close()
            return True
        except OSError:
            return False
        finally:
            client.close()
            listener.close()

    if not _loopback_socketpair_available():
        asyncio.set_event_loop_policy(_NoSelfPipeSelectorEventLoopPolicy())


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest) -> Path:
    """Use an isolated Windows temp directory without pytest's ACL-sensitive cleanup."""
    path = Path(tempfile.mkdtemp(prefix=".creator-pytest-", dir=Path.cwd()))
    request.addfinalizer(lambda: shutil.rmtree(path, ignore_errors=True))
    return path
