from datetime import datetime
from threading import Lock

_lock = Lock()
_relay_order = []
_relay_state = {}


def _now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _fit_text(text: str, limit: int = 90) -> str:
    if not text:
        return "-"
    clean = " ".join(str(text).split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def _blank_relay_state() -> dict:
    return {
        "status": "waiting",
        "start": "-",
        "received": "-",
        "emitted": "-",
        "emitted_to": "-",
        "stop": "-",
    }


def configure_relays(relay_names) -> None:
    with _lock:
        global _relay_order, _relay_state
        _relay_order = list(relay_names)
        _relay_state = {name: _blank_relay_state() for name in _relay_order}


def relay_start(relay_name: str, received: str) -> None:
    with _lock:
        if relay_name not in _relay_state:
            _relay_order.append(relay_name)
            _relay_state[relay_name] = _blank_relay_state()
        _relay_state[relay_name].update(
            {
                "status": "running",
                "start": _now_str(),
                "received": _fit_text(received),
                "emitted": "-",
                "emitted_to": "-",
                "stop": "-",
            }
        )


def relay_stop(relay_name: str, emitted: str, emitted_to: str) -> None:
    with _lock:
        if relay_name not in _relay_state:
            _relay_order.append(relay_name)
            _relay_state[relay_name] = _blank_relay_state()
        _relay_state[relay_name].update(
            {
                "status": "done",
                "emitted": _fit_text(emitted),
                "emitted_to": emitted_to,
                "stop": _now_str(),
            }
        )


def snapshot() -> tuple[list[str], dict]:
    with _lock:
        return list(_relay_order), {name: dict(data) for name, data in _relay_state.items()}
