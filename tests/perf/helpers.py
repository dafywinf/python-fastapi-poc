"""Shared uvicorn server and HTTP load helpers for performance tests."""

import concurrent.futures
import threading
import time

import httpx
import uvicorn
from fastapi import FastAPI


def start_server(app: FastAPI, port: int) -> uvicorn.Server:
    """Start a uvicorn server in a daemon thread, return when ready.

    Raises RuntimeError immediately if the thread dies (e.g. port already in
    use) rather than waiting out the full timeout.
    """
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if not thread.is_alive():
            raise RuntimeError(
                f"Server on port {port} failed to start — "
                "port may already be in use or uvicorn crashed. "
                f"Check: lsof -i :{port}"
            )
        if time.monotonic() > deadline:
            raise RuntimeError(f"Server on port {port} did not become ready within 10s")
        time.sleep(0.05)
    return server


def stop_server(server: uvicorn.Server) -> None:
    server.should_exit = True


def fire_concurrent(url: str, n: int) -> tuple[float, list[int]]:
    """Fire n concurrent GET requests, return (elapsed_seconds, status_codes)."""

    def get() -> int:
        with httpx.Client(timeout=30) as client:
            return client.get(url).status_code

    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        futures = [executor.submit(get) for _ in range(n)]
        status_codes = [f.result() for f in futures]
    elapsed = time.perf_counter() - start
    return elapsed, status_codes
