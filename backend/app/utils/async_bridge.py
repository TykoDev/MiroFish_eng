"""
Async-to-sync bridge utility for Flask.

LightRAG is async; Flask is sync. This module provides utilities to run
async coroutines from synchronous Flask context.
"""

import asyncio
import threading


_loop = None
_loop_thread = None
_loop_ready = threading.Event()
_loop_lock = threading.Lock()


def _run_loop_forever():
    global _loop

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _loop = loop
    _loop_ready.set()
    loop.run_forever()


def _ensure_loop():
    global _loop_thread

    with _loop_lock:
        if _loop_thread and _loop_thread.is_alive() and _loop and not _loop.is_closed():
            return _loop

        _loop_ready.clear()
        _loop_thread = threading.Thread(
            target=_run_loop_forever,
            name="mirofish-async-loop",
            daemon=True,
        )
        _loop_thread.start()

    _loop_ready.wait()
    return _loop


def run_async(coro):
    """Run an async coroutine from synchronous Flask context.

    Uses a single dedicated background event loop so async stateful
    libraries like LightRAG do not bounce between different loops.
    """
    loop = _ensure_loop()

    if threading.current_thread() is _loop_thread:
        raise RuntimeError(
            "run_async cannot be called from the async bridge loop thread"
        )

    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()
