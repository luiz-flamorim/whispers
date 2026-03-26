from datetime import datetime
from queue import Empty, Queue
from threading import Thread

from py5canvas import *

_commands = Queue()
_is_running = False
_state = {
    "relay_name": "-",
    "start": "-",
    "received": "-",
    "emitted": "-",
    "emitted_to": "-",
    "stop": "-",
}


def _now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _fit_text(text: str, limit: int = 110) -> str:
    if not text:
        return "-"
    clean = " ".join(str(text).split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def _queue_update(payload: dict) -> None:
    _commands.put(("state_update", payload))


def relay_start(relay_name: str, received: str) -> None:
    _queue_update(
        {
            "relay_name": relay_name,
            "start": _now_str(),
            "received": _fit_text(received),
            "emitted": "-",
            "emitted_to": "-",
            "stop": "-",
        }
    )


def relay_stop(relay_name: str, emitted: str, emitted_to: str) -> None:
    _queue_update(
        {
            "relay_name": relay_name,
            "emitted": _fit_text(emitted),
            "emitted_to": emitted_to,
            "stop": _now_str(),
        }
    )


def _apply_commands() -> None:
    while True:
        try:
            cmd, value = _commands.get_nowait()
        except Empty:
            break
        if cmd == "state_update":
            _state.update(value)


def setup() -> None:
    size(1100, 360)
    text_size(24)
    text_font(create_font("Consolas", 22))


def draw() -> None:
    _apply_commands()
    background(20, 24, 28)
    fill(230)
    y = 50
    for label in ("relay_name", "start", "received", "emitted", "emitted_to", "stop"):
        text(f"{label}: {_state[label]}", [30, y])
        y += 50


def start_visuals() -> None:
    global _is_running
    if _is_running:
        return
    _is_running = True
    try:
        Thread(target=run, daemon=True).start()
    except Exception:
        _is_running = False


def stop_visuals() -> None:
    global _is_running
    if not _is_running:
        return
    _is_running = False
    try:
        no_loop()
    except Exception:
        pass